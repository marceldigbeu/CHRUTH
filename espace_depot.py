"""Acces au stockage de l'espace membres : fichier local ou branche dediee.

Miroir de veille_depot.py pour des donnees PERSONNELLES. Trois differences :

- un fichier PAR MEMBRE, jamais un etat global : deux utilisateurs n'ecrivent
  jamais le meme fichier, donc pas de conflit d'ecriture entre personnes ;
- une branche dediee `espace-membres`, jamais la branche d'etat ao-state ;
- chaque fichier est chiffre (Fernet). La cle vit dans les secrets Streamlit
  (en ligne) ou dans un fichier local ignore par git (poste). Un lecteur du
  depot ne voit que du chiffre : les notes d'un membre ne sont lisibles par
  personne d'autre, pas meme par qui a acces au depot.

Sans cle, le poste local en genere une a la premiere ecriture (fichier
`espace/cle_locale.key`, ignore par git). En ligne, l'absence de cle refuse
l'ecriture plutot que de stocker des donnees en clair.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import requests
from cryptography.fernet import Fernet, InvalidToken

API = "https://api.github.com"
CHEMIN_ESPACE = "etat/espace_membres"
TIMEOUT = 20

_cle_forcee: str | None = None


def source() -> str:
    """'github' ou 'local' (defaut). Le poste local n'a besoin d'aucune configuration."""
    return "github" if os.environ.get("CHRUTH_ESPACE_SOURCE", "").strip().lower() == "github" \
        else "local"


def _depot() -> str:
    return os.environ.get("CHRUTH_GITHUB_REPO", "").strip()


def _branche() -> str:
    return os.environ.get("CHRUTH_ESPACE_BRANCHE", "espace-membres").strip()


def _jeton() -> str:
    return os.environ.get("CHRUTH_GITHUB_TOKEN", "").strip()


def dossier_local() -> Path:
    """Dossier des fichiers membres locaux (chiffres). Surchargable en test."""
    defaut = Path(__file__).resolve().parent / "espace" / "membres"
    return Path(os.environ.get("CHRUTH_ESPACE_DIR") or defaut)


def _chemin_cle() -> Path:
    return dossier_local().parent / "cle_locale.key"


def definir_cle(chaine: str) -> None:
    """Injection d'une cle Fernet depuis les secrets Streamlit (en ligne).

    Les secrets TOML ne sont pas des variables d'environnement : sans ce pont,
    la cle saissie dans `.streamlit/secrets.toml` ne serait jamais lue.
    """
    global _cle_forcee
    _cle_forcee = (chaine or "").strip() or None


def _reinitialiser_cle() -> None:
    """Oublie la cle forcee. Reserve aux tests."""
    global _cle_forcee
    _cle_forcee = None


def _cle(creer: bool = False) -> bytes | None:
    """Cle Fernet : forcee, environnment, fichier local, sinon genere si local."""
    if _cle_forcee:
        return _cle_forcee.encode()
    env = os.environ.get("CHRUTH_ESPACE_CLE", "").strip()
    if env:
        return env.encode()
    fichier = _chemin_cle()
    if fichier.exists():
        try:
            return fichier.read_text(encoding="utf-8").strip().encode()
        except OSError:
            return None
    if creer and source() == "local":
        cle = Fernet.generate_key()
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text(cle.decode(), encoding="utf-8")
        return cle
    return None


def cle_disponible() -> bool:
    """Vrai si une cle est resolue, sans en creer une."""
    return _cle(creer=False) is not None


def chiffrer(payload: dict[str, Any]) -> bytes:
    """Payload -> octets chiffres, pret pour le disque ou l'API GitHub.

    En local, la cle est generee a la demande (premiere ecriture). Sur GitHub,
    l'absence de cle est une erreur : on ne chiffre jamais en clair.
    """
    cle = _cle(creer=True)
    if cle is None:
        raise RuntimeError(
            "Cle de chiffrement absente : renseigner CHRUTH_ESPACE_CLE ou "
            "[espace].cle_chiffrement avant de stocker des donnees personnelles.")
    brut = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return Fernet(cle).encrypt(brut)


def dechiffrer(blob: bytes) -> dict[str, Any]:
    """Octets chiffres -> payload. Erreur claire si cle absente ou invalide."""
    if not cle_disponible():
        raise RuntimeError(
            "Cle de chiffrement absente : renseigner CHRUTH_ESPACE_CLE ou "
            "[espace].cle_chiffrement pour lire les donnees personnelles.")
    try:
        brut = Fernet(_cle()).decrypt(blob)
    except InvalidToken as exc:
        raise RuntimeError("Espace membres illisible : cle invalide ou donnees corrompues.") \
            from exc
    try:
        data = json.loads(brut)
    except Exception:  # noqa: BLE001
        raise RuntimeError("Espace membres illisible : contenu non JSON.")
    return data if isinstance(data, dict) else {}


# --- Fichiers par membre ----------------------------------------------------

def _nom_fichier(email: str) -> str:
    """Nom de fichier : l'adresse encodee en hexadécimal, sans caractere genant."""
    return email.encode("utf-8").hex() + ".enc"


