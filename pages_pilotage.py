"""Page Pilotage — les KPI du cockpit Excel, dans la plateforme.

Aucun calcul propre : les chiffres viennent de ao_pilotage.compute_kpis, la meme
fonction qui alimente l'onglet Pilotage du tableur. Deux surfaces, un seul calcul.
"""
from __future__ import annotations

import streamlit as st

import ao_db
import ao_pilotage

try:
    st.set_page_config(page_title="Pilotage CHRUTH", page_icon="🧹", layout="wide")
except st.errors.StreamlitAPIException:
    pass

st.title("Pilotage")

df = ao_db.fetch_records()
kpis = ao_pilotage.compute_kpis(df)

colonnes = st.columns(4)
colonnes[0].metric("Appels d'offres", str(kpis["nb_ao"]))
colonnes[1].metric("Chauds", str(kpis["nb_chauds"]))
colonnes[2].metric("Île-de-France", str(kpis["nb_idf"]))
colonnes[3].metric("Budget à vérifier", str(kpis["budget_a_verifier"]))

st.caption(f"Mise à jour : {kpis['date_maj']} · contrôle qualité : {kpis['check_qualite']}")

if df.empty:
    st.info("Aucun appel d'offres en base. Lancer une mise à jour depuis la page Veille.")
