from ao_extract_fields import extract_duree_mois, annualize_budget


def test_duree_en_ans():
    assert extract_duree_mois("marche d'une duree de 4 ans") == 48


def test_duree_en_mois():
    assert extract_duree_mois("contrat de 36 mois ferme") == 36


def test_duree_absente():
    assert extract_duree_mois("nettoyage des locaux") is None


def test_annualise_avec_duree():
    montant, annualise = annualize_budget(300_000, 48)
    assert montant == 75_000
    assert annualise is True


def test_annualise_duree_sous_annuelle():
    # Marche de 6 mois a 120k -> taux annuel 240k, marque annualise.
    montant, annualise = annualize_budget(120_000, 6)
    assert montant == 240_000
    assert annualise is True


def test_annualise_sans_duree():
    montant, annualise = annualize_budget(80_000, None)
    assert montant == 80_000
    assert annualise is False


def test_annualise_budget_none():
    montant, annualise = annualize_budget(None, 24)
    assert montant is None
    assert annualise is False
