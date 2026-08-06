"""Plateforme de veille CHRUTH — consulter, corriger, suivre.

Lit l'etat produit par le veilleur (GitHub Actions) et le reecrit au meme endroit.
Aucune logique de tri ici : les verdicts viennent de ao_pertinence, cette page
n'affiche que ce qui a deja ete decide et enregistre les jugements humains.

Lancement local  : double-clic LANCER_APP_CHRUTH.bat (page « Veille »)
Source distante  : CHRUTH_VEILLE_SOURCE=github + CHRUTH_GITHUB_REPO + CHRUTH_GITHUB_TOKEN
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

import ao_db
import ao_maximilien_veille
import provenance_ao
import veille_depot
import veille_etat
import veille_sources
from veille_etat import TRAITEMENTS, verdict_effectif

LIBELLE_TRAITEMENT = {
    "nouveau": "Nouveau",
    "a_traiter": "À traiter",
    "repondu": "Répondu",
    "abandonne": "Abandonné",
}

# Couleurs Streamlit (:couleur[texte]) pilotees par la donnee : la priorite et le
# verdict se lisent d'un coup d'oeil, sans avoir a decoder un chiffre.
COULEUR_PRIORITE = {"CHAUD": "red", "CHAUDE": "red", "TIEDE": "orange",
                    "TIÈDE": "orange", "FROID": "gray", "FROIDE": "gray"}
COULEUR_VERDICT = {"PERTINENT": "green", "REJETE": "red"}
FICHE_AMORCE = Path(__file__).resolve().parent / "config_chruth" / "fiche_chruth.md"

# Fenetres de fraicheur proposees, en jours. None = pas de borne.
PERIODES = {
    "Tout": None,
    "7 derniers jours": 7,
    "14 derniers jours": 14,
    "30 derniers jours": 30,
    "Depuis une date précise": "libre",
}

# set_page_config n'a le droit d'etre appele qu'une fois : l'entree multipage
# (CHRUTH_APP.py) l'a deja fait. On garde l'appel pour l'usage en page isolee.
try:
    st.set_page_config(page_title="Veille CHRUTH", layout="wide")
except st.errors.StreamlitAPIException:
    pass


# --- Etat ------------------------------------------------------------------

def charger():
    """Fusionne l'état partagé et la base BOAMP produite dans Streamlit."""
    etat, sha = veille_depot.lire()
    try:
        records = ao_db.fetch_records()
    except Exception:  # la veille partagée reste utilisable si SQLite est indisponible
        return etat, sha, 0
    etat, ajoutes = veille_sources.fusionner_boamp(etat, records)
    return etat, sha, ajoutes


def mettre_a_jour() -> str:
    """Va chercher les nouveaux AO. Renvoie un message pour l'utilisateur.

    Deux chemins, et la distinction n'est pas cosmetique :

    - **source locale** : on collecte ici meme, sans envoyer d'email. L'app est une
      fenetre sur la veille, ce n'est pas elle qui notifie.
    - **source github** : on demande au workflow de tourner. Collecter ici marquerait
      les AO comme vus dans l'etat partage, et le veilleur ne les notifierait plus
      jamais — un AO vu par l'app serait un AO perdu.
    """
    if veille_depot.source() == "github":
        if veille_depot.declencher_veille():
            return "Veille lancée. Les résultats arrivent dans quelques minutes."
        return ("Lancement à distance indisponible : jeton GitHub absent "
                "(CHRUTH_GITHUB_TOKEN).")

    ao_maximilien_veille.veiller(etat_path=veille_depot.chemin_local(), envoyer=False)
    return "Mise à jour terminée."


def enregistrer(etat, sha, message: str) -> None:
    try:
        veille_depot.ecrire(etat, sha, message)
    except PermissionError as exc:
        st.error(str(exc))
    except Exception as exc:  # noqa: BLE001
        st.error(f"Enregistrement impossible : {exc}")


