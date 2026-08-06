"""Espace membres : les donnees personnelles d'un utilisateur, et rien que lui.

Chaque membre a un fichier propre et chiffre (voir espace_depot). Ce module
porte le schema de l'espace et les operations par membre : profil, preferences,
appels d'offres suivis et notes privees, messages conserves, journal
d'activite, compte local.

Ce qui relève de la veille (verdicts, scores, reglages) reste commun et vit
ailleurs. Ici, uniquement ce qui appartient a la personne.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import espace_depot

ESPACE_VERSION = 1
STATUTS_SUIVI = ("a_voir", "favori", "mis_de_cote")
JOURNAL_MAX = 100
MESSAGES_MAX = 50

DEFAUTS: dict[str, Any] = {
    "version": ESPACE_VERSION,
    "cree_le": "",
    "actif": True,
    "mot_de_passe": "",
    "profil": {"nom_affiche": "", "role": "", "telephone": "", "signature": ""},
    "preferences": {"departements": [], "priorites": [], "periode": "Tout",
                    "page_accueil": "Accueil", "densite": "confortable"},
    "aos": {},
    "messages": [],
    "journal": [],
}

CHAMPS_PROFIL = ("nom_affiche", "role", "telephone", "signature")
CHAMPS_PREFERENCES = ("departements", "priorites", "periode", "page_accueil", "densite")


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normaliser(membre: dict[str, Any]) -> dict[str, Any]:
    """Complete une lecture avec les valeurs par defaut, sections incluses."""
    source = membre or {}
    resultat: dict[str, Any] = {}
    for cle, defaut in DEFAUTS.items():
        if cle in ("profil", "preferences"):
            section = dict(defaut)
            section.update(source.get(cle) or {})
            resultat[cle] = section
        elif cle == "aos":
            resultat[cle] = source.get("aos") or {}
        elif cle in ("messages", "journal"):
            resultat[cle] = list(source.get(cle) or [])
        else:
            resultat[cle] = source.get(cle, defaut)
    return resultat


def _membre(email: str) -> dict[str, Any]:
    return _normaliser(espace_depot.lire_membre(email))


def _ecrire(email: str, membre: dict[str, Any]) -> dict[str, Any]:
    espace_depot.ecrire_membre(email, membre, "espace membres")
    return membre


# --- Cycle de vie du membre -------------------------------------------------

def existe(email: str) -> bool:
    """Vrai si le membre a deja ete cree (horodatage present)."""
    return bool(_membre(email)["cree_le"])


def creer(email: str) -> dict[str, Any]:
    """Cree l'espace du membre s'il n'existe pas encore. Idempotent."""
    if existe(email):
        return _membre(email)
    membre = _normaliser({})
    membre["cree_le"] = _maintenant()
    return _ecrire(email, membre)


def lister_membres() -> list[str]:
    return espace_depot.lister_membres()


def supprimer(email: str) -> None:
    """Suppression complete de l'espace : depart d'un membre."""
    espace_depot.supprimer_membre(email)


def actif(email: str) -> bool:
    return bool(_membre(email)["actif"])


def desactiver(email: str) -> None:
    membre = _membre(email)
    membre["actif"] = False
    _ecrire(email, membre)


def reactiver(email: str) -> None:
    membre = _membre(email)
    membre["actif"] = True
    _ecrire(email, membre)


def definir_mot_de_passe(email: str, hachage: str) -> None:
    """Stocke le hachage. Ne jamais recevoir le mot de passe en clair ici."""
    membre = _membre(email)
    membre["mot_de_passe"] = str(hachage or "")
    _ecrire(email, membre)


def mot_de_passe(email: str) -> str:
    return str(_membre(email)["mot_de_passe"] or "")


# --- Profil et preferences --------------------------------------------------

def profil(email: str) -> dict[str, str]:
    return dict(_membre(email)["profil"])


