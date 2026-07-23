from datetime import datetime

import ao_alertes


def _ao(id_ao, priorite="CHAUD", **extra):
    row = {"id_ao": id_ao, "objet": f"Nettoyage {id_ao}", "acheteur": "Ville de Test",
           "secteur": "Mairie", "categorie": "Batiments", "ville": "Paris",
           "date_publication": "2026-06-14", "date_limite": "2099-01-01",
           "budget_annuel_eur": "40000", "budget_estime_eur": "40000",
           "url_dce": "", "url_avis": "", "priorite": priorite, "score_chruth": "70"}
    row.update(extra)
    return row


def test_construire_email_inclut_les_brouillons():
    records = [_ao("A", "CHAUD"), _ao("B", "TIEDE")]
    brouillons = {"A": {"email": "MAIL-A", "script": "SCRIPT-A"},
                  "B": {"email": "MAIL-B", "script": "SCRIPT-B"}}
    sujet, html, texte = ao_alertes.construire_email(
        records, datetime(2026, 6, 14, 9, 0), brouillons=brouillons)
    assert "MAIL-A" in html and "SCRIPT-A" in html
    assert "MAIL-B" in texte and "SCRIPT-B" in texte
    assert "Nettoyage A" in html          # tableau conserve
    assert "matin" in sujet               # sujet inchange


def test_brouillons_pour_repli_si_cache_absent(tmp_path):
    b = ao_alertes._brouillons_pour([_ao("Z")], cache_path=tmp_path / "absent.json")
    assert b["Z"]["email"].strip()        # repli deterministe non vide
    assert b["Z"]["script"].strip()
