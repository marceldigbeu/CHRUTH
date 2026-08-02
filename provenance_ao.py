"""Identification lisible de la provenance et de la plateforme d'un AO.

Le canal de découverte (BOAMP, Maximilien...) n'est pas forcément l'endroit
où l'acheteur publie le DCE. Ce module maintient cette distinction sans
inventer une plateforme lorsque les liens ne permettent pas de la reconnaître.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping
from urllib.parse import urlparse


PLATEFORMES = (
    ("marches-publics.gouv.fr", "PLACE"),
    ("marches.maximilien.fr", "Maximilien"),
    ("maximilien.fr", "Maximilien"),
    ("achatpublic.com", "Achatpublic"),
    ("marches-publics.info", "Marchés-Publics.info"),
    ("e-marchespublics.com", "e-marchespublics"),
    ("e-marches-publics.com", "e-marchespublics"),
    ("daco-achats.fr", "Daco Achats"),
    ("marches-securises.fr", "Marchés-Sécurisés"),
    ("aws-achat.info", "AWS-Achat"),
    ("klekoon.com", "Klekoon"),
    ("dematis.com", "Dematis"),
    ("xmarches.fr", "XMarchés"),
    ("ternum-bfc.fr", "Territoires Numériques BFC"),
    ("megalis.bretagne.bzh", "Mégalis Bretagne"),
    ("boamp.fr", "BOAMP"),
)

LIBELLES_SOURCE = {
    "BOAMP": "BOAMP",
    "MAXIMILIEN": "Maximilien",
    "PLACE": "PLACE",
}


def _texte(valeur: Any) -> str:
    if valeur is None:
        return ""
    texte = str(valeur).strip()
    return "" if texte.casefold() in {"nan", "none", "nat"} else texte


def _sans_accents(texte: str) -> str:
    return "".join(
        caractere for caractere in unicodedata.normalize("NFKD", texte)
        if not unicodedata.combining(caractere)
    )


def hote(url: Any) -> str:
    """Renvoie un domaine normalisé, y compris pour une URL sans schéma."""
    valeur = _texte(url)
    if not valeur or not re.match(r"^(?:https?://|www\.)", valeur, re.I):
        return ""
    if valeur.lower().startswith("www."):
        valeur = "https://" + valeur
    domaine = (urlparse(valeur).hostname or "").lower().rstrip(".")
    domaine = _sans_accents(domaine)
    return domaine.removeprefix("www.")


def plateforme_url(url: Any) -> str:
    """Nom d'une plateforme connue, ou domaine explicite si elle est inconnue."""
    domaine = hote(url)
    if not domaine:
        return ""
    for suffixe, libelle in PLATEFORMES:
        if domaine == suffixe or domaine.endswith("." + suffixe):
            return libelle
    return f"Site externe ({domaine})"


def canal_decouverte(ligne: Mapping[str, Any]) -> str:
    """Canal qui a fourni l'avis, sans le confondre avec le profil acheteur."""
    source = _texte(ligne.get("source_decouverte") or ligne.get("source"))
    if source:
        return LIBELLES_SOURCE.get(source.upper(), source)
    avis = plateforme_url(ligne.get("url_avis") or ligne.get("url"))
    if avis in {"BOAMP", "Maximilien", "PLACE"}:
        return avis
    return "Source non identifiée"


def plateforme_publication(ligne: Mapping[str, Any]) -> str:
    """Plateforme qui porte le DCE, déduite des liens les plus fiables."""
    explicite = _texte(ligne.get("plateforme_publication"))
    if explicite:
        return explicite

    site_externe = ""
    for cle in ("url_profil_acheteur", "url_dce", "url"):
        plateforme = plateforme_url(ligne.get(cle))
        if plateforme:
            if plateforme == "BOAMP" and cle == "url":
                continue
            if plateforme.startswith("Site externe"):
                site_externe = site_externe or plateforme
                continue
            return plateforme
    return site_externe or "Plateforme non identifiée"


def detecter(ligne: Mapping[str, Any]) -> tuple[str, str]:
    """Renvoie (canal de découverte, plateforme de publication)."""
    return canal_decouverte(ligne), plateforme_publication(ligne)
