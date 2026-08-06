"""Controle d'acces a la plateforme, adosse a l'authentification Streamlit.

Aucun mot de passe n'est stocke ni envoye ici, et c'est deliberé : `st.login`
delegue l'identification a un fournisseur (Google, Microsoft) qui gere deja les
mots de passe, la double authentification et les tentatives de fraude. Ce module
ne repond qu'a une question — cette adresse email a-t-elle le droit d'entrer.

L'administrateur est le seul a pouvoir repondre, parce que la liste vit dans
`.streamlit/secrets.toml`, hors de l'application : un droit d'acces modifiable
depuis l'application protegee ne protege rien.

La connexion est exigee dans tous les modes. Sans fournisseur configure, ce
sont les comptes locaux (voir comptes.py) qui protegent l'entree : chacun se
connecte avec son adresse et son mot de passe, haché dans son espace membre.
"""
from __future__ import annotations

from typing import Iterable

SECTION_AUTH = "auth"
SECTION_ACCES = "acces"


def normaliser(email: str) -> str:
    """Une adresse se compare sans casse ni espaces parasites."""
    return str(email or "").strip().casefold()


def est_autorise(email: str, autorises: Iterable[str]) -> bool:
    """Vrai si l'adresse figure dans la liste.

    Une liste vide autorise tout compte authentifie : c'est le reglage utile
    quand on veut seulement savoir qui entre, sans restreindre. Une adresse
    vide, elle, n'entre jamais — un compte sans email n'est pas identifiable.
    """
    liste = [normaliser(a) for a in autorises if str(a or "").strip()]
    adresse = normaliser(email)
    if not adresse:
        return False
    return True if not liste else adresse in liste


def est_admin(email: str, admins: Iterable[str]) -> bool:
    """Vrai si l'adresse est administratrice. Sans liste, personne ne l'est.

    Contrairement a l'acces, l'absence de liste ne vaut pas permission : un
    droit d'administration accorde par defaut serait accorde a tort.
    """
    liste = [normaliser(a) for a in admins if str(a or "").strip()]
    adresse = normaliser(email)
    return bool(adresse) and adresse in liste


def lire_acces(secrets) -> tuple[list[str], list[str]]:
    """Listes (autorises, admins) telles que l'administrateur les a ecrites.

    Tolerant a l'absence de fichier de secrets comme a une section manquante :
    un poste local n'en a pas, et la plateforme doit y demarrer quand meme.
    """
    try:
        section = secrets[SECTION_ACCES]
    except Exception:  # noqa: BLE001 — pas de secrets.toml, ou pas de section
        return [], []
    autorises = list(section.get("emails", []) or [])
    admins = list(section.get("admins", []) or [])
    return autorises, admins


def authentification_configuree(secrets) -> bool:
    """Vrai si un fournisseur d'identite est configure pour `st.login`."""
    try:
        return bool(secrets[SECTION_AUTH])
    except Exception:  # noqa: BLE001
        return False


def message_refus(email: str, admins: Iterable[str]) -> str:
    """Message affiche a qui s'authentifie sans figurer dans la liste.

    On nomme l'administrateur a contacter : un refus sans recours transforme un
    reglage a corriger en impasse.
    """
    contacts = ", ".join(a for a in admins if str(a or "").strip())
    base = f"Le compte {email} n'a pas accès à cette application."
    return f"{base} Demander l'ouverture à : {contacts}." if contacts else base
