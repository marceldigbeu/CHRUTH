"""Signature des messages : deterministe, jamais inventee."""
from signature import apposer, bloc, coordonnees

FICHE = """# Fiche CHRUTH

## Activité
Nettoyage de locaux professionnels

## Coordonnées
- Site : https://www.exemple-chruth.fr
- Email : contact@chruth.fr
- Téléphone : 01 23 45 67 89
"""

FICHE_VIDE = """# Fiche CHRUTH

## Coordonnées
<!-- Ex: https://... -->
"""


def test_les_coordonnees_sont_extraites():
    c = coordonnees(FICHE)
    assert c["site"] == "https://www.exemple-chruth.fr"
    assert c["email"] == "contact@chruth.fr"
    assert c["telephone"] == "01 23 45 67 89"


def test_une_fiche_sans_coordonnees_ne_rend_rien():
    assert coordonnees(FICHE_VIDE) == {}
    assert bloc(FICHE_VIDE) == ""


def test_les_commentaires_d_exemple_ne_sont_pas_pris_pour_des_donnees():
    """La fiche livree est pleine de <!-- Ex: ... --> : les lire serait pire que rien."""
    assert "exemple" not in bloc(FICHE_VIDE).lower()


def test_le_bloc_contient_les_trois_coordonnees():
    b = bloc(FICHE)
    assert "https://www.exemple-chruth.fr" in b
    assert "contact@chruth.fr" in b
    assert "01 23 45 67 89" in b


def test_le_bloc_tolere_une_coordonnee_partielle():
    partielle = "## Coordonnées\n- Email : contact@chruth.fr\n"
    b = bloc(partielle)
    assert "contact@chruth.fr" in b
    assert "Site" not in b


def test_apposer_ajoute_le_bloc_a_la_fin():
    resultat = apposer("Bonjour,\n\nVoici notre proposition.", FICHE)
    assert resultat.startswith("Bonjour,")
    assert resultat.rstrip().endswith("01 23 45 67 89")


def test_apposer_ne_touche_pas_au_texte_sans_coordonnees():
    """Regle 2 de la spec : pas de coordonnees, pas de signature."""
    assert apposer("Bonjour,", FICHE_VIDE) == "Bonjour,"


def test_apposer_est_idempotent():
    """Un message deja signe ne doit pas l'etre deux fois."""
    une_fois = apposer("Bonjour,", FICHE)
    assert apposer(une_fois, FICHE) == une_fois