etat, sha, ao_boamp_ajoutes = charger()
aos = etat.get("aos", {})


# --- Barre laterale : filtres ----------------------------------------------

def score_de(entree: dict) -> float:
    """Score de l'AO en nombre. 0 si absent ou illisible — un score manquant ne
    doit pas faire disparaitre l'AO d'un filtre, seulement le placer en bas."""
    try:
        return float(entree.get("score") or 0)
    except (TypeError, ValueError):
        return 0.0


with st.sidebar:
    st.header("Filtres")
    priorites_vues = sorted({str(a.get("priorite") or "?") for a in aos.values()})
    priorites = st.multiselect("Priorité", priorites_vues, default=[], key="priorites")

    # La jauge : le score etant continu a la decimale, le pas de 0,5 separe
    # reellement les AO — avec l'ancien bareme en paliers de 5, la deplacer
    # d'un cran faisait disparaitre des dizaines de marches d'un coup.
    score_min = st.slider("Score minimum", 0.0, 100.0, 0.0, 0.5, key="score_min",
                          help="Ne garder que les AO au-dessus de ce score.")
    classement = st.selectbox("Classer par", ["Fraîcheur", "Score décroissant"],
                              key="classement")

    departements_vus = sorted({str(a.get("departement") or "--") for a in aos.values()})
    departements = st.multiselect("Département", departements_vus, default=[], key="departements")

    periode = st.selectbox("Publié depuis", list(PERIODES), key="publie_depuis")
    choix = PERIODES[periode]
    if choix == "libre":
        publie_apres = st.date_input("À partir du", value=date.today() - timedelta(days=30),
                                     key="publie_depuis_date", format="DD/MM/YYYY")
    elif choix is None:
        publie_apres = None
    else:
        publie_apres = date.today() - timedelta(days=choix)

    voir_rejetes = st.checkbox("Afficher les AO rejetés par le tri", value=False,
                               key="voir_rejetes")
    non_lus_seuls = st.checkbox("Non lus seulement", value=False, key="non_lus")

    actifs = []
    if priorites:
        actifs.append("priorité " + ", ".join(priorites))
    if score_min > 0:
        actifs.append(f"score ≥ {score_min:.1f}")
    if classement != "Fraîcheur":
        actifs.append("classé par score")
    if departements:
        actifs.append("dépt " + ", ".join(departements))
    if periode != "Tout":
        actifs.append(periode.lower())
    if voir_rejetes:
        actifs.append("rejetés inclus")
    if non_lus_seuls:
        actifs.append("non lus seulement")
    st.caption("Filtres actifs : " + ("; ".join(actifs) if actifs else "aucun"))

    st.divider()
    st.subheader("Notifications")

    notifs = veille_etat.notifications_actives(etat)
    if notifs:
        st.caption("Chaque nouvel AO pertinent part par email.")
    else:
        st.warning("Notifications suspendues : aucun email ne part. "
                   "Les AO continuent d'arriver ici et seront envoyés à la reprise.")

    if st.button("Désactiver les notifications" if notifs else "Activer les notifications",
                 key="notifs"):
        veille_etat.definir_notifications(etat, not notifs)
        enregistrer(etat, sha, "notifications " + ("OFF" if notifs else "ON"))
        st.rerun()

    st.divider()
    sources = ["état partagé" if veille_depot.source() == "github" else "état local"]
    if ao_boamp_ajoutes:
        sources.append(f"base des appels d'offres ({ao_boamp_ajoutes} ajoutés)")
    st.caption("Données : " + " + ".join(sources))
    if etat.get("maj_le"):
        st.caption(f"État mis à jour : {etat['maj_le'][:16].replace('T', ' ')}")
    st.caption(f"{len(aos)} AO dans l'état")

    if st.button("Mettre à jour maintenant", key="maj", type="primary"):
        attente = ("Consultation de Maximilien et tri en cours…"
                   if veille_depot.source() == "local"
                   else "Demande de vérification envoyée…")
        try:
            with st.spinner(attente):
                message = mettre_a_jour()
            st.success(message)
            if veille_depot.source() == "local":
                st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Mise à jour impossible : {exc}")

    if veille_depot.source() == "local":
        st.caption("La mise à jour collecte et trie ici, sans envoyer d'email.")
    else:
        st.caption("La mise à jour relance le veilleur, qui notifiera les nouveaux AO.")


