from datetime import date

import pandas as pd

from ao_semaine import add_semaine_iso, build_top20_ouverts


def _df():
    return pd.DataFrame(
        [
            {"id_ao": "a", "date_limite": "2026-07-01", "score_chruth": 80, "objet": "X", "priorite": "CHAUD"},
            {"id_ao": "b", "date_limite": "2026-07-15", "score_chruth": 95, "objet": "Y", "priorite": "CHAUD"},
            {"id_ao": "c", "date_limite": "2026-06-01", "score_chruth": 99, "objet": "Z", "priorite": "CHAUD"},  # expire
            {"id_ao": "d", "date_limite": "", "score_chruth": 50, "objet": "W", "priorite": "TIEDE"},  # limite inconnue -> gardee
        ]
    )


def test_add_semaine_iso_column():
    df = pd.DataFrame([
        {"id_ao": "b", "date_publication": "2026-06-10"},
        {"id_ao": "d", "date_publication": ""},
    ])
    out = add_semaine_iso(df)
    assert "semaine_iso" in out.columns
    assert out.loc[out["id_ao"] == "b", "semaine_iso"].iloc[0] == "2026-W24"
    assert out.loc[out["id_ao"] == "d", "semaine_iso"].iloc[0] == ""


def test_top20_exclut_expires_trie_par_score():
    top = build_top20_ouverts(_df(), today=date(2026, 6, 15))
    # c (limite 2026-06-01 < today) exclu ; ordre par score : b(95) > a(80) > d(50, limite inconnue gardee)
    assert list(top["id_ao"]) == ["b", "a", "d"]
    assert "rang" in top.columns
    assert list(top["rang"]) == [1, 2, 3]


def test_top20_caps_at_20():
    rows = [{"id_ao": str(i), "date_limite": "2026-07-01", "score_chruth": i, "objet": "o", "priorite": "CHAUD"} for i in range(30)]
    top = build_top20_ouverts(pd.DataFrame(rows), today=date(2026, 6, 15))
    assert len(top) == 20
    assert top["rang"].max() == 20
