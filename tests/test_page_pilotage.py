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


def test_en_ligne_la_page_dit_la_verite_sur_la_base(monkeypatch):
    """La base SQLite est locale et gitignoree : elle n'existe pas sur le cloud.

    Renvoyer l'utilisateur vers « lancer une mise a jour » y serait un mensonge —
    le bouton de la page Veille declenche le workflow, qui remplit l'etat partage,
    jamais cette base.
    """
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "github")
    monkeypatch.setattr(ao_db, "fetch_records", lambda *a, **kw: pd.DataFrame())
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    assert not at.exception
    messages = " ".join(i.value for i in at.info).lower()
    assert "mise à jour depuis la page veille" not in messages
    assert "local" in messages
