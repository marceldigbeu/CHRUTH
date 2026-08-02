"""Accueil opérationnel de la plateforme CHRUTH."""
from __future__ import annotations

import html

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

st.markdown('<div class="chruth-kicker">Cockpit opérationnel</div>', unsafe_allow_html=True)
st.title("CHRUTH — veille marchés publics")
st.caption("Détecter les appels d'offres de propreté en Île-de-France, les trier, "
           "et préparer la prise de contact.")

df = ao_db.fetch_records()
kpis = ao_pilotage.compute_kpis(df)

try:
    etat, _ = veille_depot.lire()
except Exception:  # l'accueil doit s'afficher même si l'état manque
    etat = {}
aos_veille = etat.get("aos", {}) or {}
pertinents = sum(1 for e in aos_veille.values()
                 if veille_etat.verdict_effectif(e) == "PERTINENT")

# --- Chiffres ---------------------------------------------------------------
colonnes = st.columns(4)
colonnes[0].metric("Appels d'offres en base", str(kpis["nb_ao"]), help="Tous les AO enregistrés")
colonnes[1].metric("Priorité chaude", str(kpis["nb_chauds"]), help="Les opportunités à examiner en premier")
colonnes[2].metric("Sous veille", str(len(aos_veille)), help="AO suivis par la veille automatisée")
colonnes[3].metric("Jugés pertinents", str(pertinents), help="Verdicts automatiques ou corrigés manuellement")

# --- À traiter --------------------------------------------------------------
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
            st.markdown(
                f'<span class="chruth-badge chruth-badge--{couleur}">Échéance dans {reste} jours</span>',
                unsafe_allow_html=True,
            )
            st.markdown(f"**{str(ligne.get('objet') or '(sans intitulé)')[:110]}**")
            st.markdown(
                f"{ligne.get('acheteur', '')} · limite "
                f"{accueil.date_lisible(ligne.get('date_limite'))} · "
                f"{ligne.get('priorite', '')} · score {ligne.get('score_chruth', '')}")
            source = str(ligne.get("url_avis") or ligne.get("url_dce") or "")
            if source:
                st.link_button("Ouvrir l'avis d'origine", source)

# --- Retenus par le tri -----------------------------------------------------
st.subheader("Retenus par le tri")
retenus = accueil.retenus_par_le_tri(aos_veille)
if not retenus:
    st.info("Aucun appel d'offres retenu par le tri pour le moment. "
            "La veille écrit ici à chaque passage.")
else:
    st.caption(f"{pertinents} retenus au total, les {len(retenus)} plus récents ci-dessous.")
    for id_ao, entree in retenus:
        with st.container(border=True):
            st.markdown('<span class="chruth-badge chruth-badge--green">Pertinent</span>',
                        unsafe_allow_html=True)
            st.markdown(f"**{str(entree.get('objet') or '(sans intitulé)')[:110]}**")
            motif = (entree.get("tri") or {}).get("motif", "")
            corrige = bool(entree.get("correction_humaine"))
            st.markdown(
                f"{entree.get('acheteur', '')} · publié le "
                f"{accueil.date_lisible(entree.get('date_publication'))}" +
                (" · _corrigé à la main_" if corrige else ""))
            if motif:
                st.caption(motif)
            if entree.get("url"):
                st.link_button("Ouvrir l'avis d'origine", entree["url"])

# --- État du système --------------------------------------------------------
st.subheader("État du système")
reg = reglages.lire()
collecte_active = bool(reg.get("collecte"))
notifications_actives = bool(reg.get("notifications"))
maj = str(etat.get("maj_le") or "")
maj_lisible = maj[:16].replace("T", " ") if maj else "Jamais"
st.markdown(
    '<div class="chruth-status-grid">'
    f'<div class="chruth-status"><span>Collecte automatisée</span><strong class="{"on" if collecte_active else "off"}">'
    f'{"Active" if collecte_active else "En pause"}</strong></div>'
    f'<div class="chruth-status"><span>Notifications email</span><strong class="{"on" if notifications_actives else "off"}">'
    f'{"Actives" if notifications_actives else "Suspendues"}</strong></div>'
    f'<div class="chruth-status"><span>Dernière veille</span><strong>{html.escape(maj_lisible)}</strong></div>'
    '</div>',
    unsafe_allow_html=True,
)
st.caption(f"Source : {veille_depot.source()} · base mise à jour le {kpis['date_maj']} · "
           f"qualité : {kpis['check_qualite']}")

# --- Où aller ---------------------------------------------------------------
st.subheader("Accès rapides")
grille = st.columns(2)
for index, (chemin, titre, description) in enumerate(DESTINATIONS):
    with grille[index % 2]:
        with st.container(border=True):
            try:
                st.page_link(chemin, label=titre)
            except Exception:  # page ouverte seule, hors navigation
                st.markdown(f"**{titre}**")
            st.caption(description)
