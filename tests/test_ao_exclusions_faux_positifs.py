"""Verrou anti-régression : les faux positifs signalés (objet hors-cible avec un
mot 'nettoyage' incident dans le détail) doivent être écartés par les exclusions
DURES, sans écarter de vrai AO nettoyage.
"""
from ao_config import AO_EXCLUSION_DURES
from ao_extract_fields import keyword_in_text, normalize_text

HORS_CIBLE = [
    "MARCHE D'EXPLOITATION DES INSTALLATIONS INDIVIDUELLES DE CHAUFFAGE ET VMC GAZ",
    "Entretien et Fraisage des Reseaux EU-EV-EP / Pompes de relevages",
    "Prestations de boitage d'imprimes avec et sans adressage pour la Region Ile-de-France",
    "Restauration collective AG2R LA MONDIALE",
    "Gestion de l'etablissement d'accueil petite enfance Marcel Bontemps",
    "Accompagnement a la sensibilisation des publics pour la prevention et la gestion des dechets",
]

# Vrais AO nettoyage — le dernier est un piege (creche + gestion des dechets).
LEGITIMES = [
    "Nettoyage des locaux de l'ecole primaire",
    "Prestations de proprete et entretien des locaux administratifs",
    "Nettoyage des batiments communaux et vitrerie",
    "Nettoyage de la creche municipale et gestion des dechets menagers",
]


def _exclu(objet: str) -> bool:
    n = normalize_text(objet)
    return any(keyword_in_text(w, n) for w in AO_EXCLUSION_DURES)


def test_faux_positifs_ao_exclus():
    for objet in HORS_CIBLE:
        assert _exclu(objet), f"devrait etre exclu : {objet}"


def test_vrais_ao_nettoyage_non_exclus():
    for objet in LEGITIMES:
        assert not _exclu(objet), f"ne devrait PAS etre exclu : {objet}"
