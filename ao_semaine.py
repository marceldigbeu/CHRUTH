from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

TOP20_COLUMNS = [
    "rang", "score_chruth", "priorite", "objet", "acheteur",
    "ville", "departement", "budget_estime_eur", "date_limite", "url_avis",
]


def iso_week_bounds(today: date) -> tuple[date, date]:
    """Retourne (lundi, dimanche) de la semaine ISO contenant `today`."""
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def iso_week_label(today: date) -> str:
    year, week, _ = today.isocalendar()
    return f"{year}-W{week:02d}"


def _pub_dates(df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(df.get("date_publication"), errors="coerce").dt.date


def add_semaine_iso(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    dates = _pub_dates(df)
    df["semaine_iso"] = [iso_week_label(d) if pd.notna(d) and d is not None else "" for d in dates]
    return df


def build_top20_ouverts(df: pd.DataFrame, today: date | None = None) -> pd.DataFrame:
    """Top 20 des AO ENCORE OUVERTS (date limite a venir ou inconnue), par score decroissant.
    Independant de la date de publication -> toujours rempli tant qu'il reste des AO ouverts."""
    today = today or date.today()
    cols = [c for c in TOP20_COLUMNS if c != "rang"]
    out_columns = TOP20_COLUMNS[:1] + (["id_ao"] if df is not None and "id_ao" in df.columns else []) + cols
    if df is None or df.empty:
        return pd.DataFrame(columns=out_columns)
    work = df.copy()
    work["_lim"] = pd.to_datetime(work.get("date_limite"), errors="coerce").dt.date
    work["_score"] = pd.to_numeric(work.get("score_chruth"), errors="coerce").fillna(0)
    # Ouvert = date limite a venir (>= today) OU inconnue (on ne masque pas un AO sans date).
    mask = work["_lim"].apply(lambda d: d is None or pd.isna(d) or d >= today)
    sel = work[mask].sort_values("_score", ascending=False).head(20)
    has_id_ao = "id_ao" in sel.columns
    for c in cols:
        if c not in sel.columns:
            sel[c] = ""
    select_cols = (["id_ao"] if has_id_ao else []) + cols
    sel = sel[select_cols].reset_index(drop=True)
    sel.insert(0, "rang", range(1, len(sel) + 1))
    return sel
