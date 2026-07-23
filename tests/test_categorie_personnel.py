"""Marches de personnel : mots-cles composes et categorie dediee."""
from ao_extract_fields import classify_categorie, find_keywords_rh


def test_la_mise_a_disposition_de_personnel_est_reconnue():
    assert find_keywords_rh("Mise a disposition de personnel d'entretien") != []


def test_un_mot_isole_ne_declenche_rien():
    """« accueil » seul figure dans la moitie des marches de services."""
    assert find_keywords_rh("Marche d'accueil du public en mairie") == []
    assert find_keywords_rh("Prestations de logistique evenementielle") == []


def test_le_marqueur_de_personnel_declenche():
    assert find_keywords_rh("Prestations d'agents d'accueil et de surveillance") != []


def test_la_categorie_personnel_prime_sur_les_autres():
    """« mise a disposition de personnel pour les locaux » contient « locaux » :
    sans priorite, il serait classe Batiments et se confondrait avec la proprete."""
    assert classify_categorie("Mise a disposition de personnel pour les locaux") == "Personnel"


def test_les_categories_existantes_ne_bougent_pas():
    assert classify_categorie("Nettoyage des vitres") == "Vitres"
    assert classify_categorie("Entretien des bureaux") == "Bureaux"
    assert classify_categorie("Nettoyage des batiments communaux") == "Batiments"
