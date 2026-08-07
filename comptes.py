"""Identite et comptes : qui entre, sous quel nom, avec quel pouvoir.

Ce module repond aux questions d'identite de la plateforme, par-dessus
l'authentification Streamlit (Google) et l'espace membres (comptes locaux) :

- l'utilisateur courant : le compte Google connecte, une connexion locale
  enregistree en session, ou l'utilisateur du poste quand rien n'est configure ;
- le mot de passe des comptes locaux, hache avec scrypt (stdlib), jamais stocke
  en clair — seul le hachage vit dans l'espace chiffre du membre ;
- l'administration : en mode poste, tout le monde administre ; avec un
  fournisseur configure, seule la liste `[acces].admins` des secrets decide.

Les comptes locaux servent aux membres qui n'ont pas de compte Google. Leur
mot de passe est chiffre avec l'espace du membre (voir espace.py), donc illisible
par quiconque n'a pas la cle de chiffrement.
"""
from __future__ import annotations

import hashlib
import hmac
import os

import connexion
import espace

CLE_UTILISATEUR = "comptes.utilisateur"
DEFAUT_UTILISATEUR_LOCAL = "local@chruth"
LONGUEUR_MIN_MOT_DE_PASSE = 8

# Paramètres scrypt : memoire 16 Mo, derive unique par membre.
_SCOURT_N = 2**14
_SCOURT_R = 8
_SCOURT_P = 1


def normaliser(email: str) -> str:
    """Une adresse se compare sans casse ni espaces parasites."""
    return connexion.normaliser(email)


def _session(st) -> object:
    return st.session_state


def _auth_configuree(st) -> bool:
    return connexion.authentification_configuree(st.secrets)


def utilisateur_local_defaut() -> str:
    """L'utilisateur du poste quand aucun fournisseur n'est configure."""
    return os.environ.get("CHRUTH_UTILISATEUR_LOCAL", DEFAUT_UTILISATEUR_LOCAL) \
        .strip() or DEFAUT_UTILISATEUR_LOCAL


def utilisateur_courant(st) -> str:
    """L'adresse qui agit maintenant, ou une chaine vide si indeterminee.

    Ordre : connexion locale en session, puis compte Google, puis poste local
    sans authentification. La session prime toujours : un membre connecte sur
    un poste sans Google reste identifie par SON compte, pas par le defaut.
    """
    email = str(_session(st).get(CLE_UTILISATEUR) or "").strip()
    if email:
        return email
    user = getattr(st, "user", None)
    if user and getattr(user, "is_logged_in", False):
        return normaliser(user.email or "")
    if not _auth_configuree(st):
        return utilisateur_local_defaut()
    return ""


def est_connecte(st) -> bool:
    """Vrai si quelqu'un est identifie : compte Google ou connexion locale.

    Independant de la configuration `[auth]` : c'est ce que la garde doit
    verifier, y compris sur un poste sans fournisseur d'identite.
    """
    if getattr(st.user, "is_logged_in", False):
        return True
    return bool(str(_session(st).get(CLE_UTILISATEUR) or "").strip())


def connecter_local(st, email: str) -> str:
    """Enregistre une connexion locale dans la session."""
    email = normaliser(email)
    _session(st)[CLE_UTILISATEUR] = email
    return email


def deconnecter(st) -> None:
    """Oublie la connexion locale en session."""
    _session(st)[CLE_UTILISATEUR] = None


def est_admin_courant(st) -> bool:
    """Vrai si l'utilisateur courant administre.

    Une liste `[acces].admins` fait toujours foi, qu'un fournisseur soit
    configure ou non. Sans liste : le poste sans authentification administre
    par defaut (tout compte local connecte), et avec un fournisseur personne ne
    l'est — une liste vide n'accorde jamais l'administration.
    """
    _, admins = connexion.lire_acces(st.secrets)
    if admins:
        return connexion.est_admin(utilisateur_courant(st), admins)
    return not _auth_configuree(st)


def identite(st) -> dict[str, str]:
    """Nom et photo affichables de l'utilisateur courant."""
    email = utilisateur_courant(st)
    user = getattr(st, "user", None)
    if user and getattr(user, "is_logged_in", False) and \
            normaliser(user.email or "") == email:
        return {"email": email, "nom": user.name or "", "photo": user.picture or ""}
    profil = espace.profil(email) if email else {}
    return {"email": email, "nom": profil.get("nom_affiche") or "", "photo": ""}


# --- Mots de passe des comptes locaux ---------------------------------------

def hacher(mot_de_passe: str) -> str:
    """Hache un mot de passe avec scrypt, sel aleatoire par appel.

    Format : scrypt$n$r$p$sel$empreinte, de quoi reverifier sans reconfiguration.
    """
    sel = os.urandom(16)
    empreinte = hashlib.scrypt(
        str(mot_de_passe).encode("utf-8"),
        salt=sel, n=_SCOURT_N, r=_SCOURT_R, p=_SCOURT_P, dklen=32)
    return f"scrypt${_SCOURT_N}${_SCOURT_R}${_SCOURT_P}${sel.hex()}${empreinte.hex()}"


def verifier_mot_de_passe(mot_de_passe: str, hachage: str) -> bool:
    """Vrai si le mot de passe correspond au hachage stocke."""
    parties = str(hachage or "").split("$")
    if len(parties) != 6 or parties[0] != "scrypt":
        return False
    try:
        n, r, p = int(parties[1]), int(parties[2]), int(parties[3])
        sel = bytes.fromhex(parties[4])
        attendu = bytes.fromhex(parties[5])
    except (ValueError, TypeError):
        return False
    try:
        calcule = hashlib.scrypt(
            str(mot_de_passe).encode("utf-8"),
            salt=sel, n=n, r=r, p=p, dklen=len(attendu))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(calcule, attendu)


# --- Comptes locaux ----------------------------------------------------------

def _email_valide(email: str) -> bool:
    """Forme minimale d'une adresse : locale@domaine avec un point au domaine."""
    local, separateur, domaine = email.partition("@")
    if not separateur or not local or not domaine:
        return False
    if "@" in domaine or local.startswith(".") or domaine.startswith("."):
        return False
    return "." in domaine


def creer_compte_local(email: str, nom: str, mot_de_passe: str) -> str:
    """Cree un compte local : espace membre, hachage du mot de passe, nom.

    Rejette une adresse invalide ou un mot de passe trop court. Ne stocke que
    le hachage : le mot de passe en clair ne quitte jamais cette fonction.
    """
    email = normaliser(email)
    if not _email_valide(email):
        raise ValueError(f"adresse invalide : {email}")
    if len(str(mot_de_passe or "")) < LONGUEUR_MIN_MOT_DE_PASSE:
        raise ValueError(
            f"mot de passe trop court (minimum {LONGUEUR_MIN_MOT_DE_PASSE} caracteres)")
    espace.creer(email)
    espace.definir_mot_de_passe(email, hacher(mot_de_passe))
    espace.enregistrer_profil(email, {"nom_affiche": str(nom or "").strip()})
    return email


def authentifier_local(email: str, mot_de_passe: str) -> bool:
    """Vrai si le couple adresse/mot de passe est valide.

    Refuse un compte inconnu, desactive, ou sans mot de passe enregistre.
    """
    email = normaliser(email)
    if not espace.existe(email):
        return False
    if not espace.actif(email):
        return False
    hachage = espace.mot_de_passe(email)
    if not hachage:
        return False
    return verifier_mot_de_passe(mot_de_passe, hachage)
