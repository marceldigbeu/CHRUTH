"""Logique de la page d'accueil, hors Streamlit.

Meme partage que pour la carte ou les acheteurs : le calcul vit dans un module
ordinaire, la page ne fait que l'afficher. C'est ce qui permet de le tester sans
navigateur ni serveur.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

ECHEANCES_AFFICHEES = 5
COLONNE_JOURS = "jours_avant_limite"


def jours_restants(valeur, aujourd_hui: date | None = None) -> int | None:
    """Jours avant la date limite. None si la date est absente ou illisible."""
    aujourd_hui = aujourd_hui or date.today()
    texte = str(valeur or "").strip()[:10]
    if not texte:
        return None
    try:
        return (date.fromisoformat(texte) - aujourd_hui).days
    except ValueError:
        return None


def prochaines_echeances(df: pd.DataFrame, limite: int = ECHEANCES_AFFICHEES,
                         aujourd_hui: date | None = None) -> pd.DataFrame:
    """AO prioritaires dont la date limite approche, du plus urgent au moins urgent.

    Trois exclusions, chacune pour eviter de faire perdre du temps a l'ouverture :
    les marches expires, ceux que le tri a juges hors sujet, et les froids.

    La colonne de tri ne commence pas par un tiret bas : `itertuples` renomme
    silencieusement les colonnes ainsi nommees, et la page lirait un champ absent.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    travail = df[df["priorite"].astype(str).isin(("CHAUD", "TIEDE"))].copy()
    if "verdict_tri" in travail.columns:
        travail = travail[travail["verdict_tri"].astype(str) != "REJETE"]
    if travail.empty:
        return pd.DataFrame()
    travail[COLONNE_JOURS] = travail["date_limite"].map(
        lambda v: jours_restants(v, aujourd_hui))
    travail = travail[travail[COLONNE_JOURS].notna() & (travail[COLONNE_JOURS] >= 0)]
    return travail.sort_values(COLONNE_JOURS).head(limite)


RETENUS_AFFICHES = 5


def retenus_par_le_tri(aos: dict, limite: int = RETENUS_AFFICHES) -> list[tuple[str, dict]]:
    """AO de la veille juges pertinents, du plus recemment publie au plus ancien.

    Deux sources coexistent et ne disent pas la meme chose : la base porte les
    marches collectes et scores, l'etat de veille porte le jugement du tri. Ce
    bloc montre le second — ce que le tri a retenu — la ou les echeances
    viennent du premier. Les fusionner masquerait qu'un marche peut etre juge
    pertinent sans etre encore en base.
    """
    if not aos:
        return []
    retenus = [(i, e) for i, e in aos.items() if _verdict(e) == "PERTINENT"]
    retenus.sort(key=lambda couple: (str(couple[1].get("date_publication") or ""),
                                     str(couple[1].get("vu_le") or "")), reverse=True)
    return retenus[:limite]


def _verdict(entree: dict) -> str:
    """Verdict qui fait foi : la correction humaine prime sur le tri automatique.

    On duplique ici la regle de `veille_etat.verdict_effectif` plutot que de
    l'importer : ce module ne doit dependre que de pandas, pour rester testable
    sans etat de veille sur disque.
    """
    correction = entree.get("correction_humaine") or {}
    if correction.get("verdict"):
        return correction["verdict"]
    return (entree.get("tri") or {}).get("verdict", "")


def date_lisible(valeur) -> str:
    """Date au format francais. La valeur brute est parfois un horodatage ISO
    complet (« 2026-07-28T14:00:00+00:00 ») : l'afficher tel quel donne une
    ligne illisible pour une information qui tient en dix caracteres."""
    texte = str(valeur or "").strip()[:10]
    try:
        return date.fromisoformat(texte).strftime("%d/%m/%Y")
    except ValueError:
        return texte


def couleur_urgence(jours: int) -> str:
    """Rouge sous une semaine, orange sous quinze jours, vert au-dela."""
    if jours <= 7:
        return "red"
    return "orange" if jours <= 15 else "green"
