"""App Streamlit — Generation de messages de prospection CHRUTH (Mission 3).

Surface web complementaire au bouton Excel : choisir un AO (ou un segment prospect),
generer email + script via le backend pluggable (Ollama local OU cle cloud), editer,
copier. Le fournisseur se choisit dans la barre laterale ; les cles vivent dans .env.

Lancer :  double-clic LANCER_APP_CHRUTH.bat, page « Messages et CRM »
          (ou streamlit run app_messages.py pour cette page seule)
"""
from __future__ import annotations

import os

try:  # charge .env si python-dotenv est installe (cles API)
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import pandas as pd
import streamlit as st

import ao_messages
import crm
import llm_client
import prospect_messages as pm
from ao_config import AO_DB_PATH
from ao_db import connect

# set_page_config n'a le droit d'etre appele qu'une fois : l'entree multipage
# (CHRUTH_APP.py) l'a deja fait. On garde l'appel pour l'usage en page isolee.
try:
    st.set_page_config(page_title="CHRUTH — Messages IA", layout="wide")
except st.errors.StreamlitAPIException:
    pass
st.title("Messages et CRM")
st.caption("Générer les messages (appels d'offres et prospects) et suivre le commercial.")


# --- Barre laterale : choix du moteur LLM -----------------------------------
with st.sidebar:
    st.header("Moteur IA")
    provider = st.selectbox(
        "Fournisseur", ["ollama", "anthropic", "mistral", "groq"],
        help="ollama = local/gratuit ; les autres = cle API dans .env (rapide, non bride).",
    )
    modele = st.text_input("Modèle", value=llm_client.DEFAULT_MODELS.get(provider, ""))
    temperature = st.slider("Température", 0.0, 1.0, 0.2, 0.05)
    os.environ["CHRUTH_LLM_PROVIDER"] = provider
    if modele.strip():
        os.environ["CHRUTH_LLM_MODEL"] = modele.strip()
    dispo = llm_client.llm_disponible(provider)
    if dispo:
        st.success("Fournisseur disponible")
    else:
        st.warning("Indisponible (Ollama éteint ou clé absente) : repli déterministe.")
    st.caption("Clés API : à mettre dans un fichier `.env` (voir `.env.template`).")


@st.cache_data(show_spinner=False)
def charger_aos() -> pd.DataFrame:
    with connect(AO_DB_PATH) as c:
        rows = c.execute(
            "SELECT * FROM ao_records WHERE priorite IN ('CHAUD','TIEDE') "
            "ORDER BY CAST(score_chruth AS INTEGER) DESC"
        ).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def _memoriser(msg: dict, cle: str) -> None:
    """Range le message sous une clé de données (jamais une clé de widget).

    Sans cela, le résultat n'est affiché que dans le run qui suit le clic : dès que
    l'utilisateur édite le texte, Streamlit relance le script, le bouton repasse à
    False et le message s'efface. Une clé de données simple survit aux reruns, là
    où une clé partagée avec un widget serait purgée entre deux passages.
    """
    st.session_state[f"msg_{cle}"] = msg


def _zone_resultat(cle: str) -> None:
    msg = st.session_state.get(f"msg_{cle}")
    if not msg:
        return
    with st.container(border=True):
        src = msg.get("source", "")
        c_src = "violet" if src == "ia" else "gray"
        st.caption(f"Source : :{c_src}[**{src}**] "
                   "(ia = rédigé par le modèle ; defaut = brouillon type)")
        st.text_area("Email (éditable)", value=msg.get("email", ""), height=260)
        st.text_area("Script d'appel", value=msg.get("script", ""), height=160)
        st.caption("Sélectionner le texte puis Ctrl+C pour copier.")


tab_ao, tab_prospects, tab_crm = st.tabs(
    ["Appels d'offres", "Prospects (segment)", "CRM / Suivi"])

