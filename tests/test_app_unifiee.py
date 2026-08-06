"""Point d'entree unique : une seule app, deux pages.

Deux applications Streamlit separees se disputaient le port 8501 : la seconde ne
pouvait pas demarrer pendant la premiere, et il fallait savoir laquelle lancer.
"""
import ast
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

RACINE = Path(__file__).resolve().parent.parent
ENTREE = str(RACINE / "CHRUTH_APP.py")

EMAIL_TEST = "bob@chruth.fr"


def _pages_de_la_navigation() -> list[tuple[str, str]]:
    """Les pages (fichier, titre) declarees dans CHRUTH_APP.py.

    La navigation est une boucle sur la liste PAGES_DEF : lire des appels
    st.Page ecrits a la main laisserait une page silencieusement hors controle.
    """
    module = ast.parse((RACINE / "CHRUTH_APP.py").read_text(encoding="utf-8"))
    for noeud in module.body:
        if isinstance(noeud, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "PAGES_DEF"
                for t in noeud.targets):
            return ast.literal_eval(noeud.value)
    raise AssertionError("PAGES_DEF introuvable dans CHRUTH_APP.py")


@pytest.fixture
def etat_local(tmp_path, monkeypatch):
    chemin = tmp_path / "veille.json"
    chemin.write_text(json.dumps(
        {"version": 1, "maj_le": "", "guide_messages": "", "aos": {}}), encoding="utf-8")
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "local")
    monkeypatch.setenv("CHRUTH_VEILLE_ETAT", str(chemin))
    monkeypatch.delenv("CHRUTH_VEILLE_GUIDE", raising=False)
    return chemin


def test_l_entree_unique_demarre_sur_l_accueil(etat_local, tmp_path, monkeypatch):
    """L'app ouvrait sur la veille, qui est vide entre deux passages du veilleur.
    L'accueil lit la base et a toujours de quoi s'afficher."""
    monkeypatch.setenv("CHRUTH_AO_DB", str(tmp_path / "ao.sqlite"))
    at = AppTest.from_file(ENTREE, default_timeout=90)
    at.session_state["comptes.utilisateur"] = EMAIL_TEST
    at.run()
    assert not at.exception
    assert "CHRUTH — veille marchés publics" in [t.value for t in at.title]


def test_la_veille_reste_atteignable(etat_local, tmp_path, monkeypatch):
    monkeypatch.setenv("CHRUTH_AO_DB", str(tmp_path / "ao.sqlite"))
    at = AppTest.from_file(ENTREE, default_timeout=90)
    at.session_state["comptes.utilisateur"] = EMAIL_TEST
    at.run()
    at.switch_page("app_veille.py").run()
    assert not at.exception
    assert "Veille appels d'offres" in [t.value for t in at.title]


def test_la_page_messages_est_atteignable(etat_local, tmp_path, monkeypatch):
    monkeypatch.setenv("CHRUTH_AO_DB", str(tmp_path / "ao.sqlite"))
    at = AppTest.from_file(ENTREE, default_timeout=90)
    at.run()
    at.switch_page("app_messages.py").run()
    assert not at.exception


def test_toutes_les_pages_sont_declarees():
    """Une page oubliee ici devient une page inaccessible, sans erreur visible."""
    source = (RACINE / "CHRUTH_APP.py").read_text(encoding="utf-8")
    for page in ("pages_accueil.py", "app_veille.py", "pages_collecte.py", "pages_donnees.py", "pages_acheteurs.py", "pages_carte.py", "app_messages.py",
                 "pages_pilotage.py", "pages_reglages.py", "pages_developpeur.py"):
        assert page in source, f"page non declaree dans la navigation : {page}"


def test_les_pages_pilotage_et_reglages_sont_atteignables(etat_local, tmp_path, monkeypatch):
    monkeypatch.setenv("CHRUTH_AO_DB", str(tmp_path / "ao.sqlite"))
    at = AppTest.from_file(ENTREE, default_timeout=90)
    at.run()
    at.switch_page("pages_pilotage.py").run()
    assert not at.exception
    at.switch_page("pages_reglages.py").run()
    assert not at.exception


def test_chaque_page_reste_lancable_seule(etat_local):
    """La garde sur set_page_config ne doit pas casser l'usage direct."""
    at = AppTest.from_file(str(RACINE / "app_veille.py"), default_timeout=90)
    at.run()
    assert not at.exception


def test_un_seul_lanceur_pour_l_utilisateur():
    lanceurs = sorted(p.name for p in RACINE.glob("LANCER_APP_*.bat"))
    assert lanceurs == ["LANCER_APP_CHRUTH.bat"], f"lanceurs en trop : {lanceurs}"


def test_l_accueil_est_la_page_par_defaut():
    """Ouvrir sur la veille exposait un premier ecran vide entre deux passages :
    l'accueil, lui, s'appuie sur la base et a toujours quelque chose a montrer."""
    pages = _pages_de_la_navigation()
    assert pages[0] == ("pages_accueil.py", "Accueil")
    source = (RACINE / "CHRUTH_APP.py").read_text(encoding="utf-8")
    assert "default=(titre == pref)" in source
