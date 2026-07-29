"""La jauge de score : elle doit filtrer et classer, pas seulement s'afficher."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

RACINE = Path(__file__).resolve().parent.parent


def _etat(tmp_path: Path) -> Path:
    """Trois AO aux scores voisins : l'ancien bareme les aurait mis a egalite."""
    aos = {
        "MX-1": {"objet": "Nettoyage des ecoles", "acheteur": "Ville A", "ville": "Paris",
                 "departement": "75", "date_publication": "2026-07-20",
                 "date_limite": "2026-09-01", "score": 71.4, "priorite": "CHAUD",
                 "tri": {"verdict": "PERTINENT", "etage": "listes", "motif": "nettoyage"},
                 "traitement": "nouveau", "lu": False, "vu_le": "2026-07-20T08:00:00+00:00"},
        "MX-2": {"objet": "Nettoyage des gymnases", "acheteur": "Ville B", "ville": "Lyon",
                 "departement": "93", "date_publication": "2026-07-25",
                 "date_limite": "2026-09-02", "score": 65.7, "priorite": "CHAUD",
                 "tri": {"verdict": "PERTINENT", "etage": "listes", "motif": "nettoyage"},
                 "traitement": "nouveau", "lu": False, "vu_le": "2026-07-25T08:00:00+00:00"},
        "MX-3": {"objet": "Nettoyage des bureaux", "acheteur": "Ville C", "ville": "Lille",
                 "departement": "92", "date_publication": "2026-07-27",
                 "date_limite": "2026-09-03", "score": 42.1, "priorite": "TIEDE",
                 "tri": {"verdict": "PERTINENT", "etage": "listes", "motif": "nettoyage"},
                 "traitement": "nouveau", "lu": False, "vu_le": "2026-07-27T08:00:00+00:00"},
    }
    chemin = tmp_path / "veille.json"
    chemin.write_text(json.dumps({"version": 1, "maj_le": "2026-07-27T10:00:00+00:00",
                                  "aos": aos, "guide_messages": "",
                                  "corrections_memoire": [],
                                  "reglages": {"notifications": False}},
                                 ensure_ascii=False), encoding="utf-8")
    return chemin


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("CHRUTH_VEILLE_ETAT", str(_etat(tmp_path)))
    return lambda: AppTest.from_file(str(RACINE / "app_veille.py"), default_timeout=60).run()


def _objets_affiches(at) -> list[str]:
    """Intitules des AO du fil, dans l'ordre d'affichage."""
    return [m.value for m in at.markdown
            if m.value.startswith(("**", ":blue[**Nouveau**] · **"))]


def test_la_jauge_existe_avec_un_pas_decimal(app):
    at = app()
    jauge = next(s for s in at.slider if "Score minimum" in s.label)
    assert jauge.step == 0.5, "un pas de 5 ramenerait le probleme des paliers"
    assert jauge.value == 0.0, "par defaut la jauge ne cache rien"


def test_la_jauge_ecarte_les_ao_sous_le_seuil(app):
    at = app()
    assert len(_objets_affiches(at)) == 3

    at = app()
    next(s for s in at.slider if "Score minimum" in s.label).set_value(50.0).run()
    affiches = _objets_affiches(at)

    assert len(affiches) == 2
    assert not any("bureaux" in o for o in affiches), "42,1 est sous le seuil de 50"


def test_la_jauge_departage_deux_scores_voisins(app):
    """Le point de la decimale : un seuil entre 65,7 et 71,4 doit couper entre eux."""
    at = app()
    next(s for s in at.slider if "Score minimum" in s.label).set_value(70.0).run()
    affiches = _objets_affiches(at)

    assert len(affiches) == 1
    assert "ecoles" in affiches[0]


def test_le_classement_par_score_reordonne_le_fil(app):
    at = app()
    par_fraicheur = _objets_affiches(at)
    assert "bureaux" in par_fraicheur[0], "par defaut, le plus recemment publie d'abord"

    at = app()
    next(s for s in at.selectbox if "Classer par" in s.label).set_value("Score décroissant").run()
    par_score = _objets_affiches(at)

    assert "ecoles" in par_score[0], "71,4 en tete"
    assert "bureaux" in par_score[-1], "42,1 en queue"


def test_le_score_est_affiche_a_la_decimale(app):
    at = app()
    assert any("71.4" in m.value for m in at.markdown), \
        "afficher 71 au lieu de 71,4 reperd la precision qu'on vient de gagner"


def test_le_resume_des_filtres_mentionne_la_jauge(app):
    at = app()
    next(s for s in at.slider if "Score minimum" in s.label).set_value(50.0).run()
    assert any("score ≥ 50.0" in c.value for c in at.caption), \
        "un filtre actif invisible fait croire a une base vide"
