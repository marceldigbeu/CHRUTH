"""Page Pilotage — les KPI du cockpit Excel, dans la plateforme.

Aucun calcul propre : les chiffres viennent de ao_pilotage.compute_kpis, la meme
fonction qui alimente l'onglet Pilotage du tableur. Deux surfaces, un seul calcul.
"""
from __future__ import annotations

import streamlit as st

import ao_db
import ao_pilotage
import veille_depot

try:
    st.set_page_config(page_title="Pilotage CHRUTH", layout="wide")
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
    if veille_depot.source() == "github":
        # En ligne, la base SQLite n'existe pas : elle est locale et gitignoree.
        # Renvoyer vers « Mettre a jour maintenant » serait un mensonge — ce bouton
        # declenche le workflow, qui remplit l'etat partage, jamais cette base.
        st.info("Ces indicateurs viennent de la base **locale** du poste, qui n'est pas "
                "publiée en ligne. Ils s'affichent depuis l'application lancée sur le PC. "
                "Le suivi des appels d'offres en ligne se trouve sur la page Veille.")
    else:
        st.info("Aucun appel d'offres en base. Lancer une mise à jour depuis la page Veille.")
