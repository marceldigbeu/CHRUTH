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


def test_la_page_annonce_le_volume_et_la_repartition(monkeypatch):
    """Le nombre d'AO et les priorites restent lisibles, mais plus comme deux
    nombres isoles : le total passe en sous-titre, les priorites en repartition,
    ou « 1 chaud » se lit enfin avec les tiedes et les froids."""
    monkeypatch.setattr(ao_db, "fetch_records", lambda *a, **kw: _df())
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    assert not at.exception
    assert any("2 appels d'offres en base" in c.value for c in at.caption)
    tables = [d.value for d in at.dataframe]
    priorites = [t for t in tables if "priorite" in getattr(t, "columns", [])]
    assert priorites, "la repartition par priorite doit etre affichee"
    assert set(priorites[0]["priorite"]) == {"CHAUD", "TIEDE"}


def test_la_page_met_en_tete_ce_qui_attend(monkeypatch):
    """Le haut de page doit porter ce sur quoi on peut agir aujourd'hui."""
    monkeypatch.setattr(ao_db, "fetch_records", lambda *a, **kw: _df())
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    assert at.subheader[0].value == "Ce qui attend"
    labels = [m.label for m in at.metric]
    assert "En attente de tri" in labels


def test_la_page_ne_montre_pas_d_indicateur_invariant(monkeypatch):
    """« AO en Ile-de-France » valait toujours le total, la collecte etant
    filtree sur l'Ile-de-France : un indicateur qui ne peut pas varier
    n'informe de rien."""
    monkeypatch.setattr(ao_db, "fetch_records", lambda *a, **kw: _df())
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    labels = " ".join(m.label for m in at.metric).lower()
    assert "France" .lower() not in labels


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
