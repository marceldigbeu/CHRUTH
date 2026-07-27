"""Pages Base, Carte et Developpeur reliees au dossier output."""
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook
from streamlit.testing.v1 import AppTest

import livrables_chruth

RACINE = Path(__file__).resolve().parent.parent


@pytest.fixture
def output_test(tmp_path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    wb = Workbook()
    ws = wb.active
    ws.title = "AO_Tous"
    ws.append(["id_ao", "objet", "acheteur", "priorite"])
    ws.append(["AO-1", "Nettoyage des locaux", "Ville Test", "CHAUD"])
    ws2 = wb.create_sheet("Pilotage")
    ws2.append(["Indicateur", "Valeur"])
    ws2.append(["AO", 1])
    wb.save(output / "AO_CHRUTH.xlsm")
    pd.DataFrame([
        {"siret": "123", "denomination": "Societe Test", "enseigne": "",
         "categorie_chruth": "PRIV_BUREAU", "domaine_chruth": "PRIVE",
         "adresse_complete": "1 rue Test", "libelle_commune": "PARIS",
         "code_departement": "75", "effectif_label": "10 a 19",
         "latitude": "48.8", "longitude": "2.3"},
    ]).to_csv(output / "prospects_enrichis.csv", index=False)
    (output / "Carte_Prospects_CHRUTH.html").write_text(
        "<html><body><h1>Carte test</h1></body></html>", encoding="utf-8")
    (tmp_path / "CHRUTH_PIPELINE_UNIQUE.py").write_text("print('test')\n", encoding="utf-8")
    monkeypatch.setenv("CHRUTH_OUTPUT_DIR", str(output))
    return output


def test_le_dossier_explicite_est_prioritaire(output_test):
    assert livrables_chruth.dossier_output() == output_test.resolve()
    assert livrables_chruth.fichier("AO_CHRUTH.xlsm").is_file()


def test_la_page_base_affiche_les_deux_sources(output_test):
    at = AppTest.from_file(str(RACINE / "pages_donnees.py"), default_timeout=90)
    at.run()
    assert not at.exception
    assert "Base de donnees et fichiers" in [t.value for t in at.title]
    assert len(at.dataframe) >= 2


def test_la_page_carte_charge_le_html(output_test):
    at = AppTest.from_file(str(RACINE / "pages_carte.py"), default_timeout=90)
    at.run()
    assert not at.exception
    assert "Carte des prospects" in [t.value for t in at.title]


def test_la_page_collecte_est_prete_sans_lancer_le_pipeline(output_test):
    at = AppTest.from_file(str(RACINE / "pages_collecte.py"), default_timeout=90)
    at.run()
    assert not at.exception
    assert "Collecte des données" in [t.value for t in at.title]
    assert at.button(key="lancer_collecte").disabled


def test_le_mode_developpeur_lit_directement_le_classeur(output_test):
    at = AppTest.from_file(str(RACINE / "pages_developpeur.py"), default_timeout=90)
    at.run()
    at.toggle[0].set_value(True).run()
    assert not at.exception
    assert "Mode d\u00e9veloppeur" in [t.value for t in at.title]
    assert any("AO_Tous" in str(df.value) for df in at.dataframe)
