from ao_extract_fields import classify_categorie


def test_vitres_prioritaire():
    assert classify_categorie("Nettoyage des vitres et des bureaux") == "Vitres"


def test_bureaux():
    assert classify_categorie("Entretien des bureaux administratifs") == "Bureaux"


def test_batiments():
    assert classify_categorie("Nettoyage des locaux et batiments communaux") == "Batiments"


def test_mixte_si_aucun_marqueur():
    assert classify_categorie("Prestation de proprete generale") == "Mixte/Autre"


def test_insensible_accents_casse():
    assert classify_categorie("NETTOYAGE DE VITRERIE") == "Vitres"
