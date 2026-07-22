from ao_dce import extract_fields_from_text


def test_extract_budget_email_tel():
    text = ("Objet : nettoyage des locaux. Le marche est estime a 250 000 EUR HT. "
            "Contact : Mme Dupont, courriel j.dupont@ch-paris.fr, tel 01 23 45 67 89.")
    r = extract_fields_from_text(text)
    assert r["dce_email"] == "j.dupont@ch-paris.fr"
    assert r["dce_tel"].replace(" ", "") == "0123456789"
    assert r["dce_budget"] == "250000"
    assert "nettoyage" in r["dce_resume"].lower()
    assert r["dce_texte_extrait"]


def test_ignores_generic_email_and_small_numbers():
    text = "Page 2 sur 12. Ecrire a no-reply@plateforme.fr. Montant : 300 euros de penalite."
    r = extract_fields_from_text(text)
    assert r["dce_email"] == ""        # no-reply ignore
    assert r["dce_budget"] == ""       # 300 < seuil 1000


def test_empty_text():
    r = extract_fields_from_text("")
    assert r["dce_budget"] == "" and r["dce_email"] == "" and r["dce_tel"] == ""