def enregistrer_profil(email: str, champs: dict[str, str]) -> dict[str, str]:
    membre = _membre(email)
    for cle in CHAMPS_PROFIL:
        if cle in champs:
            membre["profil"][cle] = str(champs.get(cle) or "").strip()
    _ecrire(email, membre)
    return dict(membre["profil"])


def preferences(email: str) -> dict[str, Any]:
    return dict(_membre(email)["preferences"])


def enregistrer_preferences(email: str, champs: dict[str, Any]) -> dict[str, Any]:
    membre = _membre(email)
    for cle in CHAMPS_PREFERENCES:
        if cle in champs:
            membre["preferences"][cle] = champs.get(cle)
    _ecrire(email, membre)
    return dict(membre["preferences"])


# --- Appels d'offres suivis et notes ----------------------------------------

def _entree_ao(membre: dict[str, Any], id_ao: str) -> dict[str, Any]:
    return membre["aos"].setdefault(str(id_ao), {"statut": "", "note": ""})


def statut_ao(email: str, id_ao: str) -> str:
    return str(_membre(email)["aos"].get(str(id_ao), {}).get("statut") or "")


def definir_statut_ao(email: str, id_ao: str, statut: str) -> str:
    if statut not in ("", *STATUTS_SUIVI):
        raise ValueError(f"statut inconnu : {statut} (attendus : {STATUTS_SUIVI})")
    membre = _membre(email)
    _entree_ao(membre, id_ao)["statut"] = statut
    _ecrire(email, membre)
    return statut


def note_ao(email: str, id_ao: str) -> str:
    return str(_membre(email)["aos"].get(str(id_ao), {}).get("note") or "")


def sauver_note_ao(email: str, id_ao: str, note: str) -> str:
    membre = _membre(email)
    _entree_ao(membre, id_ao)["note"] = str(note or "").strip()
    _ecrire(email, membre)
    return str(note or "").strip()


def effacer_note_ao(email: str, id_ao: str) -> None:
    membre = _membre(email)
    entree = _entree_ao(membre, id_ao)
    entree["note"] = ""
    _ecrire(email, membre)


def aos(email: str) -> dict[str, dict[str, str]]:
    """Les AO suivis ou annotes : {id_ao: {"statut":..., "note":...}}."""
    return {id_ao: {"statut": str(e.get("statut") or ""), "note": str(e.get("note") or "")}
            for id_ao, e in _membre(email)["aos"].items()}


# --- Messages conserves -----------------------------------------------------

def messages(email: str) -> list[dict[str, str]]:
    return [dict(m) for m in _membre(email)["messages"]]


def ajouter_message(email: str, message: dict[str, str]) -> list[dict[str, str]]:
    membre = _membre(email)
    net = {cle: str(message.get(cle) or "") for cle in
           ("objet", "email", "script", "source", "le")}
    net["le"] = net["le"] or _maintenant()
    membre["messages"].insert(0, net)
    membre["messages"] = membre["messages"][:MESSAGES_MAX]
    _ecrire(email, membre)
    return [dict(m) for m in membre["messages"]]


def supprimer_message(email: str, index: int) -> list[dict[str, str]]:
    membre = _membre(email)
    try:
        membre["messages"].pop(index)
    except IndexError:
        pass
    _ecrire(email, membre)
    return [dict(m) for m in membre["messages"]]


# --- Journal d'activite -----------------------------------------------------

def journal(email: str) -> list[dict[str, str]]:
    """Activite du membre, plus recente d'abord."""
    return [dict(e) for e in reversed(_membre(email)["journal"])]


def noter(email: str, evenement: str) -> list[dict[str, str]]:
    membre = _membre(email)
    membre["journal"].append({"le": _maintenant(), "evenement": str(evenement or "")})
    membre["journal"] = membre["journal"][-JOURNAL_MAX:]
    _ecrire(email, membre)
    return [dict(e) for e in reversed(membre["journal"])]
