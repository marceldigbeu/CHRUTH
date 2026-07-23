"""Les dependances du veilleur doivent etre declarees.

Le workflow GitHub Actions installe un fichier d'exigences puis lance la veille :
une dependance oubliee ne se voit qu'au premier run reel, en production.
bs4 manquait dans requirements.txt alors que le scraper l'importe.
"""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# Modules du projet composant la chaine de veille, et le paquet pip qui les fournit.
CHAINE = ["ao_maximilien_veille", "ao_maximilien_scrape", "ao_pertinence", "veille_etat",
          "ao_alertes", "ao_messages", "llm_client", "ao_extract_fields", "ao_scoring",
          "ao_db", "ao_config"]
PAQUET_PAR_MODULE = {"requests": "requests", "bs4": "beautifulsoup4", "pandas": "pandas"}


def _imports_tiers() -> set[str]:
    trouves: set[str] = set()
    for nom in CHAINE:
        texte = (BASE / f"{nom}.py").read_text(encoding="utf-8")
        for m in re.finditer(r"^\s*(?:from|import)\s+([a-zA-Z_][\w]*)", texte, re.MULTILINE):
            racine = m.group(1)
            if racine in PAQUET_PAR_MODULE:
                trouves.add(PAQUET_PAR_MODULE[racine])
    return trouves


def _declares(fichier: str) -> set[str]:
    lignes = (BASE / fichier).read_text(encoding="utf-8").splitlines()
    return {re.split(r"[<>=!\[]", l.strip())[0].lower()
            for l in lignes if l.strip() and not l.strip().startswith("#")}


def test_requirements_veille_couvre_toute_la_chaine():
    manquants = _imports_tiers() - _declares("requirements-veille.txt")
    assert manquants == set(), f"absents de requirements-veille.txt : {sorted(manquants)}"


def test_requirements_principal_declare_aussi_bs4():
    """Le scraper est aussi lance depuis l'instance locale, hors CI."""
    assert "beautifulsoup4" in _declares("requirements.txt")


def test_le_workflow_installe_les_dependances_de_la_veille():
    wf = (BASE / ".github/workflows/veille-maximilien.yml").read_text(encoding="utf-8")
    assert "requirements-veille.txt" in wf
