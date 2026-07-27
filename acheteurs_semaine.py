"""Acheteurs actifs de la semaine : les organisations ayant publié un AO
propreté pertinent sur 7 jours glissants, classées et enrichies.

Remplace l'ancienne collecte « toutes les entreprises IDF » comme source de
prospection (celle-ci est mise en sommeil, non supprimée).
"""
from __future__ import annotations

from ao_extract_fields import normalize_text

FENETRE_JOURS = 7
PRIORITES_PERTINENTES = ("CHAUD", "TIEDE", "TIÈDE")

# Indices de droit public dans le nom, quand la catégorie juridique manque.
_MOTS_PUBLIC = ("mairie", "commune", "ville de", "departement", "département",
                "prefecture", "préfecture", "region", "région", "hopital",
                "hôpital", "centre hospitalier", "ccas", "etablissement public",
                "établissement public", "communaute", "communauté", "metropole",
                "métropole", "syndicat", "academie", "académie", "rectorat")


def classer(nature_juridique: str, nom: str = "") -> tuple[str, bool]:
    """(type, incertain) : 'public' si catégorie juridique niveau I = « 7 »,
    sinon 'prive'. Sans catégorie, repli sur le nom, marqué incertain."""
    code = str(nature_juridique or "").strip()
    if code[:1] == "7":
        return ("public", False)
    if code:
        return ("prive", False)
    n = normalize_text(nom or "")
    for mot in _MOTS_PUBLIC:
        if normalize_text(mot) in n:
            return ("public", True)
    return ("prive", True)
