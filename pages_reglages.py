"""Page Reglages — la source unique, vue depuis la plateforme.

Tout ce qui est modifie ici part dans etat/veille.json sur la branche ao-state,
et sera lu par le pipeline local, le tableur et les autres surfaces.
"""
from __future__ import annotations

import streamlit as st

import reglages

try:
    st.set_page_config(page_title="Réglages CHRUTH", layout="wide")
except st.errors.StreamlitAPIException:
    pass

valeurs = reglages.lire()

st.title("Réglages")
st.caption("Modifié ici, appliqué partout : pipeline local, tableur, veille cloud.")

# --- Destinataires ---------------------------------------------------------
with st.container(border=True):
    st.subheader("Destinataires des alertes")
    saisie = st.text_area("Une adresse par ligne",
                          value="\n".join(valeurs.get("destinataires") or []),
                          height=140, key="destinataires")
    if st.button("Enregistrer les destinataires", key="enregistrer_destinataires"):
        adresses = [l.strip() for l in saisie.splitlines() if l.strip() and "@" in l]
        reglages.ecrire({"destinataires": adresses})
        st.success(f"{len(adresses)} destinataire(s) enregistré(s).")

# --- Expediteur (lecture seule) --------------------------------------------
with st.container(border=True):
    st.subheader("Expéditeur")
    st.markdown(f"Les alertes partent de **{valeurs.get('expediteur') or 'non renseigné'}**.")
    st.caption("Non modifiable ici : l'adresse et son mot de passe d'application forment une "
               "paire. Les changer séparément casserait tous les envois. Ils se modifient "
               "ensemble dans alertes_secrets.json et les secrets GitHub.")

# --- Interrupteurs ---------------------------------------------------------
with st.container(border=True):
    st.subheader("Interrupteurs")
    for cle, libelle, aide in [
        ("notifications", "notifications", "Les emails partent-ils ?"),
        ("collecte", "collecte", "Les sources sont-elles interrogées ?"),
    ]:
        actif = bool(valeurs.get(cle, True))
        etat = ":green[actives]" if actif else ":red[suspendues]"
        st.markdown(f"**{libelle.capitalize()}** : {etat} — {aide}")
        if st.button(("Désactiver " if actif else "Activer ") + libelle, key=f"basculer_{cle}"):
            reglages.ecrire({cle: not actif})
            st.rerun()

# --- Perimetre personnel ---------------------------------------------------
with st.container(border=True):
    st.subheader("Marchés de personnel")
    rh = bool(valeurs.get("mots_cles_rh_actifs", True))
    etat_rh = ":green[pris en compte]" if rh else ":red[ignorés]"
    st.markdown(f"Mise à disposition de personnel et services associés : **{etat_rh}**.")
    if st.button("Ignorer ces marchés" if rh else "Prendre en compte ces marchés",
                 key="basculer_rh"):
        reglages.ecrire({"mots_cles_rh_actifs": not rh})
        st.rerun()

# --- Fiche CHRUTH ----------------------------------------------------------
with st.container(border=True):
    st.subheader("Fiche CHRUTH")
    st.caption("Alimente la rédaction des messages, le prompt de tri et la signature. "
               "Les coordonnées saisies sont collées telles quelles : laisser vide plutôt "
               "qu'approximer.")
    fiche = st.text_area("Fiche", value=valeurs.get("fiche_chruth") or "", height=320,
                         key="fiche", label_visibility="collapsed")
    if st.button("Enregistrer la fiche", key="enregistrer_fiche"):
        reglages.ecrire({"fiche_chruth": fiche})
        st.success("Fiche enregistrée.")
