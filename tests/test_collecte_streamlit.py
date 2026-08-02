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


def test_progression_ao_traduit_les_etapes_techniques():
    texte = """
Collecte lancée depuis Streamlit
[collecte] ON
=== 1. Collecte BOAMP ===
Collecte BOAMP CHRUTH terminee
fetched: 1554
kept: 37
"""
    progression = collecte.progression_depuis_texte(texte, "ao")
    assert progression.pourcentage == 55
    assert progression.etape == "Sélection des appels d'offres"
    assert progression.details == "37 appels d'offres retenus sur 1554 avis analysés."


def test_un_succes_force_cent_pour_cent():
    progression = collecte.progression_depuis_texte("[collecte] ON", "ao", code_retour=0)
    assert progression.pourcentage == 100
    assert progression.etape == "Collecte terminée"


def test_un_echec_ne_se_presente_jamais_comme_termine():
    progression = collecte.progression_depuis_texte(
        "Collecte BOAMP CHRUTH terminee", "ao", code_retour=1
    )
    assert progression.pourcentage < 100
    assert progression.etape == "Collecte interrompue"


def test_la_page_normale_ne_montre_ni_terminal_ni_commande():
    source = (Path(__file__).resolve().parent.parent / "pages_collecte.py").read_text(
        encoding="utf-8"
    )
    assert "st.code" not in source
    assert "Commande qui sera exécutée" not in source
    assert "Journal :" not in source
    assert "processus {processus_suivi.pid}" not in source
