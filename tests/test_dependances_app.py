"""Tout ce que l'app importe doit etre declare dans requirements.txt.

Streamlit Community Cloud installe requirements.txt puis lance l'app : une
dependance oubliee ne se voit qu'au deploiement, par un ecran d'erreur en ligne.
C'est exactement ainsi que bs4 avait manque au workflow de veille.
"""
import ast
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

# Nom du module importe -> nom du paquet a installer, quand ils different.
PAQUET = {"bs4": "beautifulsoup4", "dotenv": "python-dotenv", "nacl": "pynacl",
          "fitz": "pymupdf", "PIL": "pillow", "yaml": "pyyaml"}


def _imports_tiers(entrees: list[str]) -> set[str]:
    """Fermeture transitive des imports tiers, en suivant les modules du projet."""
    locaux = {p.stem for p in RACINE.glob("*.py")}
    vus: set[str] = set()
    a_voir = list(entrees)
    tiers: set[str] = set()

    while a_voir:
        module = a_voir.pop()
        if module in vus:
            continue
        vus.add(module)
        fichier = RACINE / f"{module}.py"
        if not fichier.exists():
            continue
        for noeud in ast.walk(ast.parse(fichier.read_text(encoding="utf-8"))):
            racines = []
            if isinstance(noeud, ast.Import):
                racines = [a.name.split(".")[0] for a in noeud.names]
            elif isinstance(noeud, ast.ImportFrom) and noeud.module and noeud.level == 0:
                racines = [noeud.module.split(".")[0]]
            for racine in racines:
                if racine in locaux:
                    a_voir.append(racine)
                elif racine not in sys.stdlib_module_names:
                    tiers.add(racine)
    return {PAQUET.get(m, m).lower() for m in tiers}


def _declares(fichier: str) -> set[str]:
    lignes = (RACINE / fichier).read_text(encoding="utf-8").splitlines()
    return {re.split(r"[<>=!\[]", l.strip())[0].lower()
            for l in lignes if l.strip() and not l.strip().startswith("#")}


def _pages_declarees() -> list[str]:
    """Les pages listees dans CHRUTH_APP.py, lues a la source.

    Ecrire la liste en dur ici la laisserait vieillir : les pages Pilotage et
    Reglages sont restees hors de cette garde le temps d'une refonte, alors que
    la dependance manquante est la panne de deploiement la plus courante.
    """
    source = (RACINE / "CHRUTH_APP.py").read_text(encoding="utf-8")
    return sorted({m.removesuffix(".py") for m in re.findall(r'st\.Page\("([^"]+\.py)"', source)})


def test_requirements_couvre_toute_l_application():
    modules = ["CHRUTH_APP"] + _pages_declarees()
    manquants = _imports_tiers(modules) - _declares("requirements.txt")
    assert manquants == set(), f"absents de requirements.txt : {sorted(manquants)}"


def test_la_garde_couvre_bien_chaque_page_de_la_navigation():
    """Sans ceci, ajouter une page la sortirait silencieusement du controle."""
    assert _pages_declarees() == [
        "app_messages", "app_veille", "pages_accueil", "pages_acheteurs", "pages_carte",
        "pages_collecte", "pages_developpeur", "pages_donnees", "pages_pilotage",
        "pages_reglages",
    ]


def test_streamlit_est_declare():
    """Sans lui, Community Cloud ne peut meme pas demarrer l'app."""
    assert "streamlit" in _declares("requirements.txt")
