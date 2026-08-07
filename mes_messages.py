"""Mes messages — les emails et scripts conserves par le membre.

Un message conserve depuis la page « Messages et CRM » vit dans l'espace
chiffre du membre, réutilisable : on le retrouve ici, on le copie, on le
supprime. L'ajout manuel sert a garder un brouillon ecrit a la main.
"""
from __future__ import annotations

import streamlit as st

import comptes
import espace

try:
    st.set_page_config(page_title="CHRUTH — Mes messages", layout="wide")
except st.errors.StreamlitAPIException:
    pass

EMAIL = comptes.utilisateur_courant(st)
if not espace.existe(EMAIL):
    espace.creer(EMAIL)

st.markdown('<div class="chruth-kicker">Espace personnel</div>', unsafe_allow_html=True)
st.title("Mes messages")
st.caption("Les messages que tu as conservés, à toi seul. Le bouton « Conserver "
           "dans mon espace » de la page Messages et CRM les range ici.")


def _afficher(index: int, message: dict) -> None:
    with st.container(border=True):
        le = str(message.get("le", ""))[:16].replace("T", " ")
        source = message.get("source", "")
        st.markdown(f"**{message.get('objet') or '(sans objet)'}** "
                    f"· {le} · _source : {source}_")
        st.text_area("Email", value=message.get("email", ""),
                     height=200, key=f"mes_email_{index}")
        st.text_area("Script d'appel", value=message.get("script", ""),
                     height=120, key=f"mes_script_{index}")
        st.caption("Sélectionner le texte puis Ctrl+C pour copier.")
        if st.button("Supprimer", key=f"mes_suppr_{index}"):
            espace.supprimer_message(EMAIL, index)
            st.rerun()


messages = espace.messages(EMAIL)
if messages:
    st.subheader(f"{len(messages)} message(s) conservé(s)")
    for i, message in enumerate(messages):
        _afficher(i, message)
else:
    st.info("Aucun message conservé pour l'instant. Rends-toi dans « Messages et "
            "CRM » et utilise « Conserver dans mon espace ».")

st.divider()
st.subheader("Ajouter un brouillon")
with st.form("nouveau_message", clear_on_submit=True):
    f_objet = st.text_input("Objet")
    f_email = st.text_area("Email", height=180)
    f_script = st.text_area("Script d'appel", height=100)
    if st.form_submit_button("Conserver"):
        if f_email.strip():
            espace.ajouter_message(EMAIL, {
                "objet": f_objet, "email": f_email, "script": f_script,
                "source": "manuel", "le": "",
            })
            st.success("Brouillon conservé dans ton espace.")
            st.rerun()
        else:
            st.warning("Le message est vide : rien à conserver.")
