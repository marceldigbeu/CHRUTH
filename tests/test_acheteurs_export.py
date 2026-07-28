import pandas as pd
from openpyxl import load_workbook

import acheteurs_semaine as asem


def test_exporter_ecrit_xlsx_et_csv(tmp_path):
    df = pd.DataFrame([{c: ("" if c != "nb_ao_semaine" else 1) for c in asem.COLONNES}])
    df = df.astype({col: object for col in df.columns})  # Force object dtype for all columns
    df.loc[0, "acheteur"] = "Mairie X"; df.loc[0, "type"] = "public"
    df.loc[0, "aos"] = [{"objet": "Nettoyage", "date_publication": "2026-07-24", "priorite": "CHAUD", "url": "u"}]
    xlsx, csv = tmp_path / "a.xlsx", tmp_path / "a.csv"
    asem.exporter(df, xlsx, csv)
    assert xlsx.exists() and csv.exists()
    wb = load_workbook(xlsx)
    entetes = [c.value for c in wb.active[1]]
    assert "acheteur" in entetes and "type" in entetes
    texte = csv.read_text(encoding="utf-8")
    assert "Mairie X" in texte and "Nettoyage" in texte  # aos aplati
