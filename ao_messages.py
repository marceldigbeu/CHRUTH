"""Mission 3 (volet AO) : messages de prospection à destination de l'ACHETEUR qui
a publié un appel d'offres. Généré directement par AO (valeurs réelles injectées
dans le prompt -> message fini, pas de placeholders : peu d'AO).

Style SEKOIA : rôle expert + contexte AO injecté + garde-fous anti-hallucination.
Repli sur les templates déterministes existants (ao_extract_fields) si pas de LLM.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

import signature
from ao_config import OUTPUT_DIR
from ao_extract_fields import call_script, email_template
from prospect_messages import _parser_reponse  # parser JSON robuste (DRY)

CACHE_PATH = OUTPUT_DIR / "ao_messages.json"
PRIORITES_AO = ("CHAUD", "TIEDE")

MESSAGES_AO_DIR = OUTPUT_DIR / "messages_ao"


def _slug_id(record) -> str:
    raw = str(record.get("id_ao") or "").strip() if hasattr(record, "get") else ""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", raw).strip("_")
    return slug or "AO"


def ecrire_brouillon_md(record, msg: dict, dossier: Path = MESSAGES_AO_DIR) -> Path:
    """Écrit le brouillon (email + script) en Markdown éditable ; renvoie le chemin."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"AO_{_slug_id(record)}.md"
    contenu = (
        f"# Brouillon AO — {_val(record, 'objet', '(objet)')}\n\n"
        f"- Acheteur : {_val(record, 'acheteur', '')}\n"
        f"- Ville : {_val(record, 'ville', '')}\n"
        f"- Date limite : {_val(record, 'date_limite', '')}\n"
        f"- Source : {msg.get('source', '')}\n\n"
        "## Email\n\n"
        f"{msg.get('email', '')}\n\n"
        "## Script d'appel\n\n"
        f"{msg.get('script', '')}\n"
    )
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def _val(record, key: str, defaut: str = "") -> str:
    v = record.get(key) if hasattr(record, "get") else None
    s = "" if v is None else str(v).strip()
    return s if s and s.lower() != "nan" else defaut


def prompt_ao(record, fiche: str = "") -> tuple[str, str]:
    objet = _val(record, "objet", "cet appel d'offres")
    acheteur = _val(record, "acheteur", "l'acheteur")
    ville = _val(record, "ville", _val(record, "departement", ""))
    date_limite = _val(record, "date_limite", "non précisée")
    budget = _val(record, "budget_annuel_eur", _val(record, "budget_estime_eur", "à vérifier"))
    secteur = _val(record, "secteur", "")
    categorie = _val(record, "categorie", "")
    system = (
        "Tu rédiges pour CHRUTH, société privée de nettoyage et de propreté des locaux, "
        "qui est CANDIDATE à un appel d'offres. Tu écris donc DU POINT DE VUE de CHRUTH "
        "(l'entreprise candidate), à destination de l'ACHETEUR PUBLIC qui a publié le "
        "marché. Tu n'es JAMAIS l'acheteur ni un de ses agents. Français professionnel et "
        'concis. Tu réponds UNIQUEMENT par un objet JSON valide {"email": "...", '
        '"script": "..."}, sans aucun texte autour.'
    )
    if fiche.strip():
        system += (
            "\n\nFICHE CHRUTH (seule source autorisée sur l'entreprise) :\n"
            + fiche.strip()
            + "\n\nTu ne disposes que de ces informations sur CHRUTH. N'invente AUCUN fait, "
            "chiffre, prix, certification ni référence absent de cette fiche."
        )
        section_offre = (
            "4. Ce que CHRUTH propose : prestations, zone et points forts (tirés de la fiche).\n"
        )
    else:
        section_offre = (
            "4. Ce que CHRUTH propose : prestations de nettoyage et zone d'intervention ; "
            "reste générique, ne cite aucun point fort spécifique non fourni.\n"
        )
    prompt = (
        "Contexte : CHRUTH (prestataire de nettoyage) souhaite répondre à l'appel d'offres "
        "ci-dessous. Rédige, AU NOM DE CHRUTH et À DESTINATION DE L'ACHETEUR, un email "
        "structuré puis un script d'appel pour manifester l'intérêt de CHRUTH et obtenir les "
        "informations pratiques.\n\n"
        "APPEL D'OFFRES :\n"
        f"- Objet : {objet}\n"
        f"- Acheteur (le destinataire) : {acheteur}\n"
        f"- Ville : {ville}\n"
        f"- Secteur : {secteur} | Catégorie : {categorie}\n"
        f"- Date limite de réponse : {date_limite}\n"
        f"- Budget estimé : {budget}\n\n"
        "STRUCTURE ATTENDUE DE L'EMAIL (dans cet ordre) :\n"
        "1. Objet : une ligne d'objet courte citant le marché.\n"
        "2. Accroche : référence explicite à l'objet du marché et au nom de l'acheteur.\n"
        "3. Compréhension du besoin : reformule en 1 à 2 phrases l'objet du marché.\n"
        f"{section_offre}"
        "5. Demande concrète : pièces à fournir, visite éventuelle, interlocuteur, date limite.\n"
        "6. Signature : \"L'équipe CHRUTH\".\n\n"
        "STRUCTURE DU SCRIPT D'APPEL : présentation -> objet du marché -> demande "
        "(interlocuteur, pièces, date limite) -> prise de congé. 3 à 5 phrases, ton oral.\n\n"
        "QUI PARLE À QUI (important) :\n"
        f"- L'EXPÉDITEUR / l'APPELANT = CHRUTH (l'entreprise candidate).\n"
        f"- Le DESTINATAIRE = {acheteur} (l'acheteur public qui a publié le marché).\n"
        "- Le script commence par : \"Bonjour, je suis [Prénom] de la société CHRUTH\".\n\n"
        "CONSIGNES :\n"
        "- Cite explicitement l'objet du marché et le nom de l'acheteur.\n"
        "- Email : objet court + corps de 90 à 140 mots, signé \"L'équipe CHRUTH\".\n"
        "- 'email' et 'script' sont des CHAÎNES de texte simples (pas de sous-structure JSON).\n\n"
        "GARDE-FOUS :\n"
        "- Ne te fais JAMAIS passer pour l'acheteur, la mairie ou un de ses agents.\n"
        "- N'invente AUCUNE référence client, certification, prix ni chiffre.\n"
        "- N'ecris AUCUNE coordonnee (site, email, telephone, adresse) : elles sont "
        "ajoutees automatiquement apres generation. En inventer une serait une faute.\n"
        "- Reste factuel : CHRUTH = nettoyage / propreté / entretien des locaux.\n\n"
        'FORMAT : un seul objet JSON {"email": "...", "script": "..."}.'
    )
    return system, prompt


