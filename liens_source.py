"""Retour a la source : reconnaitre les colonnes qui portent une adresse web.

Un AO affiche hors de son avis d'origine oblige a rechercher le marche a la main
sur BOAMP ou Maximilien pour lire les pieces. Toutes les surfaces doivent donc
offrir le lien — et comme chaque onglet Excel n'expose pas les memes colonnes,
on les reconnait au nom plutot que de les enumerer une par une.
"""
from __future__ import annotations

from typing import Iterable

# Libelles lisibles des colonnes connues. Les autres colonnes de lien gardent
# un libelle deduit de leur nom : mieux vaut « Url Machin » qu'aucun lien.
LIBELLES = {
    "url_avis": "Avis d'origine",
    "url": "Avis d'origine",
    "lien": "Avis d'origine",
    "url_dce": "Dossier de consultation",
    "url_profil_acheteur": "Profil acheteur",
}
MARQUEURS = ("url", "lien")


def est_colonne_de_lien(nom: str) -> bool:
    """Vrai si le nom de colonne designe une adresse web."""
    minuscule = str(nom or "").strip().casefold()
    return any(marqueur in minuscule for marqueur in MARQUEURS)


def colonnes_de_lien(colonnes: Iterable[str]) -> list[str]:
    """Colonnes de liens presentes, dans l'ordre ou elles arrivent."""
    return [c for c in colonnes if est_colonne_de_lien(c)]


def libelle(nom: str) -> str:
    """Libelle a afficher pour une colonne de lien."""
    connu = LIBELLES.get(str(nom or "").strip().casefold())
    if connu:
        return connu
    return str(nom or "").replace("_", " ").strip().capitalize()


def premiere_source(ligne: dict) -> str:
    """Meilleure adresse disponible pour un AO : l'avis d'abord, le DCE ensuite.

    L'avis prime parce qu'il est public et stable ; le DCE demande souvent un
    compte et peut disparaitre une fois la consultation close.
    """
    for cle in ("url_avis", "url", "lien", "url_dce", "url_profil_acheteur"):
        valeur = str(ligne.get(cle) or "").strip()
        if valeur.startswith(("http://", "https://")):
            return valeur
    return ""
