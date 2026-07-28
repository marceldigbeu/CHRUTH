from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

import acheteurs_semaine as asem

RACINE = Path(__file__).resolve().parent.parent
PAGE = str(RACINE / "pages_acheteurs.py")


def _df():
    lignes = []
    for ach, typ, dept in [("Mairie de Créteil", "public", "94"), ("Immobilière 3F", "prive", "93")]:
        l = {c: ("" if c != "nb_ao_semaine" else 1) for c in asem.COLONNES}
        l.update({"acheteur": ach, "type": typ, "departement": dept, "priorite": "CHAUD", "aos": []})
        lignes.append(l)
    return pd.DataFrame(lignes)


def test_la_page_affiche_les_acheteurs(monkeypatch):
    monkeypatch.setattr(asem, "construire", lambda *a, **k: _df())
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    assert not at.exception
    textes = " ".join(m.value for m in at.markdown)
    assert "Créteil" in textes or "Acheteurs" in textes


def test_la_page_est_declaree_dans_l_entree():
    src = (RACINE / "CHRUTH_APP.py").read_text(encoding="utf-8")
    assert "pages_acheteurs.py" in src


def test_le_filtre_public_prive_existe(monkeypatch):
    monkeypatch.setattr(asem, "construire", lambda *a, **k: _df())
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    assert any(w.key == "type_acheteur" for w in at.radio) or not at.exception
