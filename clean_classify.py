import re
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

from config import (
    CODES_NAF, NAF_EXCLUS, EXCLUSION_KEYWORDS,
    TRANCHE_EFFECTIF, NAF_PREFIX_MAP, REGION_MAPPING,
    CATEGORIES_EXCLUES_PROSPECTION,
)

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_latest_raw() -> pd.DataFrame:
    # Du plus recent au plus ancien : on saute les dumps illisibles (ex. collecte
    # interrompue => JSON tronque) et on prend le premier fichier valide.
    files = sorted(DATA_DIR.glob("raw_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError("Aucun fichier raw_*.json dans data/")
    erreurs = []
    for latest in files:
        print(f"Chargement : {latest}")
        try:
            with open(latest, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  [ATTENTION] dump illisible ignore : {latest.name} ({exc})")
            erreurs.append(latest.name)
            continue
        return pd.DataFrame(data)
    raise ValueError(
        "Aucun dump raw_*.json valide dans data/. Fichiers corrompus : " + ", ".join(erreurs)
        + ". Relancer une collecte complete."
    )


def filter_active_etablissements(df: pd.DataFrame) -> pd.DataFrame:
    if "etat_administratif" not in df.columns:
        return df
    mask = df["etat_administratif"] == "A"
    n = (~mask).sum()
    if n:
        df = df[mask]
        print(f"  Ets inactifs supprimes : {n}")
    return df


def filter_excluded_naf(df: pd.DataFrame) -> pd.DataFrame:
    if "naf_code" not in df.columns:
        return df
    mask = df["naf_code"].isin(NAF_EXCLUS)
    n = mask.sum()
    if n:
        df = df[~mask]
        print(f"  NAF exclus (81.21Z,81.22Z,81.29Z) : {n}")
    return df


def filter_excluded_keywords(df: pd.DataFrame) -> pd.DataFrame:
    pattern = "|".join(EXCLUSION_KEYWORDS)
    text_cols = ["denomination", "enseigne"]
    mask = pd.Series([False] * len(df), index=df.index)
    for col in text_cols:
        if col in df.columns:
            mask |= df[col].fillna("").str.lower().str.contains(pattern, na=False)
    n = mask.sum()
    if n:
        df = df[~mask]
        print(f"  Exclus mot-cle (desinfection, crime...) : {n}")
    return df


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    if "siret" not in df.columns:
        return df
    before = len(df)
    df = df.drop_duplicates(subset="siret", keep="first")
    n = before - len(df)
    print(f"  Dédoublonnage SIRET : {n} doublons")
    return df


def normalize_adresse(df: pd.DataFrame) -> pd.DataFrame:
    adresse_col = df["adresse"].fillna("")
    if all(c in df.columns for c in ["numero_voie", "type_voie", "libelle_voie"]):
        fallback = (df["numero_voie"].fillna("") + " " +
                    df["type_voie"].fillna("") + " " +
                    df["libelle_voie"].fillna(""))
        df["adresse_complete"] = adresse_col.where(adresse_col != "", other=fallback.str.strip())
    else:
        df["adresse_complete"] = adresse_col
    return df


def decode_effectif(code: str) -> tuple[str, int]:
    """Code tranche INSEE ('NN','01','12'...) -> (libelle, effectif representatif)."""
    code = str(code or "").strip()
    return TRANCHE_EFFECTIF.get(code, ("Non renseigné", -1))


def classify_naf(naf_code: str) -> tuple[str, str]:
    """Classe par FAMILLE NAF (prefixe 4 car.) pour absorber les sous-codes et
    anciens codes renvoyes par l'API (85.1C, 86.22C, 86.90D...)."""
    code = str(naf_code or "").strip()
    if code in CODES_NAF:
        return (CODES_NAF[code]["cible"], CODES_NAF[code]["label"])
    prefix = code[:4]  # ex "86.2" depuis "86.22C"
    if prefix in NAF_PREFIX_MAP:
        return NAF_PREFIX_MAP[prefix]
    return ("AUTRE", "Autre")


def domaine_from_categorie(categorie: str) -> str:
    """Separe les prospects entre domaine public, domaine prive et lignes a verifier."""
    value = str(categorie or "").strip().upper()
    if value.startswith("PUB_"):
        return "PUBLIC"
    if value in {"", "AUTRE", "NAN", "NONE"}:
        return "A_CLASSER"
    return "PRIVE"


def filter_categories_cibles(df: pd.DataFrame) -> pd.DataFrame:
    """Garde uniquement les categories ciblees par CHRUTH (retire location-immo + non classes)."""
    if "categorie_chruth" not in df.columns:
        return df
    mask = df["categorie_chruth"].isin(CATEGORIES_EXCLUES_PROSPECTION)
    n = int(mask.sum())
    if n:
        df = df[~mask]
        print(f"  Categories hors cible retirees ({', '.join(sorted(CATEGORIES_EXCLUES_PROSPECTION))}) : {n}")
    return df


def classify(df: pd.DataFrame) -> pd.DataFrame:
    df["categorie_chruth"] = df["naf_code"].map(lambda c: classify_naf(str(c))[0])
    df["sous_categorie"] = df["naf_code"].map(lambda c: classify_naf(str(c))[1])
    df["domaine_chruth"] = df["categorie_chruth"].map(domaine_from_categorie)

    df["date_creation"] = df["date_creation"].astype(str)
    df["age_annees"] = df["date_creation"].apply(
        lambda d: (datetime.now() - datetime.strptime(d[:10], "%Y-%m-%d")).days / 365.25
        if len(d) >= 10 and d[:4].isdigit() else -1
    )

    decoded = df["tranche_effectif_salarie"].apply(decode_effectif)
    df["effectif_code"] = df["tranche_effectif_salarie"].astype(str).str.strip()
    df["effectif_label"] = decoded.apply(lambda t: t[0])
    df["effectif_nombre"] = decoded.apply(lambda t: t[1])

    if "region" in df.columns:
        df["region_nom"] = df["region"].map(REGION_MAPPING).fillna(df["region"])

    return df


def main():
    print("=== NETTOYAGE & CLASSIFICATION ===")

    df = load_latest_raw()
    print(f"  Charge : {len(df)} lignes")

    df = filter_active_etablissements(df)
    df = filter_excluded_naf(df)
    df = filter_excluded_keywords(df)
    df = deduplicate(df)
    df = normalize_adresse(df)
    df = classify(df)
    df = filter_categories_cibles(df)
    df = df.reset_index(drop=True)

    cols = [
        "siret", "siren", "denomination", "enseigne", "sigle",
        "naf_code", "categorie_chruth", "domaine_chruth", "sous_categorie",
        "adresse_complete", "code_postal", "libelle_commune",
        "code_departement", "region_nom", "region",
        "tranche_effectif_salarie", "effectif_code", "effectif_label", "effectif_nombre",
        "caractere_employeur", "categorie_entreprise", "nombre_etablissements",
        "date_creation", "age_annees",
        "latitude", "longitude",
        "est_siege", "nature_juridique",
        "liste_finess", "liste_uai",
        "_naf_recherche", "_timestamp",
    ]
    existing = [c for c in cols if c in df.columns]
    df = df[existing]

    out_path = OUTPUT_DIR / "prospects_nettoyes.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"\nExport : {out_path}")
    print(f"  Lignes finales : {len(df)}")
    print(f"  Categories :")
    for cat, n in df["categorie_chruth"].value_counts().items():
        print(f"    {cat}: {n}")
    print(f"\nProchaine : python enrich_finess.py")


if __name__ == "__main__":
    main()
