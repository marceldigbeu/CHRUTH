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

import requests

DEFAULT_PROVIDER = "ollama"
DEFAULT_MODELS = {
    "ollama": "llama3.1:8b",
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


def _provider() -> str:
    return os.environ.get("CHRUTH_LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower()


def _model(provider: str) -> str:
    return os.environ.get("CHRUTH_LLM_MODEL") or DEFAULT_MODELS.get(provider, "")


def _ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def llm_disponible(provider: str | None = None) -> bool:
    provider = provider or _provider()
    if provider == "ollama":
        try:
            return requests.get(_ollama_host() + "/api/tags", timeout=3).status_code == 200
        except Exception:
            return False
    return bool(os.environ.get(_CLES.get(provider, "")))


_CLOUD_ORDRE = ("anthropic", "mistral", "groq", "gemini")


def cloud_provider() -> str | None:
    """Fournisseur cloud à utiliser (jamais Ollama, aucun probe réseau).

    1) CHRUTH_LLM_PROVIDER cloud explicite + sa clé présente -> ce fournisseur ;
    2) sinon la 1re clé présente dans l'ordre anthropic > mistral > groq > gemini ;
    3) sinon None.
    """
    prov = _provider()
    if prov in _CLOUD_ORDRE and os.environ.get(_CLES[prov]):
        return prov
    for p in _CLOUD_ORDRE:
        if os.environ.get(_CLES[p]):
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
            model: str | None = None, timeout: int = 120, temperature: float = 0.3) -> str:
    provider = provider or _provider()
    model = model or _model(provider)
    if provider == "ollama":
        return _gen_ollama(prompt, system, model, timeout, temperature)
    if provider == "anthropic":
        return _gen_anthropic(prompt, system, model, timeout, temperature)
    if provider in ("mistral", "groq"):
        return _gen_openai_like(prompt, system, model, timeout, temperature, provider)
    if provider == "gemini":
        return _gen_gemini(prompt, system, model, timeout, temperature)
    raise ValueError(f"Fournisseur LLM inconnu : {provider}")


def _gen_ollama(prompt: str, system: str, model: str, timeout: int, temperature: float) -> str:
    payload = {"model": model, "prompt": prompt, "system": system, "stream": False,
               "options": {"temperature": temperature}}
    r = requests.post(_ollama_host() + "/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    return str(r.json().get("response", "")).strip()


def _gen_anthropic(prompt: str, system: str, model: str, timeout: int, temperature: float) -> str:
    headers = {"x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
               "anthropic-version": "2023-06-01", "content-type": "application/json"}
    payload = {"model": model, "max_tokens": 1024, "system": system, "temperature": temperature,
               "messages": [{"role": "user", "content": prompt}]}
    r = requests.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=timeout)
    r.raise_for_status()
    return "".join(b.get("text", "") for b in r.json().get("content", [])).strip()


def _gen_gemini(prompt: str, system: str, model: str, timeout: int, temperature: float) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    headers = {"x-goog-api-key": os.environ.get("GEMINI_API_KEY", ""),
               "Content-Type": "application/json"}
    payload: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 1024},
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
                     temperature: float, provider: str) -> str:
    url = {"mistral": "https://api.mistral.ai/v1/chat/completions",
           "groq": "https://api.groq.com/openai/v1/chat/completions"}[provider]
    headers = {"Authorization": f"Bearer {os.environ.get(_CLES[provider], '')}",
               "Content-Type": "application/json"}
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    payload = {"model": model, "messages": messages, "temperature": temperature}
    r = requests.post(url, json=payload, headers=headers, timeout=timeout)
    r.raise_for_status()
    return str(r.json()["choices"][0]["message"]["content"]).strip()
