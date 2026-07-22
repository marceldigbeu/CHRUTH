import pandas as pd
import prospects_carte as pc


def test_charger_prospects_trouve_xlsm(tmp_path, monkeypatch):
    f = tmp_path / "Base_Prospects_CHRUTH.xlsm"
    pd.DataFrame([{"siret": "1", "denomination": "A", "priorite": "CHAUDE",
                   "latitude": 48.8, "longitude": 2.3}]).to_excel(f, sheet_name="Prospects", index=False)
    monkeypatch.setattr(pc, "_CANDIDATS_BASE", [tmp_path])
    df = pc.charger_prospects()
    assert len(df) == 1
