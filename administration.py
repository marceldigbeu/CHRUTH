"""Administration — gestion des espaces membres.

Geste d'administrateur : lister les membres, activer ou desactiver un compte
local, reinitialiser son mot de passe, ou supprimer completement l'espace
(depart d'un salarie). L'acces `[acces]` des secrets n'est jamais modifie ici :
il reste hors de l'application, c'est l'administrateur des secrets qui ouvre
ou ferme la porte a une adresse.
"""
from __future__ import annotations

import streamlit as st

import comptes
import connexion
import espace

try:
    st.set_page_config(page_title="CHRUTH — Administration", layout="wide")
except st.errors.StreamlitAPIException:
    pass

st.markdown('<div class="chruth-kicker">Espace personnel</div>', unsafe_allow_html=True)
st.title("Administration")
st.caption("Espace réservé aux administrateurs.")

if not comptes.est_admin_courant(st):
    st.error("Cette page est réservée aux administrateurs.")
    st.stop()

EMAIL = comptes.utilisateur_courant(st)


# --- Acces aux secrets, en lecture -------------------------------------------
autorises, admins = connexion.lire_acces(st.secrets)
with st.expander("Accès configuré dans les secrets (lecture seule)"):
    st.caption("L'application n'écrit jamais dans `[acces]` : c'est le fichier "
               "`.streamlit/secrets.toml`, hors de portée de la page, qui décide "
               "qui entre et qui administre.")
    c1, c2 = st.columns(2)
    c1.markdown("**Adresses autorisées**")
    c1.write(", ".join(autorises) if autorises else "Aucune (tout compte Google autorisé)")
    c2.markdown("**Administrateurs**")
    c2.write(", ".join(admins) if admins else "Aucun")


# --- Liste des membres --------------------------------------------------------
st.subheader("Membres de l'espace")
membres = espace.lister_membres()
if not membres:
    st.info("Aucun membre inscrit pour l'instant : les comptes se créent à la "
            "connexion (compte local) ou dès la première visite d'un espace personnel.")

for email in membres:
    actif = espace.actif(email)
    profil = espace.profil(email)
    with st.container(border=True):
        c_titre, c_statut = st.columns([3, 1])
        c_titre.markdown(f"**{profil.get('nom_affiche') or email}**  ·  {email}")
        c_statut.markdown(
            f'<span class="chruth-badge {"chruth-badge--green" if actif else "chruth-badge--red"}">'
            f'{"Actif" if actif else "Désactivé"}</span>',
            unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        if actif:
            if col_a.button("Désactiver", key=f"desa_{email}"):
                espace.desactiver(email)
                espace.noter(EMAIL, f"Compte désactivé : {email}")
                st.rerun()
        else:
            if col_a.button("Réactiver", key=f"rea_{email}"):
                espace.reactiver(email)
                espace.noter(EMAIL, f"Compte réactivé : {email}")
                st.rerun()

        with st.expander("Réinitialiser le mot de passe"):
            nouveau = st.text_input("Nouveau mot de passe (8 caractères minimum)",
                                    type="password", key=f"mdp_{email}")
            if st.button("Enregistrer", key=f"mdp_ok_{email}"):
                if len(nouveau) < 8:
                    st.error("Mot de passe trop court.")
                else:
                    espace.definir_mot_de_passe(email, comptes.hacher(nouveau))
                    espace.noter(EMAIL, f"Mot de passe réinitialisé : {email}")
                    st.success("Mot de passe mis à jour.")

        with st.expander("Supprimer complètement (départ du salarié)", key=f"suppr_{email}"):
            st.warning("Cette action efface le profil, les notes, les messages et le "
                       "compte local. Sans retour.")
            confirme = st.checkbox("Je confirme la suppression complète",
                                   key=f"conf_{email}")
            if confirme and st.button("Supprimer l'espace", key=f"ok_{email}"):
                espace.supprimer(email)
                espace.noter(EMAIL, f"Espace supprimé : {email}")
                st.rerun()
