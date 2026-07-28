"""Page Acheteurs de la semaine : les acheteurs ayant publié un AO propreté
pertinent sur 7 jours, classés public / privé-droit.
"""
from __future__ import annotations

import streamlit as st

import acheteurs_semaine as asem

try:
    st.set_page_config(page_title="Acheteurs de la semaine", layout="wide")
except st.errors.StreamlitAPIException:
    pass

st.title("Acheteurs de la semaine")
st.caption("Les organisations ayant publié un appel d'offres de propreté pertinent "
           "dans les 7 derniers jours — vos cibles chaudes, classées public / privé-droit.")

df = asem.construire()

if df.empty:
    st.info("Aucun acheteur sur les 7 derniers jours. La liste se remplit à chaque "
            "collecte du flux de veille.")
else:
    choix = st.radio("Type d'acheteur", ["Tous", "Public", "Privé-droit"],
                     horizontal=True, key="type_acheteur")
    vue = df
    if choix == "Public":
        vue = df[df["type"] == "public"]
    elif choix == "Privé-droit":
        vue = df[df["type"] == "prive"]

    st.caption(f"{len(vue)} acheteur(s) — {int((vue['type'] == 'public').sum())} public(s), "
               f"{int((vue['type'] == 'prive').sum())} privé-droit")

    for _, r in vue.iterrows():
        with st.container(border=True):
            marque = ":blue[Public]" if r["type"] == "public" else ":orange[Privé-droit]"
            incertain = " _(à confirmer)_" if r.get("type_incertain") else ""
            st.markdown(f"**{r['acheteur']}** — {marque}{incertain}")
            lieu = " ".join(x for x in [r.get("code_postal", ""), r.get("ville", ""),
                                        f"({r['departement']})" if r.get("departement") else ""] if x)
            st.markdown(f"{lieu} · {r['nb_ao_semaine']} AO cette semaine · {r['priorite']}"
                        + (f" · effectif {r['effectif']}" if r.get("effectif") else ""))
            for ao in (r["aos"] if isinstance(r["aos"], list) else []):
                lien = f"[{ao.get('objet','')}]({ao.get('url','')})" if ao.get("url") else ao.get("objet", "")
                st.markdown(f"- {lien} — publié {ao.get('date_publication','')} · {ao.get('priorite','')}")

    st.download_button("Exporter en CSV", df.assign(aos=df["aos"].map(asem._aplatir_aos)).to_csv(index=False),
                       file_name="Acheteurs_Semaine_CHRUTH.csv", mime="text/csv")
