"""Ecritures humaines dans l'etat : correction du tri, suivi, guide."""
import pytest

import veille_etat as ve
from ao_pertinence import PERTINENT, REJETE, Verdict


def _etat_avec_un_ao(tmp_path, verdict=REJETE):
    etat = ve.charger(tmp_path / "veille.json")
    ve.ajouter(etat, {"id_ao": "MX-1", "objet": "Elagage des arbres"},
               Verdict(verdict, "listes", "exclusion metier : elagage"), None)
    return etat


def test_corriger_pose_la_correction_humaine(tmp_path):
    etat = _etat_avec_un_ao(tmp_path)
    ve.corriger(etat, "MX-1", PERTINENT)
    entree = etat["aos"]["MX-1"]
    assert entree["correction_humaine"]["verdict"] == PERTINENT
    assert entree["correction_humaine"]["le"]


def test_le_verdict_effectif_suit_la_correction_humaine(tmp_path):
    etat = _etat_avec_un_ao(tmp_path)
    assert ve.verdict_effectif(etat["aos"]["MX-1"]) == REJETE
    ve.corriger(etat, "MX-1", PERTINENT)
    assert ve.verdict_effectif(etat["aos"]["MX-1"]) == PERTINENT


def test_la_correction_survit_a_un_nouveau_passage_du_tri(tmp_path):
    """Le veilleur repasse toutes les 30 min : il ne doit jamais effacer un jugement humain."""
    etat = _etat_avec_un_ao(tmp_path)
    ve.corriger(etat, "MX-1", PERTINENT)
    ve.ajouter(etat, {"id_ao": "MX-1", "objet": "Elagage des arbres"},
               Verdict(REJETE, "listes", "exclusion metier : elagage"), None)
    assert ve.verdict_effectif(etat["aos"]["MX-1"]) == PERTINENT


def test_corriger_un_ao_inconnu_leve(tmp_path):
    etat = ve.charger(tmp_path / "veille.json")
    with pytest.raises(KeyError):
        ve.corriger(etat, "MX-absent", PERTINENT)


def test_corriger_avec_un_verdict_inconnu_leve(tmp_path):
    etat = _etat_avec_un_ao(tmp_path)
    with pytest.raises(ValueError):
        ve.corriger(etat, "MX-1", "PEUT-ETRE")


def test_marquer_lu(tmp_path):
    etat = _etat_avec_un_ao(tmp_path)
    assert etat["aos"]["MX-1"]["lu"] is False
    ve.marquer_lu(etat, "MX-1")
    assert etat["aos"]["MX-1"]["lu"] is True
    ve.marquer_lu(etat, "MX-1", False)
    assert etat["aos"]["MX-1"]["lu"] is False


def test_definir_traitement(tmp_path):
    etat = _etat_avec_un_ao(tmp_path)
    ve.definir_traitement(etat, "MX-1", "a_traiter")
    assert etat["aos"]["MX-1"]["traitement"] == "a_traiter"


def test_un_statut_de_traitement_inconnu_leve(tmp_path):
    etat = _etat_avec_un_ao(tmp_path)
    with pytest.raises(ValueError):
        ve.definir_traitement(etat, "MX-1", "en_cours_peut_etre")


def test_le_traitement_survit_a_un_nouveau_passage_du_tri(tmp_path):
    etat = _etat_avec_un_ao(tmp_path)
    ve.definir_traitement(etat, "MX-1", "repondu")
    ve.ajouter(etat, {"id_ao": "MX-1", "objet": "Elagage des arbres"},
               Verdict(REJETE, "listes", "x"), None)
    assert etat["aos"]["MX-1"]["traitement"] == "repondu"


def test_le_guide_fait_un_aller_retour_disque(tmp_path):
    p = tmp_path / "veille.json"
    etat = ve.charger(p)
    ve.definir_guide(etat, "CHRUTH nettoie des bureaux en Île-de-France.")
    ve.enregistrer(etat, p)
    assert ve.charger(p)["guide_messages"] == "CHRUTH nettoie des bureaux en Île-de-France."
