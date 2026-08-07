"""Backend LLM pluggable pour CHRUTH (défaut Ollama local, repli cloud optionnel).

Sélection par variables d'environnement :
  CHRUTH_LLM_PROVIDER = ollama (défaut) | anthropic | mistral | groq | gemini
  CHRUTH_LLM_MODEL    = nom du modèle (sinon défaut par fournisseur)
  OLLAMA_HOST         = http://localhost:11434 (défaut)
  ANTHROPIC_API_KEY / MISTRAL_API_KEY / GROQ_API_KEY / GEMINI_API_KEY pour le cloud.

Données prospects = locales par défaut (Ollama). Aucun SDK : appels HTTP directs.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests

DEFAULT_PROVIDER = "ollama"
DEFAULT_MODELS = {
    "ollama": "llama3.1:8b",
    # Chaque fournisseur porte un modele par defaut, sans quoi sa cle est
    # inutilisable : un appel sans nom de modele n'a nulle part ou aller, et le
    # fournisseur est alors declare « cle absente » puis ignore en silence.
    # CHRUTH_LLM_MODEL reste la pour en imposer un autre.
    "anthropic": "claude-haiku-4-5-20251001",
    "mistral": "mistral-small-latest",
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-2.5-flash",
}
_CLES = {
    "anthropic": "ANTHROPIC_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


# --- Ou vivent les cles -----------------------------------------------------
# Le `.env` est cherche a cote de ce fichier, jamais dans le dossier courant :
# l'app peut etre lancee depuis n'importe ou, et le pipeline tourne dans un
# sous-processus dont le dossier de travail n'est pas celui du produit.
CHEMIN_ENV = Path(__file__).resolve().parent / ".env"


def charger_env(chemin: str | Path | None = None) -> None:
    """Pose dans l'environnement les cles ecrites dans un `.env`.

    Charge ici, et pas dans une page : une cle qui n'est lue que par la page
    Messages ne marche que si l'utilisateur ouvre cette page en premier — la
    veille et le pipeline, eux, la croient absente et retombent en brouillon
    deterministe. Le fichier ne recouvre jamais une variable deja posee : sur le
    veilleur GitHub, c'est le secret du depot qui doit gagner.

    L'absence de fichier est le cas normal du poste sans cle cloud : elle ne
    doit rien casser.
    """
    fichier = Path(chemin) if chemin is not None else CHEMIN_ENV
    try:
        if not fichier.is_file():
            return
        lignes = fichier.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for ligne in lignes:
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        nom, _, valeur = ligne.partition("=")
        nom = nom.removeprefix("export ").strip()
        valeur = valeur.strip().strip('"').strip("'")
        if nom and valeur and not os.environ.get(nom):
            os.environ[nom] = valeur


charger_env()


# --- Budget de tokens -------------------------------------------------------
# Un email de prospection tient largement sous 1024 tokens. Le plafond n'est pas
# la pour brider la redaction mais pour empecher qu'une reponse parte en boucle :
# sur une API facturee au token, rien d'autre ne l'arrete.
MAX_TOKENS_DEFAUT = 1024
# Entree : la fiche CHRUTH et l'intitule du marche sont recopies dans le prompt.
# Un texte de marche a rallonge ferait payer l'entree avant meme la reponse.
MAX_TOKENS_ENTREE_DEFAUT = 6000
# Environ quatre caracteres par token en francais. C'est un ordre de grandeur
# assume : seul le fournisseur compte vraiment, et il ne le dit qu'apres coup.
CARACTERES_PAR_TOKEN = 4
MARQUE_TRONCATURE = "[...]"


def estimer_tokens(texte: str | None) -> int:
    """Estimation du cout en tokens d'un texte, pour l'afficher avant de payer."""
    longueur = len(str(texte or ""))
    if not longueur:
        return 0
    return max(1, round(longueur / CARACTERES_PAR_TOKEN))


def tronquer(texte: str, max_tokens: int) -> str:
    """Coupe un texte au plafond de tokens, en signalant la coupe.

    Un plafond nul ou negatif n'est pas une demande de texte vide mais une
    valeur de reglage aberrante : on retombe sur le plafond par defaut plutot
    que d'envoyer un prompt sans contenu.
    """
    texte = str(texte or "")
    if max_tokens <= 0:
        max_tokens = MAX_TOKENS_ENTREE_DEFAUT
    limite = max_tokens * CARACTERES_PAR_TOKEN
    if len(texte) <= limite:
        return texte
    garde = max(0, limite - len(MARQUE_TRONCATURE) - 1)
    return texte[:garde].rstrip() + " " + MARQUE_TRONCATURE


def _provider() -> str:
    return os.environ.get("CHRUTH_LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower()


def _model(provider: str) -> str:
    return os.environ.get("CHRUTH_LLM_MODEL") or DEFAULT_MODELS.get(provider, "")


def _cloud_configure(provider: str) -> bool:
    """Vrai si le fournisseur possède une clé et un modèle utilisable."""
    return bool(os.environ.get(_CLES.get(provider, ""))) and bool(_model(provider))


def _ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def llm_disponible(provider: str | None = None) -> bool:
    provider = provider or _provider()
    if provider == "ollama":
        try:
            return requests.get(_ollama_host() + "/api/tags", timeout=3).status_code == 200
        except Exception:
            return False
    return _cloud_configure(provider)


_CLOUD_ORDRE = ("anthropic", "mistral", "groq", "gemini")
# Liste offerte a l'utilisateur : le local d'abord, puis tout fournisseur dont
# une cle peut exister. En omettre un rend sa cle inutilisable a la main, alors
# meme que le moteur automatique sait s'en servir.
FOURNISSEURS = ("ollama",) + _CLOUD_ORDRE


def appliquer_choix(provider: str, modele: str = "") -> None:
    """Enregistre le fournisseur choisi, et le modele seulement s'il est donne.

    Le modele vit dans une variable commune a tous les fournisseurs : la laisser
    en place en changeant de fournisseur enverrait le modele du precedent au
    suivant — une cle valable, un appel refuse, et un utilisateur convaincu que
    sa cle est morte. Un champ vide vaut donc effacement, pas conservation.
    """
    os.environ["CHRUTH_LLM_PROVIDER"] = str(provider or "").strip().lower()
    modele = str(modele or "").strip()
    if modele:
        os.environ["CHRUTH_LLM_MODEL"] = modele
    else:
        os.environ.pop("CHRUTH_LLM_MODEL", None)


def cloud_provider() -> str | None:
    """Fournisseur cloud à utiliser (jamais Ollama, aucun probe réseau).

    1) CHRUTH_LLM_PROVIDER cloud explicite + sa clé présente -> ce fournisseur ;
    2) sinon la 1re clé présente dans l'ordre anthropic > mistral > groq > gemini ;
    3) sinon None.
    """
    prov = _provider()
    if prov in _CLOUD_ORDRE and _cloud_configure(prov):
        return prov
    for p in _CLOUD_ORDRE:
        if _cloud_configure(p):
            return p
    return None


def cloud_disponible() -> bool:
    return cloud_provider() is not None


def moteur_auto() -> str | None:
    """Source auto : cloud si clé, sinon 'ollama' si dispo, sinon None (repli)."""
    prov = cloud_provider()
    if prov:
        return prov
    if llm_disponible("ollama"):
        return "ollama"
    return None


def generer(prompt: str, system: str = "", provider: str | None = None,
            model: str | None = None, timeout: int = 120, temperature: float = 0.3,
            max_tokens: int = MAX_TOKENS_DEFAUT,
            max_tokens_entree: int = MAX_TOKENS_ENTREE_DEFAUT) -> str:
    """Genere un texte, entree tronquee et sortie bornee.

    Les deux plafonds sont volontairement separes : l'entree depend de ce qu'on
    recopie du marche et de la fiche, la sortie de la longueur de message qu'on
    veut. Les confondre obligerait a rogner l'une pour allonger l'autre.
    """
    provider = provider or _provider()
    model = model or _model(provider)
    if not model:
        raise ValueError("Définir CHRUTH_LLM_MODEL pour ce fournisseur.")
    prompt = tronquer(prompt, max_tokens_entree)
    if provider == "ollama":
        return _gen_ollama(prompt, system, model, timeout, temperature, max_tokens)
    if provider == "anthropic":
        return _gen_anthropic(prompt, system, model, timeout, temperature, max_tokens)
    if provider in ("mistral", "groq"):
        return _gen_openai_like(prompt, system, model, timeout, temperature, provider, max_tokens)
    if provider == "gemini":
        return _gen_gemini(prompt, system, model, timeout, temperature, max_tokens)
    raise ValueError(f"Fournisseur LLM inconnu : {provider}")


def _gen_ollama(prompt: str, system: str, model: str, timeout: int, temperature: float,
                max_tokens: int = MAX_TOKENS_DEFAUT) -> str:
    payload = {"model": model, "prompt": prompt, "system": system, "stream": False,
               "options": {"temperature": temperature, "num_predict": max_tokens}}
    r = requests.post(_ollama_host() + "/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    return str(r.json().get("response", "")).strip()


def _gen_anthropic(prompt: str, system: str, model: str, timeout: int, temperature: float,
                   max_tokens: int = MAX_TOKENS_DEFAUT) -> str:
    headers = {"x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
               "anthropic-version": "2023-06-01", "content-type": "application/json"}
    payload = {"model": model, "max_tokens": max_tokens, "system": system, "temperature": temperature,
               "messages": [{"role": "user", "content": prompt}]}
    r = requests.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=timeout)
    r.raise_for_status()
    return "".join(b.get("text", "") for b in r.json().get("content", [])).strip()


def _gen_gemini(prompt: str, system: str, model: str, timeout: int, temperature: float,
                max_tokens: int = MAX_TOKENS_DEFAUT) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    headers = {"x-goog-api-key": os.environ.get("GEMINI_API_KEY", ""),
               "Content-Type": "application/json"}
    payload: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if system:
        payload["system_instruction"] = {"parts": [{"text": system}]}
    r = requests.post(url, json=payload, headers=headers, timeout=timeout)
    r.raise_for_status()
    candidates = r.json().get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()


def _gen_openai_like(prompt: str, system: str, model: str, timeout: int,
                     temperature: float, provider: str,
                     max_tokens: int = MAX_TOKENS_DEFAUT) -> str:
    url = {"mistral": "https://api.mistral.ai/v1/chat/completions",
           "groq": "https://api.groq.com/openai/v1/chat/completions"}[provider]
    headers = {"Authorization": f"Bearer {os.environ.get(_CLES[provider], '')}",
               "Content-Type": "application/json"}
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    payload = {"model": model, "messages": messages, "temperature": temperature,
               "max_tokens": max_tokens}
    r = requests.post(url, json=payload, headers=headers, timeout=timeout)
    r.raise_for_status()
    return str(r.json()["choices"][0]["message"]["content"]).strip()
