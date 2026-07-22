import pytest

from ao_collect_boamp import is_relevant
from ao_export_excel import SHEET_ORDER, vba_module_text
from config import departements_des_regions, normaliser_region
from outils.refresh_runner import resoudre

BRETAGNE = ["22", "29", "35", "56"]


def _record(dept: str) -> dict:
    # Avis actif (appel d'offres) + mot-cle CHRUTH fort, dans le departement donne.
    return {
        "nature_libelle": "appel d'offres ouvert",
        "objet": "nettoyage des locaux",
        "code_departement_prestation": dept,
    }


def test_region_mapping_bretagne():
    assert departements_des_regions(["Bretagne"]) == BRETAGNE


def test_region_mapping_accents_insensible():
    assert departements_des_regions(["ile-de-france"]) == departements_des_regions(["Île-de-France"])
    assert normaliser_region("AUVERGNE RHONE ALPES") == "Auvergne-Rhône-Alpes"


def test_region_inconnue_leve():
    with pytest.raises(ValueError):
        departements_des_regions(["Atlantide"])


def test_is_relevant_garde_la_region():
    keep, _ = is_relevant(_record("35"), {}, strict_budget=False, idf_only=False,
                          region_departements=BRETAGNE)
    assert keep is True


def test_is_relevant_rejette_hors_region():
    keep, reason = is_relevant(_record("75"), {}, strict_budget=False, idf_only=False,
                               region_departements=BRETAGNE)
    assert keep is False
    assert reason == "hors region"


def test_ao_region_dans_sheet_order():
    assert "AO_Region" in SHEET_ORDER


def test_vba_lit_la_cellule_region():
    src = vba_module_text()
    assert 'Sheets("Parametres")' in src
    assert "B1" in src


def test_refresh_runner_ao_ajoute_la_region():
    _, cmd = resoudre("ao", "Bretagne")
    assert cmd[-2:] == ["--regions", "Bretagne"]
    _, cmd_sans = resoudre("ao", None)
    assert "--regions" not in cmd_sans
