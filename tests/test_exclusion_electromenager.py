"""La fourniture d'appareils menagers n'est pas du nettoyage.

Cas reel du 2026-07-23, en partance vers la boite mail : BOAMP 26-72948
« Fourniture d'appareils menagers et d'equipements », retenu TIEDE parce que
« menagers » commence par le mot-cle « menage ».
"""
from ao_pertinence import PERTINENT, REJETE, trier_listes


def test_rejette_la_fourniture_d_appareils_menagers():
    v = trier_listes("26MF026 - Fourniture d'appareils menagers et d'equipements")
    assert v.verdict == REJETE


def test_rejette_l_electromenager():
    assert trier_listes("Acquisition d'electromenager pour les residences").verdict == REJETE


def test_l_entretien_menager_de_locaux_reste_pertinent():
    """Anti-regression : c'est le coeur de metier, il ne doit pas tomber avec."""
    v = trier_listes("Entretien menager des locaux des sites megalithiques")
    assert v.verdict == PERTINENT


def test_les_prestations_d_entretien_menager_restent_pertinentes():
    v = trier_listes("Prestations de nettoyage et d'entretien menager des batiments")
    assert v.verdict == PERTINENT
