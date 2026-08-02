"""Application CHRUTH — point d'entrée unique."""
from __future__ import annotations

import streamlit as st

import connexion
import theme_chruth

st.set_page_config(
    page_title="CHRUTH · Veille marchés publics",
    layout="wide",
    initial_sidebar_state="expanded",
)


def page_de_connexion() -> None:
    """Écran d'entrée quand une authentification est configurée."""
    st.markdown('<div class="chruth-kicker">Accès sécurisé</div>', unsafe_allow_html=True)
    st.title("CHRUTH")
    st.caption("Veille des marchés publics de propreté en Île-de-France.")
    st.write("Cette application est réservée aux comptes autorisés.")
    st.button("Se connecter", type="primary", on_click=st.login)


def garde() -> bool:
    """Laisse passer, ou affiche l'écran d'entrée. Renvoie True si l'accès est ouvert."""
    if not connexion.authentification_configuree(st.secrets):
        return True

    if not getattr(st.user, "is_logged_in", False):
        page_de_connexion()
        return False

    autorises, admins = connexion.lire_acces(st.secrets)
    email = getattr(st.user, "email", "") or ""
    if not connexion.est_autorise(email, autorises):
        st.error(connexion.message_refus(email, admins))
        st.button("Se déconnecter", on_click=st.logout)
        return False

    with st.sidebar:
        st.caption(f"Connecté : {email}")
        if connexion.est_admin(email, admins):
            st.caption("Administrateur")
        st.button("Se déconnecter", on_click=st.logout, key="deconnexion")
    return True


if not garde():
    st.stop()

theme_chruth.appliquer()

PAGES = [
    st.Page("pages_accueil.py", title="Accueil", default=True),
    st.Page("app_veille.py", title="Veille appels d'offres"),
    st.Page("pages_collecte.py", title="Collecte"),
    st.Page("pages_donnees.py", title="Base de données"),
    st.Page("pages_acheteurs.py", title="Acheteurs de la semaine"),
    st.Page("pages_carte.py", title="Carte"),
    st.Page("app_messages.py", title="Messages et CRM"),
    st.Page("pages_pilotage.py", title="Pilotage"),
    st.Page("pages_reglages.py", title="Réglages"),
    st.Page("pages_developpeur.py", title="Développeur"),
]

st.navigation(PAGES).run()