# --- Selection --------------------------------------------------------------

def _garde(entree: dict) -> bool:
    if not voir_rejetes and verdict_effectif(entree) == "REJETE":
        return False
    if priorites and str(entree.get("priorite") or "?") not in priorites:
        return False
    if departements and str(entree.get("departement") or "--") not in departements:
        return False
    if non_lus_seuls and entree.get("lu"):
        return False
    if score_de(entree) < score_min:
        return False
    if publie_apres is not None:
        publie = str(entree.get("date_publication") or "")
        # Date manquante : on garde. Comme pour le tri, le doute profite a l'AO —
        # un marche peut-etre frais ne doit pas disparaitre sur une donnee absente.
        # La ligne l'affiche « date inconnue », le lecteur tranche.
        if publie and publie < publie_apres.isoformat():
            return False
    return True


def _fraicheur(entree: dict) -> tuple[str, str]:
    """Cle de classement : date de publication de l'avis d'abord.

    C'est la fraicheur reelle de l'AO, pas celle de notre collecte : un avis publie
    il y a deux mois et decouvert ce matin n'est pas une nouveaute. La date de
    decouverte ne departage que les publications du meme jour, et les AO d'avant
    la capture de ce champ (sans date) descendent en fin de fil.
    """
    return (str(entree.get("date_publication") or ""), str(entree.get("vu_le") or ""))


retenus = [(i, e) for i, e in aos.items() if _garde(e)]
if classement == "Score décroissant":
    # A score egal on retombe sur la fraicheur : deux marches equivalents se
    # departagent par la date, jamais par l'ordre d'arrivee dans le fichier.
    retenus.sort(key=lambda couple: (score_de(couple[1]), _fraicheur(couple[1])), reverse=True)
else:
    retenus.sort(key=lambda couple: _fraicheur(couple[1]), reverse=True)


# --- Fil des AO -------------------------------------------------------------

st.title("Veille appels d'offres")

if not aos:
    st.info("Aucun appel d'offres dans l'état pour le moment. "
            "La veille écrit ici à chaque passage.")
elif not retenus:
    st.warning("Aucun AO ne correspond aux filtres.")
else:
    total = len(aos)
    resume = f"{len(retenus)} appel(s) d'offres affiché(s)"
    if len(retenus) != total:
        resume += f" sur {total}"
    st.caption(resume)

