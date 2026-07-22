import pandas as pd

from ao_export_excel import build_dce_a_recuperer


def test_build_dce_a_recuperer():
    df = pd.DataFrame([
        {"id_ao": "A", "objet": "nettoyage", "acheteur": "CH", "score_chruth": 80,
         "budget_estime_eur": "", "email": "", "telephone": "", "url_dce": "http://x/dce",
         "url_profil_acheteur": "http://x", "dce_statut": "LIEN_SEUL"},
        {"id_ao": "B", "objet": "complet", "acheteur": "CH2", "score_chruth": 90,
         "budget_estime_eur": "150000", "email": "a@b.fr", "telephone": "0102030405",
         "url_dce": "", "url_profil_acheteur": "", "dce_statut": ""},
    ])
    out = build_dce_a_recuperer(df)
    assert list(out["id_ao"]) == ["A"]                 # B est complet -> exclu
    assert out.iloc[0]["fichier_attendu"] == "A.pdf"
    assert "url_dce" in out.columns
