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


def _budget_score(budget: float | None) -> tuple[int, str]:
    if budget is None:
        return AO_BUDGET_SCORE_UNKNOWN, f"+{AO_BUDGET_SCORE_UNKNOWN} budget non affiche (a verifier)"
    for plafond, points in AO_BUDGET_SCORE_BANDS:
        if budget <= plafond:
            signe = "+" if points >= 0 else ""
            return points, f"{signe}{points} budget annualise <= {plafond:,} EUR".replace(",", " ")
    return AO_BUDGET_SCORE_ABOVE, f"{AO_BUDGET_SCORE_ABOVE} gros budget (> {AO_BUDGET_SCORE_BANDS[-1][0]:,} EUR)".replace(",", " ")


def _is_mapa(row: dict[str, Any]) -> bool:
    text = normalize_text(" ".join(str(row.get(k) or "") for k in ("procedure", "nature_avis", "objet", "criteres")))
    if any(token in text for token in ("adaptee", "mapa", "allotissement")):
        return True
    # "lots" en mot entier (evite ilots/pilotes) ; article R.2123-x quelle que soit la ponctuation.
    collapsed = re.sub(r"[^a-z0-9]", "", text)
    return bool(re.search(r"(?<![a-z])lots?(?![a-z])", text)) or "articler2123" in collapsed


def compute_ao_score(row: dict[str, Any]) -> tuple[int, str, str]:
    score = 0
    reasons: list[str] = []

    text = " ".join(
        str(row.get(key) or "")
        for key in ["objet", "acheteur", "procedure", "type_marche", "descripteur", "criteres", "texte_extraction"]
    )

    core_keywords, secondary_keywords = find_keywords(text)
    categorie = str(row.get("categorie") or "")
    if core_keywords and categorie not in ("", "Mixte/Autre"):
        score += 35
        reasons.append("+35 nettoyage + categorie claire")
    elif core_keywords:
        score += 30
        reasons.append("+30 mots-cles nettoyage forts")
    elif secondary_keywords:
        score += 15
        reasons.append("+15 mots-cles secondaires")
    else:
        reasons.append("0 pertinence metier faible")

    budget = _budget_value(row)
    budget_points, budget_reason = _budget_score(budget)
    score += budget_points
    reasons.append(budget_reason)

    if _is_mapa(row):
        score += 15
        reasons.append("+15 procedure adaptee / MAPA / allotissement")

    secteur = str(row.get("secteur") or "")
    if secteur and secteur != "Autre":
        score += 10
        reasons.append(f"+10 secteur cible {secteur}")

    remaining = days_until(row.get("date_limite"))
    if remaining is None:
        reasons.append("0 date limite absente")
    elif remaining < 0:
        score -= 30
        reasons.append("-30 AO expire")
    elif remaining < 5:
        score -= 15
        reasons.append(f"-15 delai critique {remaining}j")
    elif remaining <= 15:
        score += 5
        reasons.append(f"+5 delai court {remaining}j")
    else:
        score += 10
        reasons.append(f"+10 delai confortable {remaining}j")

    confidence = int(row.get("niveau_confiance") or 0)
    score = max(0, min(100, int(score)))
    priority = priority_from_score(score, confidence, row)
    return score, priority, " | ".join(reasons)


def priority_from_score(score: int, confidence: int, row: dict[str, Any]) -> str:
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
