"""App Streamlit — Generation de messages de prospection CHRUTH (Mission 3).

Surface web complementaire au bouton Excel : choisir un AO (ou un segment prospect),
generer email + script via le backend pluggable (Ollama local OU cle cloud), editer,
copier. Le fournisseur se choisit dans la barre laterale ; les cles vivent dans .env.

Lancer :  double-clic LANCER_APP_CHRUTH.bat, page « Messages et CRM »
          (ou streamlit run app_messages.py pour cette page seule)
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import ao_messages
import comptes
import crm
import espace
import liens_source
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
        "Fournisseur", list(llm_client.FOURNISSEURS),
        help="ollama = local/gratuit ; les autres = cle API dans .env (rapide, non bride).",
    )
    modele = st.text_input("Modèle", value=llm_client.DEFAULT_MODELS.get(provider, ""))
    temperature = st.slider("Température", 0.0, 1.0, 0.2, 0.05)

    # Plafond de sortie. Sur une API facturee au token, c'est le seul frein :
    # rien d'autre n'empeche une reponse de partir en boucle.
    max_tokens = st.slider("Longueur maximale (tokens)", 256, 2048,
                           llm_client.MAX_TOKENS_DEFAUT, 128, key="max_tokens",
                           help="Environ 4 caractères par token. Un email de "
                                "prospection tient sous 800 tokens.")
    st.caption(f"Soit environ {max_tokens * llm_client.CARACTERES_PAR_TOKEN:,} caractères"
               .replace(",", " "))

    # Le modele suit le fournisseur choisi : laisser en place celui du precedent
    # enverrait « mistral-small-latest » a Anthropic — cle valable, appel refuse.
    llm_client.appliquer_choix(provider, modele)
    dispo = llm_client.llm_disponible(provider)
    if dispo:
        st.success("Fournisseur disponible")
    else:
        st.warning("Indisponible (Ollama éteint ou clé absente) : repli déterministe.")
    st.caption("Clés API : à mettre dans un fichier `.env` (voir `.env.template`).")

    st.divider()
    if st.button("Recharger les données", key="recharger",
                 help="Relit la base. À utiliser si la collecte a tourné "
                      "pendant que l'application était ouverte."):
        st.cache_data.clear()
        st.rerun()


@st.cache_data(show_spinner=False)
def charger_aos() -> pd.DataFrame:
    """AO a demarcher : prioritaires ET non rejetes par le tri.

    Le score seul ne suffit pas a decider qu'un marche nous concerne : il compte
    des mots-cles, et une formation « lutte contre les discriminations » ou un
    marche de paie en collectionne autant qu'un marche de nettoyage. Le verdict
    d'`ao_pertinence` tranche, lui, sur le fond — sans ce filtre la liste s'ouvre
    sur des marches qu'on ne repondra jamais. Les AO pas encore tries (verdict
    vide) restent affiches : on cache ce qui est juge hors sujet, pas ce qui
    n'a pas encore ete juge.
    """
    with connect(AO_DB_PATH) as c:
        rows = c.execute(
            "SELECT * FROM ao_records WHERE priorite IN ('CHAUD','TIEDE') "
            "AND COALESCE(verdict_tri, '') <> 'REJETE' "
            "ORDER BY CAST(score_chruth AS REAL) DESC"
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


def _zone_resultat(cle: str, objet: str = "") -> None:
    msg = st.session_state.get(f"msg_{cle}")
    if not msg:
        return
    with st.container(border=True):
        src = msg.get("source", "")
        c_src = "violet" if src == "ia" else "gray"
        st.caption(f"Source : :{c_src}[**{src}**] "
                   "(ia = rédigé par le modèle ; base = déjà enregistré lors "
                   "d'un passage précédent ; defaut = brouillon type)")
        st.text_area("Email (éditable)", value=msg.get("email", ""), height=260)
        st.text_area("Script d'appel", value=msg.get("script", ""), height=160)
        st.caption("Sélectionner le texte puis Ctrl+C pour copier.")
        if st.button("Conserver dans mon espace", key=f"conserver_{cle}"):
            email = comptes.utilisateur_courant(st)
            if not espace.existe(email):
                espace.creer(email)
            espace.ajouter_message(email, {
                "objet": objet, "email": msg.get("email", ""),
                "script": msg.get("script", ""), "source": msg.get("source", ""),
                "le": "",
            })
            espace.noter(email, f"Message conservé : {objet}")
            st.success("Message conservé dans ton espace (page « Mes messages »).")


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
        # Marche arrive depuis la page Veille : on le presente deja selectionne.
        # Sans cela il faut le retrouver a la main dans une liste de 85 lignes.
        defaut = 0
        demande = st.session_state.pop("ao_a_rediger", None)
        if demande is not None:
            positions = [i for i, v in enumerate(aos["id_ao"]) if str(v) == str(demande)]
            if positions:
                defaut = positions[0]
            else:
                st.warning(f"Le marché {demande} vient de la veille mais n'est pas "
                           "encore dans la base : lance une collecte pour l'y faire entrer.")

        idx = st.selectbox("Choisis un appel d'offres", range(len(libelles)),
                           index=defaut, format_func=lambda i: libelles[i])
        ao = aos.iloc[idx].to_dict()
        with st.expander("Détails de l'AO"):
            st.write({k: ao.get(k) for k in
                      ("objet", "acheteur", "ville", "date_limite",
                       "budget_annuel_eur", "secteur", "categorie")})

        # On ecrit a un acheteur a partir d'un avis : pouvoir le relire avant
        # d'envoyer evite les messages qui citent de travers l'objet du marche.
        source = liens_source.premiere_source(ao)
        if source:
            st.markdown(f"[Ouvrir l'avis d'origine]({source})")

        # Ce que coutera la redaction, avant de la lancer : sur une API facturee
        # au token, on ne veut pas decouvrir le montant apres coup.
        cout = ao_messages.cout_estime(ao, max_tokens=max_tokens)
        c1, c2, c3 = st.columns(3)
        c1.metric("Tokens envoyés", f"{cout['entree']:,}".replace(",", " "))
        c2.metric("Réponse (plafond)", f"{cout['sortie_max']:,}".replace(",", " "))
        c3.metric("Total au pire", f"{cout['total_max']:,}".replace(",", " "))
        st.caption("Estimation à environ 4 caractères par token. Le décompte exact "
                   "reste celui du fournisseur.")

        # Une cle par AO : partager "msg_ao" ferait s'afficher le message du
        # marche precedent des qu'on change de ligne dans la liste.
        cle = f"ao_{ao.get('id_ao')}"
        if st.button("Regénérer le message", key="gen_ao", type="primary"):
            # `st.status` plutot qu'un spinner : il nomme l'etape en cours et
            # reste a l'ecran une fois fini. Sur trois minutes d'attente locale,
            # un simple sablier laisse croire que rien ne se passe.
            with st.status("Rédaction en cours…", expanded=True) as etat:
                st.write(f"Fournisseur : **{provider}** · modèle : **{modele or 'défaut'}**")
                st.write(f"Envoi d'environ **{cout['entree']} tokens**, "
                         f"réponse plafonnée à **{max_tokens}**.")
                if provider == "ollama":
                    st.write("Modèle local : compter 2 à 3 minutes.")
                msg = ao_messages.generer_message_ao(ao, temperature=temperature,
                                                     max_tokens=max_tokens)
                origine = msg.get("source", "")
                etat.update(label=f"Message rédigé (source : {origine})", state="complete",
                            expanded=False)
            _memoriser(msg, cle)

        # Le message redige lors de la collecte est deja en base : on l'affiche
        # sans rien recalculer. Regenerer prend plusieurs minutes sur un modele
        # local — attendre ce delai pour relire un texte deja ecrit n'a pas de sens.
        if not st.session_state.get(f"msg_{cle}"):
            existant = str(ao.get("proposition_message") or "").strip()
            if existant:
                _memoriser({"email": existant,
                            "script": str(ao.get("script_appel") or ""),
                            "source": "base"}, cle)
        _zone_resultat(cle, objet=str(ao.get("objet") or "")[:90])

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
        _zone_resultat("prospect", objet=f"Prospects {categorie} {priorite}")

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
    if not k["nb_total"]:
        # Quatre zeros sans explication se lisent comme une panne. On dit d'ou ils
        # viennent : ce sont des compteurs vides, pas un calcul qui a echoue.
        st.info("Aucun suivi commercial enregistré pour l'instant : les indicateurs "
                "ci-dessous restent donc à zéro. Ils se calculent au fil des entrées "
                "saisies dans le formulaire.")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Entrées", k["nb_total"])
    m2.metric("Taux de conversion", f"{k['taux_conversion'] * 100:.0f}%")
    m3.metric("CA signé / an", f"{k['ca_signe_annuel_eur']:,.0f} €")
    m4.metric("Taux de churn", f"{k['taux_churn'] * 100:.0f}%")
    if k["nb_total"]:
        st.dataframe(df_crm, width="stretch")
