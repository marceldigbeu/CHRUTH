import pandas as pd
from pathlib import Path

from config import CODES_NAF

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

FINESS_PATH = DATA_DIR / "finess_extraction.csv"


def load_prospects() -> pd.DataFrame:
    path = OUTPUT_DIR / "prospects_nettoyes.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} introuvable. Exécute d'abord clean_classify.py"
        )
    df = pd.read_csv(path, dtype=str)
    print(f"Prospects chargés : {len(df)} lignes")
    return df


def load_finess() -> pd.DataFrame:
    if not FINESS_PATH.exists():
        print(
            "[AVERTISSEMENT] Fichier FINESS introuvable. "
            "Télécharge-le depuis :\n"
            "  https://www.data.gouv.fr/fr/datasets/finess-extraction-du-fichier-des-etablissements/\n"
            "  Place le fichier CSV dans le dossier data/ sous le nom 'finess_extraction.csv'"
        )
        return pd.DataFrame()
    df = pd.read_csv(FINESS_PATH, sep=";", dtype=str, low_memory=False)
    print(f"FINESS chargé : {len(df)} établissements")
    return df


def merge_finess(prospects: pd.DataFrame, finess: pd.DataFrame) -> pd.DataFrame:
    if finess.empty:
        print("Pas de jointure FINESS possible")
        return prospects

    normalized_cols = {c.strip().lower(): c for c in finess.columns}
    siret_col = normalized_cols.get("siret")
    if siret_col is None:
        print(f"Colonne SIRET introuvable dans FINESS : {list(finess.columns)[:10]}")
        return prospects

    # Le nom de colonne telephone varie selon l'extraction FINESS (avec/sans accent)
    tel_col = next((c for key, c in normalized_cols.items()
                    if key in ("telephone", "téléphone", "tel")), None)
    if tel_col is None:
        print(f"Colonne telephone introuvable dans FINESS : {list(finess.columns)[:10]}")
        return prospects

    finess = finess[finess[siret_col].notna()].copy()
    finess = finess.drop_duplicates(subset=siret_col, keep="first")

    finess_subset = finess[[siret_col, tel_col]].copy()
    finess_subset = finess_subset.rename(columns={siret_col: "siret", tel_col: "telephone_finess"})

    merged = prospects.merge(finess_subset, on="siret", how="left")
    n_enriched = merged["telephone_finess"].notna().sum()
    print(f"Enrichis avec téléphone FINESS : {n_enriched}")

    return merged


def main():
    print("=== ENRICHISSEMENT FINESS ===")
    prospects = load_prospects()
    finess = load_finess()
    enriched = merge_finess(prospects, finess)

    out_path = OUTPUT_DIR / "prospects_enrichis.csv"
    enriched.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\nExport : {out_path}")
    print(f"Prochaine étape : python scoring_export.py")


if __name__ == "__main__":
    main()
