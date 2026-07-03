"""Mission 3 (perf) - suivi des envois de messages : source de verite persistee.

Mirror du pattern crm.py : un CSV (suivi/suivi_envois.csv, gitignore) que l'on
charge et synchronise en PRESERVANT les statuts saisis a la main. Le .xlsx
livrable n'est qu'une vue rendue ; jamais la source.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from prospect_messages import cle_var

BASE_DIR = Path(__file__).resolve().parent
SUIVI_PATH = BASE_DIR / "suivi" / "suivi_envois.csv"

COLONNES = [
    "siret", "denomination", "ville", "segment", "variante", "template_id",
    "date_generation", "statut", "date_resultat",
]
STATUT_INITIAL = "A_ENVOYER"


def _norm_siret(s: str) -> str:
    """Normalise un siret : supprime le suffixe '.0' produit par un float pandas.

    Exemples : '123.0' -> '123', '12345678901234.0' -> '12345678901234', '123' -> '123'.
    """
    s = str(s).strip()
    if s.endswith(".0"):
        candidate = s[:-2]
        if candidate.isdigit():
            return candidate
    return s


def charger(path: Path = SUIVI_PATH) -> pd.DataFrame:
    p = Path(path)
    if p.exists():
        df = pd.read_csv(p, dtype=str).fillna("")
        for c in COLONNES:
            if c not in df.columns:
                df[c] = ""
        return df[COLONNES]
    return pd.DataFrame(columns=COLONNES)


def _segment(row) -> str:
    return f"{row['categorie_chruth']}|{row['priorite']}"


def synchroniser(df_prospects: pd.DataFrame, recommandations: dict | None = None,
                 path: Path = SUIVI_PATH) -> pd.DataFrame:
    reco = recommandations or {}
    existant = charger(path)
    connus = set(existant["siret"])

    # compteur de variantes deja attribuees par segment (pour continuer l'alternance)
    deja = existant.groupby("segment")["variante"].apply(list).to_dict()
    nouvelles = []
    src = df_prospects.copy()
    src["siret"] = src["siret"].astype(str).map(_norm_siret)
    src = src.sort_values("siret")  # ordre stable et deterministe
    for _, row in src.iterrows():
        siret = str(row["siret"])
        if siret in connus:
            continue
        seg = _segment(row)
        seg_reco = reco.get(seg)
        if seg_reco in ("A", "B"):
            var = seg_reco
        else:
            rang = len(deja.get(seg, []))
            var = "A" if rang % 2 == 0 else "B"
        deja.setdefault(seg, []).append(var)
        nouvelles.append({
            "siret": siret,
            "denomination": str(row.get("denomination", "")),
            "ville": str(row.get("libelle_commune", "")),
            "segment": seg,
            "variante": var,
            "template_id": cle_var(row["categorie_chruth"], row["priorite"], var),
            "date_generation": date.today().isoformat(),
            "statut": STATUT_INITIAL,
            "date_resultat": "",
        })

    df = pd.concat([existant, pd.DataFrame(nouvelles, columns=COLONNES)],
                   ignore_index=True)[COLONNES]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    return df
