"""Filtre du fil sur la date de publication."""
import json
from datetime import date, timedelta
from pathlib import Path

import veille_etat as ve
from ao_pertinence import PERTINENT, Verdict
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app_veille.py")


def _il_y_a(jours: int) -> str:
    return (date.today() - timedelta(days=jours)).isoformat()


def _ao(id_ao, objet, publie):
    ao = {"id_ao": id_ao, "objet": objet, "acheteur": "Mairie", "ville": "STAINS",
          "departement": "93", "date_limite": "2026-12-31", "procedure": "MAPA",
          "url": "https://x/1", "score": "65", "priorite": "CHAUD"}
    if publie is not None:
        ao["date_publication"] = publie
    return ao


def _preparer(tmp_path, monkeypatch, aos):
    chemin = tmp_path / "veille.json"
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "local")
    monkeypatch.setenv("CHRUTH_VEILLE_ETAT", str(chemin))
    monkeypatch.delenv("CHRUTH_VEILLE_GUIDE", raising=False)

    etat = ve.charger(chemin)
    for ao in aos:
        ve.ajouter(etat, ao, Verdict(PERTINENT, "listes", "ok"), None)
        if ao.get("date_publication") is None:
            etat["aos"][ao["id_ao"]].pop("date_publication", None)
    chemin.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")
    return chemin


def _textes(at) -> str:
    return " ".join(m.value for m in at.markdown)


def test_par_defaut_tout_est_affiche(tmp_path, monkeypatch):
    _preparer(tmp_path, monkeypatch, [
        _ao("MX-1", "Nettoyage recent", _il_y_a(2)),
        _ao("MX-2", "Nettoyage ancien", _il_y_a(90)),
    ])
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert at.selectbox(key="publie_depuis").value == "Tout"
    assert "Nettoyage recent" in _textes(at)
    assert "Nettoyage ancien" in _textes(at)


def test_le_filtre_sept_jours_ecarte_les_avis_plus_anciens(tmp_path, monkeypatch):
    _preparer(tmp_path, monkeypatch, [
        _ao("MX-1", "Nettoyage recent", _il_y_a(2)),
        _ao("MX-2", "Nettoyage ancien", _il_y_a(30)),
    ])
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.selectbox(key="publie_depuis").select("7 derniers jours").run()

    assert "Nettoyage recent" in _textes(at)
    assert "Nettoyage ancien" not in _textes(at)


def test_la_borne_du_filtre_est_inclusive(tmp_path, monkeypatch):
    _preparer(tmp_path, monkeypatch, [_ao("MX-1", "Nettoyage pile a la borne", _il_y_a(7))])
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.selectbox(key="publie_depuis").select("7 derniers jours").run()
    assert "Nettoyage pile a la borne" in _textes(at)


def test_une_date_precise_peut_etre_choisie(tmp_path, monkeypatch):
    _preparer(tmp_path, monkeypatch, [
        _ao("MX-1", "Nettoyage recent", _il_y_a(5)),
        _ao("MX-2", "Nettoyage ancien", _il_y_a(40)),
    ])
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.selectbox(key="publie_depuis").select("Depuis une date précise").run()
    at.date_input(key="publie_depuis_date").set_value(date.today() - timedelta(days=10)).run()

    assert "Nettoyage recent" in _textes(at)
    assert "Nettoyage ancien" not in _textes(at)


def test_un_ao_sans_date_reste_visible_malgre_le_filtre(tmp_path, monkeypatch):
    """Le doute profite a l'AO, comme pour le tri : une date manquante ne doit pas
    faire disparaitre un marche peut-etre frais. La ligne l'affiche « date inconnue »."""
    _preparer(tmp_path, monkeypatch, [
        _ao("MX-1", "Nettoyage recent", _il_y_a(1)),
        _ao("MX-2", "Nettoyage sans date", None),
        _ao("MX-3", "Nettoyage ancien", _il_y_a(60)),
    ])
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.selectbox(key="publie_depuis").select("7 derniers jours").run()

    textes = _textes(at)
    assert "Nettoyage recent" in textes
    assert "Nettoyage sans date" in textes
    assert "Nettoyage ancien" not in textes


def test_le_filtre_se_combine_avec_celui_des_rejetes(tmp_path, monkeypatch):
    chemin = tmp_path / "veille.json"
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "local")
    monkeypatch.setenv("CHRUTH_VEILLE_ETAT", str(chemin))
    monkeypatch.delenv("CHRUTH_VEILLE_GUIDE", raising=False)

    etat = ve.charger(chemin)
    ve.ajouter(etat, _ao("MX-1", "Nettoyage recent", _il_y_a(1)),
               Verdict(PERTINENT, "listes", "ok"), None)
    ve.ajouter(etat, _ao("MX-2", "Elagage recent", _il_y_a(1)),
               Verdict("REJETE", "listes", "exclusion metier : elagage"), None)
    chemin.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")

    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.selectbox(key="publie_depuis").select("7 derniers jours").run()
    assert "Elagage recent" not in _textes(at)

    at.checkbox(key="voir_rejetes").check().run()
    assert "Elagage recent" in _textes(at)
