"""La documentation livree doit decrire l'application livree.

Le guide annoncait « huit pages » alors que la navigation en comptait dix, et le
PDF decrivait une version anterieure du HTML. Ces deux derives sont silencieuses :
rien ne casse, le client lit simplement des instructions fausses. Ces tests les
rendent bruyantes.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
GUIDE_HTML = RACINE / "GUIDE_UTILISATION_CHRUTH.html"
GUIDE_PDF = RACINE / "GUIDE_UTILISATION_CHRUTH.pdf"

NOMBRES = {8: "huit", 9: "neuf", 10: "dix", 11: "onze", 12: "douze"}


def _pages_de_la_navigation() -> list[str]:
    source = (RACINE / "CHRUTH_APP.py").read_text(encoding="utf-8")
    return re.findall(r'st\.Page\("[^"]+",\s*title="([^"]+)"', source)


def _texte_pdf() -> str:
    fitz = pytest.importorskip("fitz", reason="PyMuPDF requis pour lire le PDF")
    with fitz.open(GUIDE_PDF) as doc:
        return "\n".join(page.get_text() for page in doc)


def _sans_accents(texte: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", texte)
                   if unicodedata.category(c) != "Mn")


def test_le_guide_annonce_le_bon_nombre_de_pages():
    """« huit pages » ecrit en toutes lettres alors qu'il y en a dix : le lecteur
    cherche une page qui existe mais qu'on ne lui a pas nommee."""
    attendu = NOMBRES.get(len(_pages_de_la_navigation()))
    assert attendu, "ajouter le nombre au dictionnaire NOMBRES"
    texte = _sans_accents(GUIDE_HTML.read_text(encoding="utf-8")).lower()
    assert f"{attendu} pages" in texte, \
        f"le guide doit annoncer « {attendu} pages »"


def test_chaque_page_de_la_navigation_est_nommee_dans_le_guide():
    guide = _sans_accents(GUIDE_HTML.read_text(encoding="utf-8")).lower()
    manquantes = [t for t in _pages_de_la_navigation()
                  if _sans_accents(t).lower() not in guide]
    assert not manquantes, f"pages absentes du guide : {manquantes}"


def test_le_pdf_couvre_toutes_les_sections_du_html():
    """Le PDF est une vue du HTML : une section presente dans l'un et absente de
    l'autre signifie que le PDF n'a pas ete regenere."""
    html = GUIDE_HTML.read_text(encoding="utf-8")
    titres = [re.sub(r"<[^>]+>", "", t).strip()
              for t in re.findall(r"<h2[^>]*>.*?</h2>", html, re.S)]
    assert titres, "aucun titre de section trouve dans le HTML"

    pdf = _sans_accents(_texte_pdf()).lower()
    manquants = [t for t in titres if _sans_accents(t).lower() not in pdf]
    assert not manquants, (
        f"sections absentes du PDF : {manquants}. "
        "Regenerer avec : python outils/generer_pdf_guide.py")


def test_le_generateur_de_pdf_est_livre():
    """Sans lui, la regeneration redevient un geste manuel — donc oublie."""
    assert (RACINE / "outils" / "generer_pdf_guide.py").is_file()


@pytest.mark.parametrize("sujet", [
    "jauge", "score minimum", "tokens", "mot de passe d'application",
    "acces et connexion", "accueil",
])
def test_les_fonctions_recentes_sont_documentees(sujet):
    """Une fonction livree mais non documentee n'existe pas pour l'utilisateur."""
    guide = _sans_accents(GUIDE_HTML.read_text(encoding="utf-8")).lower()
    assert sujet in guide, f"sujet absent du guide : {sujet}"
