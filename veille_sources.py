"""Fusion des sources affichées par la page Veille."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandas as pd


def _texte(valeur: Any) -> str:
    if valeur is None:
        return ""
    try:
        if pd.isna(valeur):
            return ""
    except (TypeError, ValueError):
        pass
    return str(valeur).strip()


def _premier(ligne: dict[str, Any], *cles: str) -> str:
    for cle in cles:
        valeur = _texte(ligne.get(cle))
        if valeur:
            return valeur
    return ""


def entree_boamp(ligne: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """Convertit une ligne SQLite BOAMP au format de la page Veille."""
    id_ao = _texte(ligne.get("id_ao"))
    if not id_ao:
        return None

    verdict = _texte(ligne.get("verdict_tri")).upper()
    if verdict not in {"PERTINENT", "REJETE"}:
        # La base ne contient que les avis déjà retenus par la collecte.
        verdict = "PERTINENT"

    entree = {
        "objet": _texte(ligne.get("objet")),
        "acheteur": _texte(ligne.get("acheteur")),
        "ville": _texte(ligne.get("ville")),
        "departement": _premier(ligne, "departement_prestation", "departement"),
        "date_publication": _texte(ligne.get("date_publication")),
        "date_limite": _texte(ligne.get("date_limite")),
        "procedure": _texte(ligne.get("procedure")),
        "url": _premier(ligne, "url_avis", "url_dce", "url_profil_acheteur"),
        "score": _texte(ligne.get("score_chruth")),
        "priorite": _texte(ligne.get("priorite")),
        "vu_le": _premier(ligne, "first_seen", "last_seen", "date_publication"),
        "tri": {
            "verdict": verdict,
            "etage": "collecte_boamp",
            "motif": _premier(ligne, "motif_tri", "raisons_scoring")
            or "Retenu par la collecte BOAMP",
            "terme": _texte(ligne.get("mots_cles_detectes")),
        },
        "correction_humaine": None,
        "traitement": "nouveau",
        "notifie_le": _texte(ligne.get("alerte_envoyee")) or None,
        "lu": False,
    }
    return id_ao, entree


def fusionner_boamp(
    etat: dict[str, Any], records: pd.DataFrame | None
) -> tuple[dict[str, Any], int]:
    """Ajoute les AO BOAMP absents sans écraser l’état partagé existant."""
    resultat = deepcopy(etat)
    aos = resultat.setdefault("aos", {})
    if records is None or records.empty:
        return resultat, 0

    ajoutes = 0
    for ligne in records.to_dict("records"):
        convertie = entree_boamp(ligne)
        if convertie is None:
            continue
        id_ao, entree = convertie
        if id_ao in aos:
            continue
        aos[id_ao] = entree
        ajoutes += 1
    return resultat, ajoutes
