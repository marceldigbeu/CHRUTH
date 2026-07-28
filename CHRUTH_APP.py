"""Application CHRUTH — point d'entree unique.

Les anciennes surfaces sont reunies dans une plateforme a huit pages : veille,
collecte, base de donnees, carte, messages et CRM, pilotage, reglages et mode developpeur.
Une seule adresse et un seul lancement suffisent.

Lancer :  streamlit run CHRUTH_APP.py   (ou double-clic LANCER_APP_CHRUTH.bat)
"""
from __future__ import annotations

import streamlit as st

import theme_chruth

st.set_page_config(page_title="CHRUTH", layout="wide")

theme_chruth.appliquer()

PAGES = [
    st.Page("app_veille.py", title="Veille appels d'offres", default=True),
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
