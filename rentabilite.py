"""Mission 4 (modele a priori) : rentabilite ESTIMEE par prospect et par segment,
SANS donnees clients historiques. Proxy du CA potentiel = effectif x tarif moyen
de nettoyage par salarie (selon la categorie) ; marge = CA x taux.

Ce sont des ESTIMATIONS (hypotheses dans config.py), pas des chiffres reels :
elles servent a prioriser les segments les plus profitables a demarcher. Quand
l'entreprise disposera de donnees clients reelles, on remplacera ce modele par une
analyse retrospective (rentabilite reelle + churn).
"""
from __future__ import annotations

import pandas as pd

from config import (
    TARIF_NETTOYAGE_DEFAUT,
    TARIF_NETTOYAGE_PAR_SALARIE,
    TAUX_MARGE_NETTOYAGE,
)


def _to_int(v) -> int:
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
            return 0
        return int(float(v))
    except (ValueError, TypeError):
        return 0


def tarif(categorie) -> float:
    return float(TARIF_NETTOYAGE_PAR_SALARIE.get(str(categorie or "").strip(), TARIF_NETTOYAGE_DEFAUT))


def ca_estime(row) -> float:
    """CA annuel potentiel estime = effectif x tarif/salarie de la categorie."""
    return float(_to_int(row.get("effectif_nombre"))) * tarif(row.get("categorie_chruth"))


def marge_estimee(ca: float, taux: float = TAUX_MARGE_NETTOYAGE) -> float:
    return round(float(ca) * taux, 2)


def enrichir(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les colonnes ca_estime_eur et marge_estimee_eur (par prospect)."""
    df = df.copy()
    df["ca_estime_eur"] = df.apply(ca_estime, axis=1).round(0)
    df["marge_estimee_eur"] = (df["ca_estime_eur"] * TAUX_MARGE_NETTOYAGE).round(0)
    return df


def table_segments(df: pd.DataFrame) -> pd.DataFrame:
    """Agrege la rentabilite estimee par segment (categorie x priorite), classee
    par marge potentielle totale decroissante (segments les plus profitables)."""
    work = df if "ca_estime_eur" in df.columns else enrichir(df)
    grp = (
        work.groupby(["categorie_chruth", "priorite"], dropna=False)
        .agg(
            nb_prospects=("ca_estime_eur", "size"),
            ca_potentiel_total=("ca_estime_eur", "sum"),
            marge_potentielle_total=("marge_estimee_eur", "sum"),
            ca_moyen=("ca_estime_eur", "mean"),
        )
        .reset_index()
        .sort_values("marge_potentielle_total", ascending=False)
    )
    grp.insert(0, "rang", range(1, len(grp) + 1))
    for c in ("ca_potentiel_total", "marge_potentielle_total", "ca_moyen"):
        grp[c] = grp[c].round(0)
    return grp
