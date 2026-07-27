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
st.caption("Lance les collectes Internet et régénère automatiquement les livrables concernés.")

racine = livrables.racine_livraison()
output = livrables.dossier_output()
script = racine / "CHRUTH_PIPELINE_UNIQUE.py"

c1, c2 = st.columns(2)
c1.metric("Livraison active", racine.name)
c2.metric("Dossier de sortie", output.name)
st.caption(f"Pipeline utilisé : `{script}`")

if not script.is_file():
    st.error(f"Pipeline introuvable : {script}")
    st.stop()

with st.container(border=True):
    st.subheader("Que faut-il collecter ?")
    libelle_mode = st.radio(
        "Type de collecte",
        list(LIBELLES_MODES),
        horizontal=True,
        key="collecte_mode",
    )
    mode = LIBELLES_MODES[libelle_mode]

    if mode == "ao":
        st.info("Collecte BOAMP/DCE, puis régénération de AO_CHRUTH.xlsm. Durée habituelle : quelques minutes.")
    elif mode == "prospects":
        st.info("Collecte API Entreprises, puis régénération de la base, de la carte, du CRM et des KPI.")
    else:
        st.info("Enchaîne la collecte des appels d'offres et des prospects, puis régénère leurs livrables.")

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
            help="Séparer plusieurs régions par des virgules. Laisser vide pour la configuration AO actuelle.",
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
    st.error("Ferme dans Excel avant de continuer : " + ", ".join(p.name for p in verrouilles))

processus = st.session_state.get("collecte_processus")
en_cours = processus is not None and processus.poll() is None
if en_cours:
    st.warning("Une collecte est déjà en cours. Un second lancement est bloqué.")

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
with st.expander("Commande qui sera exécutée"):
    st.code(" ".join(commande), language=None)

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
        st.session_state.pop("collecte_cache_actualise", None)
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Lancement impossible : {exc}")


@st.fragment(run_every=3)
def afficher_suivi() -> None:
    processus_suivi = st.session_state.get("collecte_processus")
    if processus_suivi is None:
        st.caption("Aucune collecte lancée pendant cette session.")
        return

    code = processus_suivi.poll()
    libelle = st.session_state.get("collecte_libelle", "Collecte")
    if code is None:
        st.info(f"{libelle} en cours — processus {processus_suivi.pid}. Cette zone s'actualise automatiquement.")
    elif code == 0:
        st.success(f"{libelle} terminée. Les pages Base de données et Carte utilisent maintenant les nouveaux fichiers.")
        if st.session_state.get("collecte_cache_actualise") != processus_suivi.pid:
            st.cache_data.clear()
            st.session_state["collecte_cache_actualise"] = processus_suivi.pid
    else:
        st.error(f"La collecte s'est arrêtée avec le code {code}. Consulte le journal ci-dessous.")

    journal_brut = st.session_state.get("collecte_journal", "")
    journal = Path(journal_brut) if journal_brut else None
    if journal:
        st.caption(f"Journal : `{journal}`")
        st.code(collecte.fin_journal(journal), language=None)


st.subheader("Suivi")
afficher_suivi()
st.caption("Fermer cette page n'arrête pas une collecte déjà lancée.")
