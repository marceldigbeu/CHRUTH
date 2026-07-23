"""Etat JSON de la veille : anti-doublon, suivi, guide."""
import json

import veille_etat as ve
from ao_pertinence import PERTINENT, Verdict


def test_charger_un_etat_absent_rend_une_structure_vide(tmp_path):
    etat = ve.charger(tmp_path / "absent.json")
    assert etat["version"] == ve.ETAT_VERSION
    assert etat["aos"] == {}
    assert etat["guide_messages"] == ""


def test_charger_un_fichier_corrompu_ne_casse_pas_la_veille(tmp_path):
    p = tmp_path / "veille.json"
    p.write_text("{ ceci n'est pas du json", encoding="utf-8")
    assert ve.charger(p)["aos"] == {}


def test_aller_retour_disque(tmp_path):
    p = tmp_path / "veille.json"
    etat = ve.charger(p)
    ve.ajouter(etat, {"id_ao": "MX-1", "objet": "Nettoyage"}, Verdict(PERTINENT, "listes", "ok"),
               notifie_le="2026-07-22T10:00:00Z")
    ve.enregistrer(etat, p)

    relu = ve.charger(p)
    assert relu["aos"]["MX-1"]["objet"] == "Nettoyage"
    assert relu["aos"]["MX-1"]["tri"]["verdict"] == PERTINENT
    assert relu["aos"]["MX-1"]["traitement"] == "nouveau"
    assert relu["aos"]["MX-1"]["lu"] is False


def test_nouveaux_ne_rend_que_les_inconnus(tmp_path):
    etat = ve.charger(tmp_path / "veille.json")
    ve.ajouter(etat, {"id_ao": "MX-1", "objet": "A"}, Verdict(PERTINENT, "listes", "ok"), None)
    a_traiter = ve.nouveaux(etat, [{"id_ao": "MX-1"}, {"id_ao": "MX-2"}])
    assert [a["id_ao"] for a in a_traiter] == ["MX-2"]


def test_le_fichier_est_lisible_et_indente(tmp_path):
    """L'etat est versionne dans git : un diff illisible serait un mauvais choix."""
    p = tmp_path / "veille.json"
    etat = ve.charger(p)
    ve.ajouter(etat, {"id_ao": "MX-1", "objet": "Nettoyage des ecoles"},
               Verdict(PERTINENT, "listes", "ok"), None)
    ve.enregistrer(etat, p)
    contenu = p.read_text(encoding="utf-8")
    assert "\n  " in contenu
    assert "Nettoyage des ecoles" in contenu  # non echappe en \uXXXX
    json.loads(contenu)
