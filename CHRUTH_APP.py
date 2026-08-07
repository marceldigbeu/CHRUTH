"""Application CHRUTH — point d'entrée unique."""
from __future__ import annotations

import streamlit as st

import comptes
import connexion
import espace
import navigation_acces
import theme_chruth

st.set_page_config(
    page_title="CHRUTH · Veille marchés publics",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _deconnecter() -> None:
    """Ferme la connexion locale, puis le fournisseur Google s'il est ouvert."""
    comptes.deconnecter(st)
    try:
        if getattr(st.user, "is_logged_in", False):
            st.logout()
    except Exception:  # noqa: BLE001 — pas de session Google a fermer
        pass


CLE_MESSAGE_CREATION = "creation_compte.message"


def _creer_compte_local() -> None:
    """Crée le compte à partir des champs, puis dépose le résultat en session.

    Les valeurs sont lues dans `session_state` et non reçues en paramètres :
    les `args` d'un `on_click` sont figés au rendu précédent, donc antérieurs
    à la saisie. La création recevait trois chaînes vides et refusait toujours
    l'adresse — quoi que le visiteur ait tapé.

    Le résultat transite par la session plutôt que par un `st.success` écrit
    ici : ce qu'un callback affiche est produit avant le rendu, donc perdu.
    C'est le corps de la page qui l'affiche.
    """
    try:
        comptes.creer_compte_local(
            st.session_state.get("creer_email", ""),
            st.session_state.get("creer_nom", ""),
            st.session_state.get("creer_mdp", ""),
        )
        st.session_state[CLE_MESSAGE_CREATION] = (
            "succes", "Compte créé. Renseigne la même adresse ci-dessus pour te connecter.")
    except ValueError as exc:
        st.session_state[CLE_MESSAGE_CREATION] = ("erreur", str(exc))


def _afficher_message_creation() -> None:
    """Rend le résultat de la dernière tentative de création, s'il y en a une."""
    niveau, message = st.session_state.get(CLE_MESSAGE_CREATION, ("", ""))
    if niveau == "succes":
        st.success(message)
    elif niveau == "erreur":
        st.error(message)


def page_de_connexion() -> None:
    """Écran d'entrée, avant tout accès à la plateforme.

    Deux portes : le fournisseur Google (s'il est configuré), et un compte
    local pour les membres sans compte Google. La création d'un compte local
    n'ouvre pas l'accès : l'adresse doit ensuite figurer dans `[acces]` des
    secrets pour entrer — seul l'administrateur l'y met.
    """
    st.markdown('<div class="chruth-kicker">Accès sécurisé</div>', unsafe_allow_html=True)
    st.title("CHRUTH")
    st.caption("Veille des marchés publics de propreté en Île-de-France.")
    st.write("Cette application est réservée aux comptes autorisés.")
    if connexion.authentification_configuree(st.secrets):
        st.button("Se connecter avec Google", type="primary", on_click=st.login)
        st.divider()

    st.subheader("Compte CHRUTH")
    st.caption("Pour les membres sans compte Google. Le mot de passe reste "
               "stocké haché, dans l'espace chiffré de chacun.")
    with st.form("connexion_locale"):
        email = st.text_input("Adresse email")
        mdp = st.text_input("Mot de passe", type="password")
        soumettre = st.form_submit_button("Se connecter", type="primary")
        if soumettre:
            email = comptes.normaliser(email)
            if comptes.authentifier_local(email, mdp):
                comptes.connecter_local(st, email)
                st.rerun()
            else:
                st.error("Adresse ou mot de passe inconnu.")

    with st.expander("Créer un compte local"):
        st.caption("Aucun compte encore ? Crée le tien : adresse, nom affiché "
                   "et mot de passe.")
        st.text_input("Adresse email", key="creer_email")
        st.text_input("Nom affiché", key="creer_nom")
        st.text_input("Mot de passe (8 caractères minimum)",
                      type="password", key="creer_mdp")
        st.button("Créer le compte", on_click=_creer_compte_local)
        _afficher_message_creation()


def garde() -> bool:
    """Laisse passer, ou affiche l'écran d'entrée. Renvoie True si l'accès est ouvert.

    La connexion est exigée dans tous les modes : Google quand un fournisseur
    est configuré, compte local sinon. Sans identification, rien ne s'affiche.
    """
    if not comptes.est_connecte(st):
        page_de_connexion()
        return False

    email = comptes.utilisateur_courant(st)
    autorises, admins = connexion.lire_acces(st.secrets)
    if not connexion.est_autorise(email, autorises):
        st.error(connexion.message_refus(email, admins))
        st.button("Se déconnecter", on_click=_deconnecter)
        return False

    with st.sidebar:
        st.caption(f"Connecté : {email}")
        if comptes.est_admin_courant(st):
            st.caption("Administrateur")
        st.button("Se déconnecter", on_click=_deconnecter, key="deconnexion")
    return True


if not garde():
    st.stop()

theme_chruth.appliquer()

PAGES_DEF = [
    ("pages_accueil.py", "Accueil"),
    ("app_veille.py", "Veille appels d'offres"),
    ("pages_collecte.py", "Collecte"),
    ("pages_donnees.py", "Base de données"),
    ("pages_acheteurs.py", "Acheteurs de la semaine"),
    ("pages_carte.py", "Carte"),
    ("app_messages.py", "Messages et CRM"),
    ("pages_pilotage.py", "Pilotage"),
    ("pages_reglages.py", "Réglages"),
    ("pages_developpeur.py", "Développeur"),
    ("mes_ao.py", "Mes appels d'offres"),
    ("mes_messages.py", "Mes messages"),
    ("mon_espace.py", "Mon espace"),
    ("administration.py", "Administration"),
]

_TITRES = [titre for _, titre in PAGES_DEF]


def page_accueil_preferee() -> str:
    """Page d'accueil demandée par le membre, « Accueil » sinon.

    Lecture tolérante : sans membre, sans clé de chiffrement ou sur toute autre
    erreur de lecture, on garde la page par défaut de la plateforme.
    """
    try:
        email = comptes.utilisateur_courant(st)
        if not email:
            return "Accueil"
        pref = str(espace.preferences(email).get("page_accueil") or "Accueil")
    except Exception:  # noqa: BLE001
        return "Accueil"
    return pref if pref in _TITRES else "Accueil"


def _construire_pages() -> list:
    """La navigation du compte connecté, réduite à ce qu'il a le droit de voir.

    L'inscription étant ouverte, la barre latérale est le seul endroit où se
    joue la frontière entre l'espace du membre et le fonds de l'entreprise :
    une page non déclarée ici n'est pas atteignable.
    """
    visibles = navigation_acces.pages_visibles(
        PAGES_DEF, admin=comptes.est_admin_courant(st))
    pref = navigation_acces.page_par_defaut(visibles, page_accueil_preferee())
    return [st.Page(chemin, title=titre, default=(titre == pref))
            for chemin, titre in visibles]


st.navigation(_construire_pages()).run()
