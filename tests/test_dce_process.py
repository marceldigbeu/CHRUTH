import pandas as pd

from ao_dce_process import needs_dce, apply_extraction


def test_needs_dce():
    assert needs_dce({"budget_estime_eur": "", "email": "", "telephone": ""}) is True
    assert needs_dce({"budget_estime_eur": "150000", "email": "a@b.fr", "telephone": "0102030405"}) is False
    assert needs_dce({"budget_estime_eur": "", "email": "a@b.fr", "telephone": "0102030405"}) is True


def test_apply_extraction_fills_only_empty():
    row = {"budget_estime_eur": "", "email": "garde@moi.fr", "telephone": "", "preuve_source": ""}
    extracted = {"dce_budget": "200000", "dce_email": "dce@x.fr", "dce_tel": "0123456789",
                 "dce_resume": "r", "dce_contact": "", "dce_texte_extrait": "t"}
    out = apply_extraction(row, extracted, statut="DEPOT_MANUEL_OK", fichier="26-1.pdf")
    assert out["budget_estime_eur"] == "200000"     # etait vide -> rempli
    assert out["email"] == "garde@moi.fr"           # existait -> NON ecrase
    assert out["telephone"] == "0123456789"         # etait vide -> rempli
    assert out["dce_budget"] == "200000"            # colonne dediee
    assert out["dce_statut"] == "DEPOT_MANUEL_OK"
    assert out["dce_fichier"] == "26-1.pdf"
    assert "DCE" in out["preuve_source"]