for id_ao, entree in retenus:
    with st.container(border=True):
        verdict = verdict_effectif(entree)
        tri = entree.get("tri") or {}
        corrige = bool(entree.get("correction_humaine"))

        # Repere de nouveaute en texte (pas d'icone) : lisible et sobre.
        prefixe = ":blue[**Nouveau**] · " if not entree.get("lu") else ""
        st.markdown(f"{prefixe}**{entree.get('objet', '(sans intitulé)')}**")

        publie = entree.get("date_publication") or "date inconnue"
        prio = str(entree.get("priorite") or "")
        c_prio = COULEUR_PRIORITE.get(prio.upper(), "gray")
        # Score a la decimale : c'est elle qui departage deux AO de meme priorite.
        score_txt = f" {score_de(entree):.1f}" if entree.get("score") not in (None, "") else ""
        prio_txt = f":{c_prio}[{prio}{score_txt}]".strip() if prio else ""
        ligne = (f"{entree.get('acheteur', '')} — {entree.get('ville', '')} "
                 f"({entree.get('departement') or '--'}) · publié le {publie} · limite "
                 f"{entree.get('date_limite') or 'non précisée'} · {prio_txt}")
        st.markdown(ligne)

        decouverte, plateforme = provenance_ao.detecter(entree)
        st.caption(
            f"Découvert via : {decouverte} · Dossier publié sur : {plateforme}"
        )

        origine = "corrigé à la main" if corrige else f"tri {tri.get('etage', '')}"
        c_verdict = COULEUR_VERDICT.get(verdict, "gray")
        st.markdown(f"Verdict : :{c_verdict}[**{verdict}**] — {tri.get('motif', '')} "
                    f"_({origine})_")

        if entree.get("url"):
            libelle_lien = (f"Ouvrir sur {plateforme}"
                            if not plateforme.startswith(("Plateforme", "Site externe"))
                            else "Ouvrir la consultation")
            st.markdown(f"[{libelle_lien}]({entree['url']})")

        # Passerelle vers la redaction : on juge un marche ici, on l'ecrit
        # ailleurs. Sans ce bouton il faut aller le retrouver a la main dans la
        # liste de la page Messages.
        if st.button("Rédiger un message", key=f"redaction_{id_ao}"):
            st.session_state["ao_a_rediger"] = id_ao
            st.switch_page("app_messages.py")

        colonnes = st.columns([1, 1, 1, 2])
        with colonnes[0]:
            if st.button("Pertinent", key=f"ok_{id_ao}"):
                veille_etat.corriger(etat, id_ao, "PERTINENT")
                enregistrer(etat, sha, f"correction {id_ao} -> PERTINENT")
                st.rerun()
        with colonnes[1]:
            if st.button("Pas pertinent", key=f"ko_{id_ao}"):
                veille_etat.corriger(etat, id_ao, "REJETE")
                enregistrer(etat, sha, f"correction {id_ao} -> REJETE")
                st.rerun()
        with colonnes[2]:
            libelle = "Marquer non lu" if entree.get("lu") else "Marquer lu"
            if st.button(libelle, key=f"lu_{id_ao}"):
                veille_etat.marquer_lu(etat, id_ao, not entree.get("lu"))
                enregistrer(etat, sha, f"lecture {id_ao}")
                st.rerun()
        with colonnes[3]:
            courant = entree.get("traitement", "nouveau")
            if courant not in TRAITEMENTS:
                courant = "nouveau"
            choisi = st.selectbox("Suivi", list(TRAITEMENTS),
                                  index=list(TRAITEMENTS).index(courant),
                                  format_func=lambda s: LIBELLE_TRAITEMENT.get(s, s),
                                  key=f"trait_{id_ao}", label_visibility="collapsed")
            if choisi != courant:
                veille_etat.definir_traitement(etat, id_ao, choisi)
                enregistrer(etat, sha, f"suivi {id_ao} -> {choisi}")
                st.rerun()


# --- Guide des messages -----------------------------------------------------
# Information d'entreprise : masquee tant que l'acces a l'app n'est pas restreint
# (spec 10). CHRUTH_VEILLE_GUIDE=1 l'active en connaissance de cause.

if os.environ.get("CHRUTH_VEILLE_GUIDE", "").strip() == "1":
    st.header("Guide des messages")
    st.caption("Alimente la rédaction des messages et le prompt de tri. "
               "Ce qui est saisi ici fait foi.")

    amorce = etat.get("guide_messages", "")
    if not amorce:
        try:
            amorce = FICHE_AMORCE.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            amorce = ""

    texte = st.text_area("Guide", value=amorce, height=280, key="guide",
                         label_visibility="collapsed")
    if st.button("Enregistrer le guide", key="enregistrer_guide"):
        veille_etat.definir_guide(etat, texte)
        enregistrer(etat, sha, "guide des messages")
        st.success("Guide enregistré.")