def _email_depuis_fichier(nom: str) -> str:
    if not nom.endswith(".enc"):
        raise ValueError(f"fichier membre inattendu : {nom}")
    return bytes.fromhex(nom[:-4]).decode("utf-8")


def _fichier_local(email: str) -> Path:
    return dossier_local() / _nom_fichier(email)


def _entetes() -> dict[str, str]:
    entetes = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    if _jeton():
        entetes["Authorization"] = f"Bearer {_jeton()}"
    return entetes


def _url_membre(email: str) -> str:
    return f"{API}/repos/{_depot()}/contents/{CHEMIN_ESPACE}/{_nom_fichier(email)}?ref={_branche()}"


def _url_put(email: str) -> str:
    return f"{API}/repos/{_depot()}/contents/{CHEMIN_ESPACE}/{_nom_fichier(email)}"


def _url_liste() -> str:
    return f"{API}/repos/{_depot()}/contents/{CHEMIN_ESPACE}?ref={_branche()}"


def ecriture_possible() -> bool:
    """En local, toujours. Sur GitHub, seulement avec jeton et cle."""
    if source() == "local":
        return True
    return bool(_jeton() and _depot()) and cle_disponible()


def _sha_github(email: str) -> str | None:
    r = requests.get(_url_membre(email), headers=_entetes(), timeout=TIMEOUT)
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise RuntimeError(f"lecture de l'espace membre impossible (HTTP {r.status_code})")
    return r.json().get("sha")


def lire_membre(email: str) -> dict[str, Any]:
    """Espace du membre, ou dictionnaire vide si absent ou jamais cree."""
    if source() == "local":
        fichier = _fichier_local(email)
        if not fichier.exists():
            return {}
        return dechiffrer(fichier.read_bytes())
    r = requests.get(_url_membre(email), headers=_entetes(), timeout=TIMEOUT)
    if r.status_code == 404:
        return {}
    if r.status_code != 200:
        raise RuntimeError(f"lecture de l'espace membre impossible (HTTP {r.status_code})")
    return dechiffrer(base64.b64decode(r.json().get("content", "")))


def _put(email: str, payload: dict[str, Any], sha: str | None, message: str):
    corps = {
        "message": message,
        "content": base64.b64encode(chiffrer(payload)).decode(),
        "branch": _branche(),
    }
    if sha:
        corps["sha"] = sha
    return requests.put(_url_put(email), headers=_entetes(), json=corps, timeout=TIMEOUT)


def ecrire_membre(email: str, payload: dict[str, Any],
                  message: str = "espace membres") -> None:
    """Enregistre l'espace d'un membre. Sur conflit, relit puis reessaie une fois."""
    if not ecriture_possible():
        raise PermissionError(
            "Ecriture de l'espace membres impossible : en ligne, renseigner "
            "CHRUTH_GITHUB_REPO, CHRUTH_GITHUB_TOKEN et la cle de chiffrement "
            "(CHRUTH_ESPACE_CLE ou [espace].cle_chiffrement).")
    if source() == "local":
        fichier = _fichier_local(email)
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_bytes(chiffrer(payload))
        return
    sha = _sha_github(email)
    r = _put(email, payload, sha, message)
    if r.status_code in (409, 422):
        # Un autre ecran a ecrit entre notre lecture et notre ecriture.
        r = _put(email, payload, _sha_github(email), message)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"ecriture de l'espace membre refusee (HTTP {r.status_code})")


def lister_membres() -> list[str]:
    """Adresses de tous les membres, ordonnees."""
    if source() == "local":
        dossier = dossier_local()
        if not dossier.exists():
            return []
        emails = []
        for fichier in sorted(dossier.glob("*.enc")):
            try:
                emails.append(_email_depuis_fichier(fichier.name))
            except (ValueError, UnicodeDecodeError):
                continue
        return emails
    r = requests.get(_url_liste(), headers=_entetes(), timeout=TIMEOUT)
    if r.status_code == 404:
        return []
    if r.status_code != 200:
        raise RuntimeError(f"liste de l'espace membres impossible (HTTP {r.status_code})")
    emails = []
    for entree in r.json():
        try:
            emails.append(_email_depuis_fichier(entree.get("name", "")))
        except (ValueError, UnicodeDecodeError):
            continue
    return sorted(emails)


def supprimer_membre(email: str) -> None:
    """Supprime l'espace d'un membre. Absence du fichier = rien a faire."""
    if not ecriture_possible():
        raise PermissionError("Suppression impossible : ecriture non configuree.")
    if source() == "local":
        try:
            _fichier_local(email).unlink()
        except FileNotFoundError:
            pass
        return
    sha = _sha_github(email)
    if sha is None:
        return
    r = requests.delete(
        _url_put(email), headers=_entetes(),
        json={"message": "suppression espace membre", "sha": sha, "branch": _branche()},
        timeout=TIMEOUT)
    if r.status_code not in (200, 204):
        raise RuntimeError(f"suppression de l'espace membre refusee (HTTP {r.status_code})")
