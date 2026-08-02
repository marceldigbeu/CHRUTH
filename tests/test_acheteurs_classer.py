from acheteurs_semaine import classer


def test_categorie_droit_public_niveau_7():
    assert classer("7220") == ("public", False)   # commune
    assert classer("7100", "") == ("public", False)


def test_societes_de_droit_prive():
    assert classer("5710") == ("prive", False)     # SA (ESH)
    assert classer("5385") == ("prive", False)     # SEM


def test_sans_categorie_repli_sur_le_nom():
    assert classer("", "Mairie de Créteil") == ("public", True)
    assert classer("", "Département de Seine-Saint-Denis") == ("public", True)
    assert classer("", "Immobilière 3F") == ("prive", True)
