"""Acces a l'etat de la veille depuis l'app : fichier local ou API GitHub.

Le veilleur tourne dans GitHub Actions et ecrit l'etat par git. L'app, elle,
tourne ailleurs (poste local ou Streamlit Community Cloud) : elle atteint le
meme fichier par l'API GitHub, sur la branche d'etat.

Ce module ne connait ni le tri, ni l'interface : il lit et il ecrit.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import requests

import veille_etat

API = "https://api.github.com"
CHEMIN_ETAT = "etat/veille.json"
WORKFLOW = "veille-maximilien.yml"
TIMEOUT = 20


def source() -> str:
    """'github' ou 'local' (defaut). L'app locale n'a besoin d'aucune configuration."""
    return "github" if os.environ.get("CHRUTH_VEILLE_SOURCE", "").strip().lower() == "github" \
        else "local"


def _depot() -> str:
    return os.environ.get("CHRUTH_GITHUB_REPO", "").strip()


def _branche() -> str:
    return os.environ.get("CHRUTH_GITHUB_BRANCHE", "ao-state").strip()


def _jeton() -> str:
    return os.environ.get("CHRUTH_GITHUB_TOKEN", "").strip()


def _chemin_local() -> Path:
    defaut = Path(__file__).resolve().parent / "etat" / "veille.json"
    return Path(os.environ.get("CHRUTH_VEILLE_ETAT") or defaut)


def _entetes() -> dict[str, str]:
    entetes = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    if _jeton():
        entetes["Authorization"] = f"Bearer {_jeton()}"
    return entetes


def ecriture_possible() -> bool:
    """En local, toujours. Sur GitHub, seulement avec un jeton."""
    return True if source() == "local" else bool(_jeton() and _depot())


def _url_contenu() -> str:
    return f"{API}/repos/{_depot()}/contents/{CHEMIN_ETAT}?ref={_branche()}"


def _lire_github() -> tuple[dict[str, Any], str | None]:
    r = requests.get(_url_contenu(), headers=_entetes(), timeout=TIMEOUT)
    if r.status_code == 404:
        return veille_etat._vide(), None
    if r.status_code != 200:
        raise RuntimeError(f"lecture de l'etat impossible (HTTP {r.status_code})")
    corps = r.json()
    brut = base64.b64decode(corps.get("content", "")).decode("utf-8")
    try:
        etat = json.loads(brut)
    except Exception:  # noqa: BLE001
        return veille_etat._vide(), corps.get("sha")
    etat.setdefault("aos", {})
    etat.setdefault("guide_messages", "")
    etat.setdefault("version", veille_etat.ETAT_VERSION)
    return etat, corps.get("sha")


def lire() -> tuple[dict[str, Any], str | None]:
    """Etat courant et, sur GitHub, le sha du blob (necessaire pour ecrire)."""
    if source() == "local":
        return veille_etat.charger(_chemin_local()), None
    return _lire_github()


def _put(etat: dict[str, Any], sha: str | None, message: str):
    corps = {
        "message": message,
        "content": base64.b64encode(
            json.dumps(etat, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        ).decode(),
        "branch": _branche(),
    }
    if sha:
        corps["sha"] = sha
    return requests.put(f"{API}/repos/{_depot()}/contents/{CHEMIN_ETAT}",
                        headers=_entetes(), json=corps, timeout=TIMEOUT)


def ecrire(etat: dict[str, Any], sha: str | None,
           message: str = "etat veille (app)") -> str | None:
    """Enregistre l'etat. Sur conflit, relit puis reessaie une fois (spec 7)."""
    if not ecriture_possible():
        raise PermissionError(
            "Ecriture impossible : jeton GitHub absent. Renseigner CHRUTH_GITHUB_TOKEN "
            "(permissions contents:write et actions:write sur ce seul depot)."
        )
    if source() == "local":
        veille_etat.enregistrer(etat, _chemin_local())
        return None

    r = _put(etat, sha, message)
    if r.status_code in (409, 422):
        # Un run de veille a ecrit entre notre lecture et notre ecriture.
        _, sha_frais = _lire_github()
        r = _put(etat, sha_frais, message)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"ecriture de l'etat refusee (HTTP {r.status_code})")
    return (r.json().get("content") or {}).get("sha")


def declencher_veille() -> bool:
    """Lance le workflow immediatement (bouton « verifier maintenant », spec 6.5)."""
    if source() != "github" or not _jeton():
        return False
    r = requests.post(
        f"{API}/repos/{_depot()}/actions/workflows/{WORKFLOW}/dispatches",
        headers=_entetes(), json={"ref": "main"}, timeout=TIMEOUT)
    return r.status_code in (204, 201)
