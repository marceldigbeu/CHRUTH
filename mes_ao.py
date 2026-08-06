"""Mes appels d'offres — suivi personnel et notes privees du membre.

Ce suivi est distinct du verdict de tri commun (voir veille_etat) : il vit
dans l'espace chiffre du membre. Chaque entree porte un statut (a_voir, favori,
mis_de_cote) et une note privee libre.
"""
from __future__ import annotations

import streamlit as st

import ao_db
import comptes
import espace

try:
    st.set_page_config(page_title="CHRUTH — Mes appels d'offres", layout="wide")
except st.errors.StreamlitAPIException:
    pass

STATUTS = {
    "": "—",
    "a_voir": "À voir",
    "favori": "Favori",
    "mis_de_cote": "Mis de côté",
}

EMAIL = comptes.utilisateur_courant(st)
if not espace.existe(EMAIL):
    espace.creer(EMAIL)


def _enrichir(id_ao: str, entree: dict) -> dict:
    """Ajoute objet et acheteur quand l'AO est encore dans la base."""
    ligne = _AO_PAR_ID.get(str(id_ao))
    if ligne is None:
        return {"id_ao": id_ao, "objet": "(retiré de la base)", "acheteur": "",
                "statut": entree.get("statut", ""), "note": entree.get("note", "")}
    return {"id_ao": str(id_ao), "objet": ligne.get("objet", ""),
            "acheteur": ligne.get("acheteur", ""),
            "statut": entree.get("statut", ""), "note": entree.get("note", "")}


try:
    df = ao_db.fetch_records()
    _AO_PAR_ID = {str(r["id_ao"]): r for r in df.to_dict("records")}
    choix = sorted(_AO_PAR_ID.keys(),
                   key=lambda i: str(_AO_PAR_ID[i].get("objet") or "").lower())
except Exception:  # noqa: BLE001 — la base peut manquer hors poste de collecte
    _AO_PAR_ID = {}
    choix = []

st.markdown('<div class="chruth-kicker">Espace personnel</div>', unsafe_allow_html=True)
st.title("Mes appels d'offres")
st.caption("Les marchés que tu suis et tes notes privées — à toi seul, distincts "
           "du tri commun de la veille.")


# --- Suivre un nouveau marché -------------------------------------------------
st.subheader("Suivre un appel d'offres")
if not choix:
    st.info("Aucun appel d'offres en base pour l'instant. Lance la collecte d'abord.")
else:
    demandé = st.session_state.pop("ao_a_suivre", None)
    defaut = choix.index(demandé) if demandé in choix else 0
    id_choisi = st.selectbox("Marché à suivre", choix, index=defaut,
                             format_func=lambda i: _AO_PAR_ID[i].get("objet", i))
    entree = espace.aos(EMAIL).get(str(id_choisi), {"statut": "", "note": ""})
    ligne = _AO_PAR_ID.get(str(id_choisi), {})
    st.caption(f"{ligne.get('acheteur', '')} · "
               f"limite {str(ligne.get('date_limite') or '—')}")
    c1, c2 = st.columns(2)
    statut = c1.selectbox("Statut", list(STATUTS.keys()),
                          format_func=lambda s: STATUTS[s],
                          index=list(STATUTS.keys()).index(entree.get("statut", "")))
    note = c2.text_area("Note privée", value=entree.get("note", ""), height=90)
    b1, b2 = st.columns(2)
    if b1.button("Enregistrer", key="suivre_enreg", type="primary"):
        espace.definir_statut_ao(EMAIL, str(id_choisi), statut)
        if note != entree.get("note", ""):
            espace.sauver_note_ao(EMAIL, str(id_choisi), note)
        espace.noter(EMAIL, f"Suivi de l'AO {id_choisi} : {STATUTS[statut] or 'retiré'}")
        st.success("Suivi enregistré.")
        st.rerun()
    if b2.button("Effacer la note", key="suivre_effacer"):
        espace.effacer_note_ao(EMAIL, str(id_choisi))
        st.rerun()


# --- Liste des AO suivis ------------------------------------------------------
st.subheader("Mes marchés suivis")
suivis = espace.aos(EMAIL)
if not suivis:
    st.caption("Aucun marché suivi pour l'instant : ajoute-en un ci-dessus.")
else:
    for id_ao, entree in suivis.items():
        avec = _enrichir(id_ao, entree)
        statut = avec["statut"]
        couleur = {"favori": "green", "a_voir": "orange", "mis_de_cote": "red"}.get(statut, "")
        badge = f'<span class="chruth-badge chruth-badge--{couleur}">' \
                f'{STATUTS.get(statut, "—")}</span>' if couleur else ""
        with st.container(border=True):
            if badge:
                st.markdown(badge, unsafe_allow_html=True)
            st.markdown(f"**{avec['objet']}**")
            st.caption(f"{avec['acheteur']} · {avec['id_ao']}")
            if avec["note"]:
                st.markdown(avec["note"])
            col1, col2, col3 = st.columns([1, 1, 3])
            nouveau = col1.selectbox("Statut", list(STATUTS.keys()), key=f"st_{id_ao}",
                                     format_func=lambda s: STATUTS[s],
                                     index=list(STATUTS.keys()).index(statut)
                                     if statut in STATUTS else 0)
            if col2.button("Enregistrer", key=f"enreg_{id_ao}"):
                espace.definir_statut_ao(EMAIL, id_ao, nouveau)
                espace.noter(EMAIL, f"Statut de l'AO {id_ao} : {STATUTS[nouveau] or 'retiré'}")
                st.rerun()
            if col3.button("Ouvrir dans la veille", key=f"ouvrir_{id_ao}"):
                st.session_state["ao_a_rediger"] = id_ao
                st.switch_page("app_veille.py")
