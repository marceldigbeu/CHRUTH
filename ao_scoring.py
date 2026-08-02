from __future__ import annotations

import re
from typing import Any

import pandas as pd

from ao_config import (
    AO_BUDGET_SCORE_BANDS,
    AO_BUDGET_SCORE_ABOVE,
    AO_BUDGET_SCORE_UNKNOWN,
    AO_PRIORITY_LABELS,
)
from ao_extract_fields import days_until, find_keywords, normalize_text


def _budget_value(row: dict[str, Any]) -> float | None:
    """Budget annualise si dispo, sinon budget total. None si inconnu."""
    for key in ("budget_annuel_eur", "budget_estime_eur"):
        raw = row.get(key)
        if raw is None:
            continue
        try:
            if pd.isna(raw):
                continue
            return float(raw)
        except Exception:
            continue
    return None


def _interpoler(ancres: list[tuple[float, float]], x: float) -> float:
    """Courbe affine par morceaux passant par `ancres`, plate au-dela des bornes.

    Un bareme en paliers place tous les marches d'une meme tranche a la meme
    valeur : 30 000 et 45 000 EUR recevaient 25 points chacun. En interpolant
    entre les paliers, chaque euro compte un peu — c'est ce qui permet ensuite
    de trier et de filtrer sur le score.
    """
    if x <= ancres[0][0]:
        return ancres[0][1]
    for (x0, y0), (x1, y1) in zip(ancres, ancres[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return ancres[-1][1]


def _ancres_budget() -> list[tuple[float, float]]:
    """Ancres deduites des tranches existantes : chaque tranche vaut ses points
    en son milieu, et la courbe relie ces milieux.

    On ne redefinit pas le bareme ici — il reste dans `ao_config`. Prendre le
    milieu plutot que la borne evite qu'un marche juste sous un plafond touche
    la note pleine de la tranche superieure.
    """
    ancres: list[tuple[float, float]] = []
    bas = 0.0
    for plafond, points in AO_BUDGET_SCORE_BANDS:
        ancres.append(((bas + plafond) / 2, float(points)))
        bas = plafond
    ancres.append((bas * 1.5, float(AO_BUDGET_SCORE_ABOVE)))
    return ancres


def _budget_score(budget: float | None) -> tuple[float, str]:
    if budget is None:
        return float(AO_BUDGET_SCORE_UNKNOWN), f"+{AO_BUDGET_SCORE_UNKNOWN} budget non affiche (a verifier)"
    points = _interpoler(_ancres_budget(), float(budget))
    signe = "+" if points >= 0 else ""
    montant = f"{budget:,.0f}".replace(",", " ")
    return points, f"{signe}{points:.1f} budget annualise {montant} EUR"


# Delai : meme principe que le budget, en milieu de palier.
# Paliers d'origine : < 5 j = -15 | 5 a 15 j = +5 | > 15 j = +10.
ANCRES_DELAI: list[tuple[float, float]] = [(2.5, -15.0), (10.0, 5.0), (30.0, 10.0)]
PENALITE_EXPIRE = -30.0

# Completude du dossier : a criteres metier egaux, un AO joignable passe devant.
CHAMPS_COMPLETUDE = ("email", "telephone", "nom_contact", "url_dce")
POIDS_COMPLETUDE = 2.0


def _delai_score(restant: int | None) -> tuple[float, str]:
    if restant is None:
        return 0.0, "0 date limite absente"
    if restant < 0:
        return PENALITE_EXPIRE, f"{PENALITE_EXPIRE:.0f} AO expire"
    points = _interpoler(ANCRES_DELAI, float(restant))
    signe = "+" if points >= 0 else ""
    return points, f"{signe}{points:.1f} delai {restant} j"


def _completude(row: dict[str, Any]) -> tuple[float, str]:
    """Part des coordonnees presentes, sur `POIDS_COMPLETUDE` points."""
    presents = sum(1 for c in CHAMPS_COMPLETUDE if str(row.get(c) or "").strip())
    points = POIDS_COMPLETUDE * presents / len(CHAMPS_COMPLETUDE)
    return points, f"+{points:.1f} dossier renseigne ({presents}/{len(CHAMPS_COMPLETUDE)})"


def _is_mapa(row: dict[str, Any]) -> bool:
    text = normalize_text(" ".join(str(row.get(k) or "") for k in ("procedure", "nature_avis", "objet", "criteres")))
    if any(token in text for token in ("adaptee", "mapa", "allotissement")):
        return True
    # "lots" en mot entier (evite ilots/pilotes) ; article R.2123-x quelle que soit la ponctuation.
    collapsed = re.sub(r"[^a-z0-9]", "", text)
    return bool(re.search(r"(?<![a-z])lots?(?![a-z])", text)) or "articler2123" in collapsed


def _pertinence_metier(text: str, categorie: str) -> tuple[float, str]:
    """Points metier, avec une part continue pour la densite de termes.

    Un intitule qui empile « nettoyage », « proprete » et « entretien des
    locaux » nous concerne plus surement qu'un intitule qui n'en porte qu'un.
    La densite ne peut pas faire changer de palier : elle departage a
    l'interieur du palier, elle ne le remplace pas.
    """
    core, secondaires = find_keywords(text)
    if core and categorie not in ("", "Mixte/Autre"):
        socle, plafond, trouves, libelle = 33.0, 35.0, core, "nettoyage + categorie claire"
    elif core:
        socle, plafond, trouves, libelle = 28.0, 30.0, core, "mots-cles nettoyage forts"
    elif secondaires:
        socle, plafond, trouves, libelle = 13.0, 15.0, secondaires, "mots-cles secondaires"
    else:
        return 0.0, "0 pertinence metier faible"
    points = min(plafond, socle + 0.5 * len(trouves))
    return points, f"+{points:.1f} {libelle} ({len(trouves)} termes)"


def compute_ao_score(row: dict[str, Any]) -> tuple[float, str, str]:
    """Score continu sur 100, arrondi a la decimale.

    Continu et non plus par paliers : voir `_interpoler`. La decimale n'est pas
    cosmetique, c'est elle qui departage les marches que l'ancien bareme laissait
    a egalite — et donc ce qui rend le tri et le filtre par score utilisables.
    """
    score = 0.0
    reasons: list[str] = []

    text = " ".join(
        str(row.get(key) or "")
        for key in ["objet", "acheteur", "procedure", "type_marche", "descripteur", "criteres", "texte_extraction"]
    )

    metier_points, metier_reason = _pertinence_metier(text, str(row.get("categorie") or ""))
    score += metier_points
    reasons.append(metier_reason)

    budget_points, budget_reason = _budget_score(_budget_value(row))
    score += budget_points
    reasons.append(budget_reason)

    if _is_mapa(row):
        score += 15
        reasons.append("+15 procedure adaptee / MAPA / allotissement")

    secteur = str(row.get("secteur") or "")
    if secteur and secteur != "Autre":
        score += 10
        reasons.append(f"+10 secteur cible {secteur}")

    delai_points, delai_reason = _delai_score(days_until(row.get("date_limite")))
    score += delai_points
    reasons.append(delai_reason)

    completude_points, completude_reason = _completude(row)
    score += completude_points
    reasons.append(completude_reason)

    confidence = int(row.get("niveau_confiance") or 0)
    score = round(max(0.0, min(100.0, score)), 1)
    priority = priority_from_score(score, confidence, row)
    return score, priority, " | ".join(reasons)


def priority_from_score(score: float, confidence: int, row: dict[str, Any]) -> str:
    if row.get("statut_extraction") == "DCE_A_TELECHARGER":
        return "A_VERIFIER"
    if confidence < 45 and score >= AO_PRIORITY_LABELS["TIEDE"]:
        return "A_VERIFIER"
    if score >= AO_PRIORITY_LABELS["CHAUD"]:
        return "CHAUD"
    if score >= AO_PRIORITY_LABELS["TIEDE"]:
        return "TIEDE"
    return "FROID"


def scoring_rules_table() -> pd.DataFrame:
    rows = [
        {"critere": "Nettoyage", "regle": "Mot-cle fort + categorie claire", "points": 35},
        {"critere": "Nettoyage", "regle": "Mot-cle secondaire seulement", "points": 15},
        {"critere": "Budget (annualise)", "regle": "<= 50 000 EUR / an (cible PME)", "points": 25},
        {"critere": "Budget (annualise)", "regle": "50 000 - 100 000 EUR / an", "points": 20},
        {"critere": "Budget (annualise)", "regle": "100 000 - 200 000 EUR / an", "points": 5},
        {"critere": "Budget (annualise)", "regle": "200 000 - 500 000 EUR / an", "points": -10},
        {"critere": "Budget (annualise)", "regle": "> 500 000 EUR / an (gros groupe)", "points": -20},
        {"critere": "Budget (annualise)", "regle": "Non affiche (frequent MAPA)", "points": 10},
        {"critere": "Procedure", "regle": "Procedure adaptee / MAPA / allotissement", "points": 15},
        {"critere": "Secteur cible", "regle": "Ecole / mairie / bat. admin / gymnase / mediatheque", "points": 10},
        {"critere": "Delai", "regle": "Date limite confortable (> 15 j)", "points": 10},
        {"critere": "Delai", "regle": "Delai critique (< 5 j)", "points": -15},
        {"critere": "Delai", "regle": "AO expire", "points": -30},
        {"critere": "Priorite", "regle": "Score >= 65 et confiance suffisante", "points": "CHAUD"},
        {"critere": "Priorite", "regle": "Score >= 40", "points": "TIEDE"},
        {"critere": "Priorite", "regle": "DCE requis / confiance faible", "points": "A_VERIFIER"},
    ]
    return pd.DataFrame(rows)
