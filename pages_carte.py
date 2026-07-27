"""Carte interactive des prospects integree a Streamlit."""
from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import livrables_chruth as livrables

try:
    st.set_page_config(page_title="Carte CHRUTH", layout="wide")
except st.errors.StreamlitAPIException:
    pass


@st.cache_data(show_spinner=False)
def lire_carte(chemin: str, _modifie: int) -> str:
    return Path(chemin).read_text(encoding="utf-8", errors="replace") if chemin else ""


st.title("Carte des prospects")
carte = livrables.fichier("Carte_Prospects_CHRUTH.html")

if not carte.exists():
    st.error(f"Carte introuvable : {carte}")
    st.caption("Regenerer les prospects pour recreer Carte_Prospects_CHRUTH.html.")
else:
    info = livrables.informations(carte)
    c1, c2, c3 = st.columns(3)
    c1.metric("Taille", livrables.taille_humaine(int(info["taille"])))
    c2.metric("Derniere mise a jour", str(info["modifie"]))
    c3.metric("Source", "Livraison no-code" if "Downloads" in str(carte) else "Depot")
    st.caption("La carte conserve ses clusters, filtres, rayons, recherche et itineraires. "
               "Une connexion Internet est requise pour les fonds OpenStreetMap.")

    html = lire_carte(str(carte), carte.stat().st_mtime_ns)
    components.html(html, height=780, scrolling=False)
    st.download_button("Telecharger la carte HTML", carte.read_bytes(),
                       file_name=carte.name, mime="text/html")
