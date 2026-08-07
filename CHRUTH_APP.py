"""Application CHRUTH — point d'entrée unique."""
from __future__ import annotations

import streamlit as st

import comptes
import connexion
import espace
import theme_chruth

st.set_page_config(
    page_title="CHRUTH · Veille marchés publics",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _deconnecter() -> None:
    """Ferme la connexion locale, puis le fournisseur Google s'il est ouvert."""
    comptes.deconnecter(st)
    try:
        if getattr(st.user, "is_logged_in", False):
            st.logout()
    except Exception:  # noqa: BLE001 — pas de session Google a fermer
        pass


def _creer_compte_local(email: str, nom: str, mdp: str) -> None:
    try:
        comptes.creer_compte_local(email, nom, mdp)
        st.success("Compte créé. Renseigne la même adresse ci-dessus pour te connecter.")
    except ValueError as exc:
        st.error(str(exc))


def page_de_connexion() -> None:
    """Écran d'entrée, avant tout accès à la plateforme.

    Deux portes : le fournisseur Google (s'il est configuré), et un compte
    local pour les membres sans compte Google. La création d'un compte local
    n'ouvre pas l'accès : l'adresse doit ensuite figurer dans `[acces]` des
    secrets pour entrer — seul l'administrateur l'y met.
    """
    st.markdown('<div class="chruth-kicker">Accès sécurisé</div>', unsafe_allow_html=True)
    st.title("CHRUTH")
    st.caption("Veille des marchés publics de propreté en Île-de-France.")
    st.write("Cette application est réservée aux comptes autorisés.")
    if connexion.authentification_configuree(st.secrets):
        st.button("Se connecter avec Google", type="primary", on_click=st.login)
        st.divider()

    st.subheader("Compte CHRUTH")
    st.caption("Pour les membres sans compte Google. Le mot de passe reste "
               "stocké haché, dans l'espace chiffré de chacun.")
    with st.form("connexion_locale"):
        email = st.text_input("Adresse email")
        mdp = st.text_input("Mot de passe", type="password")
        soumettre = st.form_submit_button("Se connecter", type="primary")
        if soumettre:
            email = comptes.normaliser(email)
            if comptes.authentifier_local(email, mdp):
                comptes.connecter_local(st, email)
                st.rerun()
            else:
                st.error("Adresse ou mot de passe inconnu.")

    with st.expander("Créer un compte local"):
        st.caption("Aucun compte encore ? Crée le tien : adresse, nom affiché "
                   "et mot de passe.")
        c_email = st.text_input("Adresse email", key="creer_email")
        c_nom = st.text_input("Nom affiché", key="creer_nom")
        c_mdp = st.text_input("Mot de passe (8 caractères minimum)",
                              type="password", key="creer_mdp")
        st.button("Créer le compte", on_click=_creer_compte_local,
                  args=(c_email, c_nom, c_mdp))


def garde() -> bool:
    """Laisse passer, ou affiche l'écran d'entrée. Renvoie True si l'accès est ouvert.

    La connexion est exigée dans tous les modes : Google quand un fournisseur
    est configuré, compte local sinon. Sans identification, rien ne s'affiche.
    """
    if not comptes.est_connecte(st):
        page_de_connexion()
        return False

    email = comptes.utilisateur_courant(st)
    autorises, admins = connexion.lire_acces(st.secrets)
    if not connexion.est_autorise(email, autorises):
        st.error(connexion.message_refus(email, admins))
        st.button("Se déconnecter", on_click=_deconnecter)
        return False

    with st.sidebar:
        st.caption(f"Connecté : {email}")
        if comptes.est_admin_courant(st):
            st.caption("Administrateur")
        st.button("Se déconnecter", on_click=_deconnecter, key="deconnexion")
    return True


if not garde():
    st.stop()

theme_chruth.appliquer()

PAGES_DEF = [
    ("pages_accueil.py", "Accueil"),
    ("app_veille.py", "Veille appels d'offres"),
    ("pages_collecte.py", "Collecte"),
    ("pages_donnees.py", "Base de données"),
    ("pages_acheteurs.py", "Acheteurs de la semaine"),
    ("pages_carte.py", "Carte"),
    ("app_messages.py", "Messages et CRM"),
    ("pages_pilotage.py", "Pilotage"),
    ("pages_reglages.py", "Réglages"),
    ("pages_developpeur.py", "Développeur"),
    ("mes_ao.py", "Mes appels d'offres"),
    ("mes_messages.py", "Mes messages"),
    ("mon_espace.py", "Mon espace"),
    ("administration.py", "Administration"),
]

_TITRES = [titre for _, titre in PAGES_DEF]


def page_accueil_preferee() -> str:
    """Page d'accueil demandée par le membre, « Accueil » sinon.

    Lecture tolérante : sans membre, sans clé de chiffrement ou sur toute autre
    erreur de lecture, on garde la page par défaut de la plateforme.
    """
    try:
        email = comptes.utilisateur_courant(st)
        if not email:
            return "Accueil"
        pref = str(espace.preferences(email).get("page_accueil") or "Accueil")
    except Exception:  # noqa: BLE001
        return "Accueil"
    return pref if pref in _TITRES else "Accueil"


def _construire_pages() -> list:
    pref = page_accueil_preferee()
    return [st.Page(chemin, title=titre, default=(titre == pref))
            for chemin, titre in PAGES_DEF]


st.navigation(_construire_pages()).run()
