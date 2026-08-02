"""Collecte pilotée depuis Streamlit."""
import sys
from pathlib import Path

import collecte_streamlit as collecte


def _pipeline(tmp_path: Path) -> Path:
    script = tmp_path / "CHRUTH_PIPELINE_UNIQUE.py"
    script.write_text("print('ok')\n", encoding="utf-8")
    return script


def test_commande_ao_ne_retraite_pas_les_prospects_ni_la_finance(tmp_path):
    script = _pipeline(tmp_path)
    commande = collecte.construire_commande(tmp_path, "ao", regions="Île-de-France")
    assert str(script) in commande
    assert "--collect-ao" in commande
    assert "--skip-prospects" in commande
    assert "--skip-finance" in commande
    assert "--leave-collecte-on" in commande
    assert commande[-2:] == ["--regions", "Île-de-France"]


def test_commande_prospects_par_departements(tmp_path):
    _pipeline(tmp_path)
    commande = collecte.construire_commande(
        tmp_path,
        "prospects",
        scope="departements",
        departements="75,92",
    )
    assert "--skip-ao" in commande
    assert "--collect-prospects" in commande
    assert commande[-2:] == ["--departements", "75,92"]


def test_un_classeur_excel_ouvert_bloque_le_mode_concerne(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    (output / "~$AO_CHRUTH.xlsm").write_text("verrou", encoding="utf-8")
    assert [p.name for p in collecte.classeurs_verrouilles(output, "ao")] == ["AO_CHRUTH.xlsm"]
    assert collecte.classeurs_verrouilles(output, "prospects") == []


def test_le_lanceur_ecrit_un_journal_sans_bloquer_streamlit(tmp_path):
    script = _pipeline(tmp_path)
    processus, journal = collecte.lancer(tmp_path, [sys.executable, "-u", str(script)])
    assert processus.wait(timeout=10) == 0
    contenu = journal.read_text(encoding="utf-8")
    assert "Collecte lancée depuis Streamlit" in contenu
    assert "ok" in contenu
