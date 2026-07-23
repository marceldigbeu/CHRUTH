"""Application CHRUTH — point d'entree unique.

Deux surfaces web coexistaient (veille et messages), chacune lancee a part et
chacune sur le port 8501 : la seconde ne pouvait pas demarrer pendant la premiere.
Elles sont ici deux pages d'une meme application, une seule adresse, un seul
lancement.

Lancer :  streamlit run CHRUTH_APP.py   (ou double-clic LANCER_APP_CHRUTH.bat)
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="CHRUTH", page_icon="🧹", layout="wide")

PAGES = [
    st.Page("app_veille.py", title="Veille appels d'offres", icon="📡", default=True),
    st.Page("app_messages.py", title="Messages et CRM", icon="📨"),
]

st.navigation(PAGES).run()
