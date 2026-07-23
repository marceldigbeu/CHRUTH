"""Page Pilotage : les KPI du cockpit, dans la plateforme."""
from pathlib import Path

import pandas as pd
import ao_db
from streamlit.testing.v1 import AppTest

PAGE = str(Path(__file__).resolve().parent.parent / "pages_pilotage.py")


def _df() -> pd.DataFrame:
    return pd.DataFrame([
        {"id_ao": "26-1", "objet": "Nettoyage", "priorite": "CHAUD", "departement": "93",
         "departement_prestation": "93", "budget_statut": "A_VERIFIER_BUDGET",
         "statut_extraction": "LISTING"},
        {"id_ao": "26-2", "objet": "Nettoyage", "priorite": "TIEDE", "departement": "75",
         "departement_prestation": "75", "budget_statut": "OK",
         "statut_extraction": "LISTING"},
    ])


def test_la_page_affiche_les_kpi(monkeypatch):
    monkeypatch.setattr(ao_db, "fetch_records", lambda *a, **kw: _df())
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    assert not at.exception
    valeurs = [m.value for m in at.metric]
    assert "2" in valeurs   # nb_ao
    assert "1" in valeurs   # nb_chauds


def test_la_page_supporte_une_base_vide(monkeypatch):
    monkeypatch.setattr(ao_db, "fetch_records", lambda *a, **kw: pd.DataFrame())
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    assert not at.exception
