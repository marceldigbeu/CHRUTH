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


def test_requirements_couvre_toute_l_application():
    manquants = _imports_tiers(["CHRUTH_APP", "app_veille", "app_messages"]) - _declares("requirements.txt")
    assert manquants == set(), f"absents de requirements.txt : {sorted(manquants)}"


def test_streamlit_est_declare():
    """Sans lui, Community Cloud ne peut meme pas demarrer l'app."""
    assert "streamlit" in _declares("requirements.txt")
