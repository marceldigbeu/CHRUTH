"""Mon espace — profil, preferences et journal personnel du membre.

Identite en lecture (email, photo Google en ligne), champs edites dans l'espace
chiffre du membre : nom affiche, role, signature ; telephone et photo ne vivent
que sur le poste (decision de la section 5 du plan). Les preferences restent
des valeurs stockees : la page Veille les consomme a la demande.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

import comptes
import espace
import espace_depot

try:
    st.set_page_config(page_title="CHRUTH — Mon espace", layout="wide")
except st.errors.StreamlitAPIException:
    pass

DEPARTEMENTS_IDF = ["75", "77", "78", "91", "92", "93", "94", "95"]
PERIODES = ["Tout", "7 derniers jours", "14 derniers jours", "30 derniers jours",
            "Depuis une date précise"]
DENSITES = ["confortable", "compacte"]
PAGES_DISPONIBLES = [
    "Accueil", "Veille appels d'offres", "Collecte", "Base de données",
    "Acheteurs de la semaine", "Carte", "Messages et CRM", "Pilotage",
    "Réglages", "Développeur", "Mes appels d'offres", "Mes messages",
    "Mon espace", "Administration",
]

EMAIL = comptes.utilisateur_courant(st)
if not espace.existe(EMAIL):
    espace.creer(EMAIL)

en_local = espace_depot.source() == "local"


def _dossier_photos() -> Path:
    return espace_depot.dossier_local().parent / "photos"


def _chemin_photo() -> Path:
    return _dossier_photos() / (EMAIL.encode("utf-8").hex() + ".jpg")


def _photo_locale() -> bytes | None:
    chemin = _chemin_photo()
    if chemin.exists():
        try:
            return chemin.read_bytes()
        except OSError:
            return None
    return None


st.markdown('<div class="chruth-kicker">Espace personnel</div>', unsafe_allow_html=True)
st.title("Mon espace")
st.caption("Ce que cette machine connaît de toi. Les données personnelles "
           "restent chiffrées, dans un fichier par membre.")


# --- Identite ----------------------------------------------------------------
identite = comptes.identite(st)
col_titre, col_photo = st.columns([3, 1])
with col_titre:
    st.subheader(identite["nom"] or EMAIL)
    st.caption(EMAIL)
    if identite["photo"]:
        st.image(identite["photo"], width=120)

if en_local:
    with col_photo:
        upload = st.file_uploader("Photo de profil (poste uniquement)",
                                  type=["jpg", "jpeg", "png"], key="photo_upload")
        if upload is not None:
            _dossier_photos().mkdir(parents=True, exist_ok=True)
            _chemin_photo().write_bytes(upload.getvalue())
            st.success("Photo enregistrée sur ce poste.")
        else:
            locale = _photo_locale()
            if locale is not None:
                st.image(locale, width=120, caption="Photo locale")
    st.caption("En ligne, la photo affichée est celle de ton compte Google. "
               "Le téléphone, lui, ne sort pas du poste.")

# --- Profil ------------------------------------------------------------------
st.subheader("Profil")
with st.form("profil_form"):
    profil = espace.profil(EMAIL)
    f_nom = st.text_input("Nom affiché", value=profil.get("nom_affiche", ""))
    f_role = st.text_input("Rôle", value=profil.get("role", ""))
    f_telephone = st.text_input("Téléphone (poste uniquement)",
                                value=profil.get("telephone", ""), disabled=not en_local)
    f_signature = st.text_area("Signature d'email", value=profil.get("signature", ""),
                               height=110)
    if st.form_submit_button("Enregistrer le profil"):
        espace.enregistrer_profil(EMAIL, {
            "nom_affiche": f_nom, "role": f_role,
            "telephone": f_telephone, "signature": f_signature,
        })
        st.success("Profil enregistré.")

# --- Preferences -------------------------------------------------------------
st.subheader("Préférences d'affichage")
with st.form("preferences_form"):
    prefs = espace.preferences(EMAIL)
    f_dep = st.multiselect("Départements suivis par défaut",
                           DEPARTEMENTS_IDF, default=prefs.get("departements") or [])
    f_prior = st.text_input("Priorités par défaut (séparées par des virgules)",
                            value=", ".join(prefs.get("priorites") or []))
    f_periode = st.selectbox("Période par défaut", PERIODES,
                             index=PERIODES.index(prefs.get("periode"))
                             if prefs.get("periode") in PERIODES else 0)
    f_page = st.selectbox("Page d'accueil souhaitée", PAGES_DISPONIBLES,
                          index=PAGES_DISPONIBLES.index(prefs.get("page_accueil"))
                          if prefs.get("page_accueil") in PAGES_DISPONIBLES else 0)
    f_densite = st.selectbox("Densité d'affichage", DENSITES,
                             index=DENSITES.index(prefs.get("densite"))
                             if prefs.get("densite") in DENSITES else 0)
    if st.form_submit_button("Enregistrer les préférences"):
        espace.enregistrer_preferences(EMAIL, {
            "departements": [d for d in f_dep],
            "priorites": [p.strip() for p in f_prior.split(",") if p.strip()],
            "periode": f_periode, "page_accueil": f_page, "densite": f_densite,
        })
        st.success("Préférences enregistrées.")

# --- Journal -----------------------------------------------------------------
st.subheader("Journal d'activité")
entrees = espace.journal(EMAIL)
if not entrees:
    st.caption("Rien encore : les actions personnelles (notes, statuts, messages "
               "conservés) apparaîtront ici.")
else:
    for entree in entrees[:10]:
        avec = entree.get("le", "")[:16].replace("T", " ")
        st.markdown(f"**{avec}** — {entree.get('evenement', '')}")