# --- Onglet AO --------------------------------------------------------------
with tab_ao:
    aos = charger_aos()
    if aos.empty:
        st.info("Aucun AO CHAUD/TIÈDE en base. Lance d'abord la collecte.")
    else:
        st.write(f"**{len(aos)} appels d'offres** CHAUD/TIÈDE")
        libelles = [
            f"[{r.priorite}] {str(r.objet)[:80]} — {r.acheteur}"
            for r in aos.itertuples()
        ]
        idx = st.selectbox("Choisis un appel d'offres", range(len(libelles)),
                           format_func=lambda i: libelles[i])
        ao = aos.iloc[idx].to_dict()
        with st.expander("Détails de l'AO"):
            st.write({k: ao.get(k) for k in
                      ("objet", "acheteur", "ville", "date_limite",
                       "budget_annuel_eur", "secteur", "categorie")})
        if st.button("Générer le message", key="gen_ao", type="primary"):
            with st.spinner("Génération en cours…"):
                msg = ao_messages.generer_message_ao(ao, temperature=temperature)
            _memoriser(msg, "ao")
        _zone_resultat("ao")

# --- Onglet Prospects -------------------------------------------------------
with tab_prospects:
    st.write("Génère le template d'un **segment** (catégorie × priorité), avec un "
             "exemple de prospect pour visualiser le rendu.")
    col1, col2 = st.columns(2)
    categorie = col1.text_input("Catégorie", value="PRIV_BUREAU")
    priorite = col2.selectbox("Priorité", ["CHAUDE", "TIEDE"])
    c1, c2, c3 = st.columns(3)
    denomination = c1.text_input("Dénomination (exemple)", value="CABINET DENTAIRE DU MARAIS",
                                  key="denom_prospect")
    ville = c2.text_input("Ville (exemple)", value="PARIS 03")
    effectif = c3.text_input("Effectif (exemple)", value="10 a 19")
    if st.button("Générer le message", key="gen_prospect", type="primary"):
        with st.spinner("Génération en cours…"):
            templates = pm.generer_templates([(categorie, priorite)], refresh=True)
            tpl = templates[f"{categorie}|{priorite}"]
            ligne = {"denomination": denomination, "libelle_commune": ville,
                     "effectif_label": effectif}
            msg = {"email": pm.rendre(tpl["email"], ligne),
                   "script": pm.rendre(tpl["script"], ligne),
                   "source": tpl["source"]}
            _memoriser(msg, "prospect")
        _zone_resultat("prospect")

# --- Onglet CRM / Suivi -----------------------------------------------------
with tab_crm:
    st.write("Enregistre le **suivi commercial réel** (contact, devis, contrat). "
             "Ces données alimenteront l'analyse de rentabilité réelle et du churn.")
    with st.form("crm_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_denom = c1.text_input("Société")
        f_siret = c2.text_input("SIRET")
        f_cat = c3.text_input("Catégorie")
        c4, c5 = st.columns(2)
        f_statut = c4.selectbox("Statut", crm.STATUTS)
        f_presta = c5.text_input("Type de prestation")
        c6, c7 = st.columns(2)
        f_devis = c6.number_input("Montant devis (€/an)", min_value=0.0, step=100.0)
        f_contrat = c7.number_input("Montant contrat (€/an)", min_value=0.0, step=100.0)
        c8, c9 = st.columns(2)
        f_debut = c8.text_input("Date début (AAAA-MM-JJ)")
        f_fin = c9.text_input("Date fin (si perdu/terminé)")
        f_comm = st.text_area("Commentaire")
        soumis = st.form_submit_button("Enregistrer")
        if soumis and (f_denom or f_siret):
            crm.ajouter({
                "denomination": f_denom, "siret": f_siret, "categorie": f_cat,
                "statut": f_statut, "type_prestation": f_presta,
                "montant_devis_eur": f_devis or "", "montant_contrat_annuel_eur": f_contrat or "",
                "date_debut": f_debut, "date_fin": f_fin, "commentaire": f_comm,
            })
            st.success("Entrée enregistrée.")
        elif soumis:
            st.warning("Renseigne au moins la société ou le SIRET.")

    df_crm = crm.charger()
    k = crm.kpis(df_crm)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Entrées", k["nb_total"])
    m2.metric("Taux de conversion", f"{k['taux_conversion'] * 100:.0f}%")
    m3.metric("CA signé / an", f"{k['ca_signe_annuel_eur']:,.0f} €")
    m4.metric("Taux de churn", f"{k['taux_churn'] * 100:.0f}%")
    st.dataframe(df_crm, width="stretch")
