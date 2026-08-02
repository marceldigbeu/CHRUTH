"""Page Pilotage — l'etat de la veille, et ce qu'elle laisse a faire.

Les quatre KPI historiques viennent toujours d'`ao_pilotage.compute_kpis`, la
meme fonction qui alimente l'onglet Pilotage du tableur : deux surfaces, un seul
calcul. Le reste vient de `pilotage`, et n'existe que sur cette page.

Ce que la page ne montre pas, deliberement : un entonnoir commercial. Les
colonnes de suivi (statut de contact, date de contact, RDV) sont vides dans la
base — un tel bloc n'afficherait que des zeros, ce qui se lit comme une panne.
L'entonnoir de collecte, lui, est entierement renseigne par le journal.
"""
from __future__ import annotations

import streamlit as st

import ao_db
import ao_pilotage
import pilotage
import veille_depot

try:
    st.set_page_config(page_title="Pilotage CHRUTH", layout="wide")
except st.errors.StreamlitAPIException:
    pass

st.title("Pilotage")

df = ao_db.fetch_records()
kpis = ao_pilotage.compute_kpis(df)

if df.empty:
    if veille_depot.source() == "github":
        # En ligne, la base SQLite n'existe pas : elle est locale et gitignoree.
        st.info("Ces indicateurs viennent de la base **locale** du poste, qui n'est pas "
                "publiée en ligne. Ils s'affichent depuis l'application lancée sur le PC. "
                "Le suivi des appels d'offres en ligne se trouve sur la page Veille.")
    else:
        st.info("Aucun appel d'offres en base. Lancer une mise à jour depuis la page Veille.")
    st.stop()

try:
    logs = ao_db.fetch_logs()
except Exception:  # noqa: BLE001 — le pilotage doit s'afficher meme sans journal
    logs = None

st.caption(f"{kpis['nb_ao']} appels d'offres en base · dernière collecte "
           f"{pilotage.age_de_la_base(logs)} · contrôle qualité : {kpis['check_qualite']}")

# --- Ce qui attend ----------------------------------------------------------
# En tete parce que c'est la seule partie sur laquelle on peut agir aujourd'hui.
st.subheader("Ce qui attend")
ech = pilotage.echeances(df)
colonnes = st.columns(4)
colonnes[0].metric("Échéance sous 7 jours", ech["sous_7j"],
                   help="Répondre sérieusement en moins d'une semaine est rare.")
colonnes[1].metric("Sous 15 jours", ech["sous_15j"])
colonnes[2].metric("Sous 30 jours", ech["sous_30j"])
colonnes[3].metric("En attente de tri", pilotage.attente_de_tri(df),
                   help="Collectés mais jamais jugés pertinents ou non.")
st.caption(f"{ech['ouvertes']} marchés encore ouverts · {ech['expirees']} expirés. "
           "Les paliers sont cumulatifs : « sous 15 jours » contient « sous 7 jours ».")

# --- Entonnoir de collecte --------------------------------------------------
st.subheader("Ce que la collecte a filtré")
entonnoir = pilotage.entonnoir_collecte(logs)
if not entonnoir["examines"]:
    st.info("Aucun passage de collecte enregistré pour le moment.")
else:
    c1, c2, c3 = st.columns(3)
    c1.metric("Avis examinés", f"{entonnoir['examines']:,}".replace(",", " "))
    c2.metric("Retenus par le filtre", entonnoir["retenus"])
    c3.metric("Nouveaux en base", entonnoir["enregistres"])
    st.caption(f"Dernier passage {entonnoir['source']} du {entonnoir['quand']}.")
    if entonnoir["raisons"]:
        st.markdown("**Pourquoi les autres ont été écartés**")
        for raison in entonnoir["raisons"]:
            st.markdown(f"- {raison['motif']} — **{raison['nombre']}**")
        st.caption("Un motif qui gonfle anormalement signale un filtre à revoir "
                   "plutôt qu'un marché absent.")

# --- Flux dans le temps -----------------------------------------------------
st.subheader("Rythme des publications")
flux = pilotage.flux_hebdomadaire(df)
if flux.empty:
    st.info("Pas assez de dates de publication pour tracer un rythme.")
else:
    st.bar_chart(flux, x="semaine", y="appels d'offres", height=240)
    st.caption("Appels d'offres par semaine de publication. Un creux prolongé "
               "vient plus souvent d'une collecte arrêtée que d'un marché calme.")

# --- Ou sont les marches ----------------------------------------------------
st.subheader("Où sont les marchés")
priorites, gauche, droite = st.columns(3)
with priorites:
    # Le nombre de chauds seul ne disait rien : lu avec les tiedes et les froids,
    # il dit si le bareme trie ou s'il classe tout dans le meme panier.
    st.markdown("**Par priorité**")
    repartition_priorite = pilotage.repartition(df, "priorite")
    if repartition_priorite.empty:
        st.caption("Aucune priorité renseignée.")
    else:
        st.dataframe(repartition_priorite, hide_index=True, width="stretch")
with gauche:
    st.markdown("**Par département**")
    departements = pilotage.repartition(df, "departement")
    if departements.empty:
        st.caption("Aucun département renseigné.")
    else:
        st.dataframe(departements, hide_index=True, width="stretch")
with droite:
    st.markdown("**Par catégorie**")
    categories = pilotage.repartition(df, "categorie")
    if categories.empty:
        st.caption("Aucune catégorie renseignée.")
    else:
        st.dataframe(categories, hide_index=True, width="stretch")

# --- A reprendre a la main --------------------------------------------------
st.subheader("À reprendre à la main")
taches = pilotage.qualite_donnees(df)
if not taches:
    st.success("Rien à reprendre : budgets, contacts et tri sont complets.")
else:
    for tache in taches:
        with st.container(border=True):
            st.markdown(f"**{tache['point']} — {tache['nombre']}**")
            st.caption(tache["detail"])

# --- Historique des passages ------------------------------------------------
with st.expander("Derniers passages de collecte"):
    passages = pilotage.derniers_passages(logs)
    if passages.empty:
        st.caption("Aucun passage enregistré.")
    else:
        st.dataframe(passages, hide_index=True, width="stretch")