def _repli(record) -> dict:
    return {"email": email_template(record), "script": call_script(record), "source": "defaut"}


def _signer(data: dict, fiche: str) -> dict:
    """Appose la signature sur l'email et le script. Sans coordonnees, rend data tel quel."""
    if not signature.bloc(fiche or ""):
        return data
    return {**data,
            "email": signature.apposer(str(data.get("email") or ""), fiche),
            "script": signature.apposer(str(data.get("script") or ""), fiche)}


def cout_estime(record, fiche=None, max_tokens: int | None = None) -> dict:
    """Ce que coutera la redaction de cet AO, avant de la lancer.

    L'entree est mesurable exactement — c'est le prompt qu'on s'apprete a
    envoyer. La sortie ne l'est pas : on affiche donc son plafond, qui est le
    pire cas, seul chiffre honnete tant que le modele n'a pas repondu.
    """
    import llm_client

    if fiche is None:
        from prospect_messages import fiche_chruth
        fiche = fiche_chruth()
    system, prompt = prompt_ao(record, fiche=fiche or "")
    entree = llm_client.estimer_tokens(system) + llm_client.estimer_tokens(prompt)
    sortie_max = llm_client.MAX_TOKENS_DEFAUT if max_tokens is None else max_tokens
    return {"entree": entree, "sortie_max": sortie_max, "total_max": entree + sortie_max}


def generer_message_ao(record, client=None, temperature: float = 0.2, fiche=None,
                       max_tokens: int | None = None) -> dict:
    if client is None:
        import llm_client as client
    if fiche is None:
        from prospect_messages import fiche_chruth
        fiche = fiche_chruth()
    # Vrai client -> moteur_auto (cloud/ollama/None). Client injecté (tests) -> llm_disponible.
    if hasattr(client, "moteur_auto"):
        provider = client.moteur_auto()
        dispo = provider is not None
    else:
        provider = None
        try:
            dispo = client.llm_disponible()
        except Exception:
            dispo = False
    if dispo:
        try:
            system, prompt = prompt_ao(record, fiche=fiche or "")
            # cloud rapide (60s) ; Ollama à froid peut dépasser (300s)
            timeout = 300 if provider == "ollama" else 60
            # Plafond de sortie : sans lui, une API facturee au token n'a aucune
            # borne. `None` laisse la valeur par defaut du client.
            options = {} if max_tokens is None else {"max_tokens": max_tokens}
            data = _parser_reponse(client.generer(
                prompt, system, provider=provider, temperature=temperature,
                timeout=timeout, **options))
            if data:
                return _signer({**data, "source": "ia"}, fiche or "")
        except Exception:
            pass
    return _signer(_repli(record), fiche or "")


def _charger_cache(p: Path) -> dict:
    try:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _sauver_cache(c: dict, p: Path) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")


def generer_pour_ao_df(df: pd.DataFrame, refresh: bool = False, cache_path: Path = CACHE_PATH,
                       client=None) -> pd.DataFrame:
    """Ajoute brouillon_email_ia / brouillon_script_ia aux AO CHAUD/TIEDE (cache par id_ao)."""
    df = df.copy()
    df["brouillon_email_ia"] = ""
    df["brouillon_script_ia"] = ""
    if df.empty or "priorite" not in df.columns:
        return df
    cache = {} if refresh else _charger_cache(cache_path)
    from prospect_messages import fiche_chruth
    fiche = fiche_chruth()
    prio = df["priorite"].astype(str).str.upper()
    for idx in df.index:
        if prio[idx] not in PRIORITES_AO:
            continue
        rec = df.loc[idx]
        key = str(rec.get("id_ao") or idx)
        msg = cache.get(key)
        if msg is None:
            msg = generer_message_ao(rec, client=client, fiche=fiche)
            cache[key] = msg
        df.at[idx, "brouillon_email_ia"] = msg.get("email", "")
        df.at[idx, "brouillon_script_ia"] = msg.get("script", "")
    _sauver_cache(cache, cache_path)
    return df
