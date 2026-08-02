"""Collecte AO et prospects directement depuis la plateforme Streamlit."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

import collecte_streamlit as collecte
import livrables_chruth as livrables

try:
    st.set_page_config(page_title="Collecte CHRUTH", layout="wide")
except st.errors.StreamlitAPIException:
    pass


LIBELLES_MODES = {
    "Appels d'offres": "ao",
    "Prospects": "prospects",
    "Appels d'offres et prospects": "complete",
}
LIBELLES_SCOPES = {
    "Région": "region",
    "Départements": "departements",
    "France entière": "france",
    "Test rapide": "test",
}

st.title("Collecte des données")
st.caption("Choisissez les données à actualiser. La progression s'affiche automatiquement.")

racine = livrables.racine_livraison()
output = livrables.dossier_output()
script = racine / "CHRUTH_PIPELINE_UNIQUE.py"

if not script.is_file():
    st.error("Le module de collecte est indisponible. Contactez l'administrateur de la plateforme.")
    st.stop()

with st.container(border=True):
    st.subheader("Que faut-il actualiser ?")
    libelle_mode = st.radio(
        "Type de collecte",
        list(LIBELLES_MODES),
        horizontal=True,
        key="collecte_mode",
    )
    mode = LIBELLES_MODES[libelle_mode]

    if mode == "ao":
        st.info("Recherche les nouveaux appels d'offres et met à jour la veille. Durée habituelle : 2 à 5 minutes.")
    elif mode == "prospects":
        st.info("Actualise la base prospects, la carte et le suivi commercial.")
    else:
        st.info("Actualise successivement les appels d'offres et les prospects.")

    contient_prospects = mode in {"prospects", "complete"}
    scope = "region"
    if contient_prospects:
        libelle_scope = st.selectbox(
            "Périmètre des prospects",
            list(LIBELLES_SCOPES),
            index=0,
            key="collecte_scope",
        )
        scope = LIBELLES_SCOPES[libelle_scope]
    regions = ""
    departements = ""
    if mode in {"ao", "complete"} or (contient_prospects and scope == "region"):
        regions = st.text_input(
            "Région(s)",
            value="Île-de-France",
            help="Séparer plusieurs régions par des virgules.",
            key="collecte_regions",
        )
    if contient_prospects and scope == "departements":
        departements = st.text_input(
            "Départements",
            value="75,77,78,91,92,93,94,95",
            help="Codes séparés par des virgules.",
            key="collecte_departements",
        )
    if contient_prospects and scope == "france":
        st.warning("La collecte France entière peut durer plusieurs dizaines de minutes.")

verrouilles = collecte.classeurs_verrouilles(output, mode)
if verrouilles:
    st.error("Fermez dans Excel avant de continuer : " + ", ".join(p.name for p in verrouilles))

processus = st.session_state.get("collecte_processus")
en_cours = processus is not None and processus.poll() is None
if en_cours:
    st.info("Une collecte est déjà en cours. Son avancement est affiché ci-dessous.")

confirme = st.checkbox(
    "Je confirme avoir fermé les classeurs concernés et autorise la collecte Internet.",
    key="collecte_confirmation",
)

commande = collecte.construire_commande(
    racine,
    mode,
    scope=scope,
    regions=regions,
    departements=departements,
)

if st.button(
    "Lancer la collecte",
    type="primary",
    disabled=not confirme or bool(verrouilles) or en_cours,
    key="lancer_collecte",
):
    try:
        processus, journal = collecte.lancer(racine, commande)
        st.session_state["collecte_processus"] = processus
        st.session_state["collecte_journal"] = str(journal)
        st.session_state["collecte_libelle"] = libelle_mode
        st.session_state["collecte_mode_code"] = mode
        st.session_state.pop("collecte_cache_actualise", None)
        st.rerun()
    except Exception:  # noqa: BLE001
        st.error("La collecte n'a pas pu démarrer. Réessayez dans quelques instants.")


@st.fragment(run_every=3)
def afficher_suivi() -> None:
    processus_suivi = st.session_state.get("collecte_processus")
    if processus_suivi is None:
        st.caption("Aucune collecte lancée pendant cette session.")
        return

    code = processus_suivi.poll()
    mode_suivi = st.session_state.get("collecte_mode_code", "ao")
    journal_brut = st.session_state.get("collecte_journal", "")
    journal = Path(journal_brut) if journal_brut else None
    progression = collecte.progression_journal(journal, mode_suivi, code)

    st.progress(
        progression.pourcentage,
        text=f"{progression.pourcentage}% — {progression.etape}",
    )
    if code is None:
        st.caption("La page se met à jour automatiquement. Vous pouvez continuer à utiliser les autres pages.")
        if progression.details:
            st.write(progression.details)
    elif code == 0:
        st.success("Les données sont à jour et disponibles dans la veille.")
        if progression.details:
            st.write(progression.details)
        if st.session_state.get("collecte_cache_actualise") != processus_suivi.pid:
            st.cache_data.clear()
            st.session_state["collecte_cache_actualise"] = processus_suivi.pid
    else:
        st.error("La collecte a été interrompue. Réessayez ; si le problème persiste, contactez l'administrateur.")


st.subheader("Avancement")
afficher_suivi()
st.caption("La collecte continue même si vous quittez cette page.")
