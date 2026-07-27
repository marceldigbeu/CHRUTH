"""Mode Jour/Nuit partage par toute la navigation Streamlit."""
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import theme_chruth

RACINE = Path(__file__).resolve().parent.parent
ENTREE = str(RACINE / "CHRUTH_APP.py")


@pytest.fixture
def etat_local(tmp_path, monkeypatch):
    chemin = tmp_path / "veille.json"
    chemin.write_text(json.dumps(
        {"version": 1, "maj_le": "", "guide_messages": "", "aos": {}}), encoding="utf-8")
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "local")
    monkeypatch.setenv("CHRUTH_VEILLE_ETAT", str(chemin))
    return chemin


def test_les_deux_palettes_ont_des_couleurs_distinctes():
    jour = theme_chruth.css_theme(False)
    nuit = theme_chruth.css_theme(True)
    assert theme_chruth.PALETTES["jour"]["fond"] in jour
    assert theme_chruth.PALETTES["nuit"]["fond"] in nuit
    assert jour != nuit


def test_le_selecteur_active_le_mode_nuit_et_survit_a_la_navigation(
        etat_local, tmp_path, monkeypatch):
    monkeypatch.setenv("CHRUTH_AO_DB", str(tmp_path / "ao.sqlite"))
    at = AppTest.from_file(ENTREE, default_timeout=90)
    at.run()

    selecteur = next(t for t in at.toggle if t.label == "Mode nuit")
    selecteur.set_value(True).run()
    assert at.session_state[theme_chruth.CLE_MODE_NUIT] is True
    assert not at.exception

    at.switch_page("pages_reglages.py").run()
    assert at.session_state[theme_chruth.CLE_MODE_NUIT] is True
    assert not at.exception
