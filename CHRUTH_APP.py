"""Application CHRUTH — point d'entree unique.

Les anciennes surfaces sont reunies dans une plateforme a huit pages : veille,
collecte, base de donnees, carte, messages et CRM, pilotage, reglages et mode developpeur.
Une seule adresse et un seul lancement suffisent.

Lancer :  streamlit run CHRUTH_APP.py   (ou double-clic LANCER_APP_CHRUTH.bat)
"""
from __future__ import annotations

import streamlit as st

import connexion
import theme_chruth

st.set_page_config(page_title="CHRUTH", layout="wide")


def page_de_connexion() -> None:
    """Ecran d'entree quand une authentification est configuree.

    On n'affiche rien d'autre : une page de connexion qui laisse deviner les
    donnees derriere elle n'est plus une page de connexion.
    """
    st.title("CHRUTH")
    st.caption("Veille des marchés publics de propreté en Île-de-France.")
    st.write("Cette application est réservée aux comptes autorisés.")
    st.button("Se connecter", type="primary", on_click=st.login)


def garde() -> bool:
    """Laisse passer, ou affiche l'ecran d'entree. Renvoie True si l'acces est ouvert.

    Sans fournisseur d'identite configure, la plateforme reste ouverte : c'est le
    mode poste local, ou la garde n'aurait rien a proteger et empecherait de
    travailler.
    """
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
    # L'accueil ouvre l'app : il s'appuie sur la base, qui est toujours peuplee,
    # la ou la veille peut legitimement etre vide entre deux passages — un premier
    # ecran vide se lit comme une panne.
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
