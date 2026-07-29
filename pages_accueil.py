"""Page d'accueil — ce qu'il faut savoir en ouvrant l'application.

Elle ne recalcule rien : les chiffres de la base viennent d'`ao_pilotage`, ceux
de la veille de l'etat partage, le classement des echeances d'`accueil`. Son
travail est de repondre a trois questions dans cet ordre — qu'est-ce qui est
urgent, est-ce que le systeme tourne, ou est-ce que je vais ensuite — parce
qu'une page d'accueil qui n'appelle a aucune action ne fait que retarder d'un clic.
"""
from __future__ import annotations

import streamlit as st

import accueil
import ao_db
import ao_pilotage
import reglages
import veille_depot
import veille_etat

try:
    st.set_page_config(page_title="CHRUTH — Accueil", layout="wide")
except st.errors.StreamlitAPIException:
    pass

DESTINATIONS = [
    ("app_veille.py", "Veille appels d'offres", "Le fil des marchés détectés, à trier."),
    ("pages_donnees.py", "Base de données", "Tous les AO collectés, filtrables et exportables."),
    ("app_messages.py", "Messages et CRM", "Les brouillons d'email et le suivi commercial."),
    ("pages_acheteurs.py", "Acheteurs de la semaine", "Qui a publié ces 7 derniers jours."),
]

st.title("CHRUTH — veille marchés publics")
st.caption("Détecter les appels d'offres de propreté en Île-de-France, les trier, "
           "et préparer la prise de contact.")

df = ao_db.fetch_records()
kpis = ao_pilotage.compute_kpis(df)

try:
    etat, _ = veille_depot.lire()
except Exception:  # noqa: BLE001 — l'accueil doit s'afficher meme si l'etat manque
    etat = {}
aos_veille = etat.get("aos", {}) or {}
pertinents = sum(1 for e in aos_veille.values()
                 if veille_etat.verdict_effectif(e) == "PERTINENT")

# --- Chiffres ---------------------------------------------------------------
colonnes = st.columns(4)
colonnes[0].metric("Appels d'offres en base", str(kpis["nb_ao"]))
colonnes[1].metric("Chauds", str(kpis["nb_chauds"]))
colonnes[2].metric("Sous veille", str(len(aos_veille)))
colonnes[3].metric("Jugés pertinents", str(pertinents))

# --- A traiter --------------------------------------------------------------
st.subheader("Échéances les plus proches")
urgents = accueil.prochaines_echeances(df)
if urgents.empty:
    st.info("Aucun appel d'offres prioritaire avec une date limite à venir. "
            "Lancer une mise à jour depuis la page Veille pour en collecter.")
else:
    for ligne in urgents.to_dict("records"):
        with st.container(border=True):
            reste = int(ligne[accueil.COLONNE_JOURS])
            couleur = accueil.couleur_urgence(reste)
            st.markdown(f"**{str(ligne.get('objet') or '(sans intitulé)')[:110]}**")
            st.markdown(
                f"{ligne.get('acheteur', '')} · limite "
                f"{accueil.date_lisible(ligne.get('date_limite'))} · "
                f":{couleur}[dans {reste} j] · {ligne.get('priorite', '')} "
                f"{ligne.get('score_chruth', '')}")
            source = str(ligne.get("url_avis") or ligne.get("url_dce") or "")
            if source:
                st.markdown(f"[Ouvrir l'avis d'origine]({source})")

# --- Retenus par le tri -----------------------------------------------------
# Source differente du bloc precedent : les echeances viennent de la base, ceci
# vient du jugement de la veille. Un marche peut etre retenu sans etre en base.
st.subheader("Retenus par le tri")
retenus = accueil.retenus_par_le_tri(aos_veille)
if not retenus:
    st.info("Aucun appel d'offres retenu par le tri pour le moment. "
            "La veille écrit ici à chaque passage.")
else:
    st.caption(f"{pertinents} retenus au total, les {len(retenus)} plus récents ci-dessous.")
    for id_ao, entree in retenus:
        with st.container(border=True):
            st.markdown(f"**{str(entree.get('objet') or '(sans intitulé)')[:110]}**")
            motif = (entree.get("tri") or {}).get("motif", "")
            corrige = bool(entree.get("correction_humaine"))
            st.markdown(
                f"{entree.get('acheteur', '')} · publié le "
                f"{accueil.date_lisible(entree.get('date_publication'))} · "
                f":green[**PERTINENT**]" + (" _(corrigé à la main)_" if corrige else ""))
            if motif:
                st.caption(motif)
            if entree.get("url"):
                st.markdown(f"[Ouvrir l'avis d'origine]({entree['url']})")

# --- Etat du systeme --------------------------------------------------------
st.subheader("État du système")
reg = reglages.lire()
colonnes = st.columns(3)
with colonnes[0]:
    st.markdown("**Collecte**")
    st.markdown(":green[active]" if reg.get("collecte") else ":gray[en pause]")
with colonnes[1]:
    st.markdown("**Notifications email**")
    st.markdown(":green[actives]" if reg.get("notifications") else ":gray[suspendues]")
with colonnes[2]:
    st.markdown("**Dernière veille**")
    maj = str(etat.get("maj_le") or "")
    st.markdown(maj[:16].replace("T", " ") if maj else ":gray[jamais]")
st.caption(f"Source de la veille : {veille_depot.source()} · "
           f"base mise à jour le {kpis['date_maj']} · qualité : {kpis['check_qualite']}")

# --- Ou aller ---------------------------------------------------------------
st.subheader("Aller à")
for chemin, titre, description in DESTINATIONS:
    with st.container(border=True):
        try:
            st.page_link(chemin, label=titre)
        except Exception:  # noqa: BLE001 — page ouverte seule, hors navigation
            st.markdown(f"**{titre}**")
        st.caption(description)
