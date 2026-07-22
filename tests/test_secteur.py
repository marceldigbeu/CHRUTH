from ao_extract_fields import detect_secteur


def test_ecole():
    assert detect_secteur("Groupe scolaire Jules Ferry", "Nettoyage") == "Ecole"


def test_mairie():
    assert detect_secteur("Ville de Montreuil", "Entretien des locaux") == "Mairie"


def test_gymnase():
    assert detect_secteur("Commune", "Nettoyage du gymnase municipal") == "Gymnase"


def test_mediatheque():
    assert detect_secteur("Mediatheque intercommunale", "Proprete") == "Mediatheque"


def test_autre_par_defaut():
    assert detect_secteur("Societe privee XYZ", "Nettoyage bureaux") == "Autre"
