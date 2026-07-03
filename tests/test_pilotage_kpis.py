from datetime import date

import pandas as pd

from ao_pilotage import compute_kpis


def _df():
    return pd.DataFrame(
        [
            {"id_ao": "1", "priorite": "CHAUD", "departement": "75", "departement_prestation": "",
             "budget_statut": "", "statut_extraction": "OK"},
            {"id_ao": "2", "priorite": "TIEDE", "departement": "69", "departement_prestation": "",
             "budget_statut": "A_VERIFIER_BUDGET", "statut_extraction": "OK"},
            {"id_ao": "3", "priorite": "CHAUD", "departement": "", "departement_prestation": "93",
             "budget_statut": "", "statut_extraction": "DCE_A_TELECHARGER"},
        ]
    )


def test_kpis_counts():
    k = compute_kpis(_df(), today=date(2026, 6, 8))
    assert k["nb_ao"] == 3
    assert k["nb_chauds"] == 2
    assert k["nb_idf"] == 2
    assert k["budget_a_verifier"] == 1
    assert k["date_maj"] == "08/06/2026"
    assert k["nom_projet"] == "Prospection Appels d'Offres CHRUTH"


def test_kpis_check_qualite_alertes():
    k = compute_kpis(_df(), today=date(2026, 6, 8))
    assert k["check_qualite"] == "2 alertes"


def test_kpis_empty():
    k = compute_kpis(pd.DataFrame(), today=date(2026, 6, 8))
    assert k["nb_ao"] == 0
    assert k["check_qualite"] == "OK"
