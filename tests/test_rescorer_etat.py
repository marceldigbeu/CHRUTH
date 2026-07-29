"""Rescorer l'etat de veille ne doit rien couter au travail deja fait a la main."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "outils"))

import rescorer_base as rb  # noqa: E402


def test_la_correction_humaine_survit_au_rescore():
    avant = {"MX-1": {"objet": "Nettoyage", "score": 65, "correction_humaine":
                      {"verdict": "PERTINENT", "le": "2026-07-01", "par": "app"}}}
    apres = {"MX-1": {"objet": "Nettoyage", "score": 71.4, "correction_humaine": None}}

    fusion = rb.fusionner_travail_humain(avant, apres)

    assert fusion["MX-1"]["score"] == 71.4, "le nouveau score doit bien s'appliquer"
    assert fusion["MX-1"]["correction_humaine"]["verdict"] == "PERTINENT"


def test_le_suivi_et_la_lecture_survivent():
    avant = {"MX-1": {"traitement": "repondu", "lu": True,
                      "notifie_le": "2026-07-01T10:00:00+00:00", "vu_le": "2026-06-30"}}
    apres = {"MX-1": {"traitement": "nouveau", "lu": False, "notifie_le": None}}

    fusion = rb.fusionner_travail_humain(avant, apres)

    assert fusion["MX-1"]["traitement"] == "repondu"
    assert fusion["MX-1"]["lu"] is True
    assert fusion["MX-1"]["notifie_le"] == "2026-07-01T10:00:00+00:00"
    assert fusion["MX-1"]["vu_le"] == "2026-06-30", "la date de decouverte ne se reinitialise pas"


def test_un_ao_depublie_entre_temps_n_est_pas_perdu():
    avant = {"MX-DISPARU": {"objet": "Nettoyage", "traitement": "repondu"}}
    apres = {"MX-2": {"objet": "Proprete"}}

    fusion = rb.fusionner_travail_humain(avant, apres)

    assert "MX-DISPARU" in fusion, "un marche auquel on a repondu ne doit pas disparaitre"
    assert "MX-2" in fusion


def test_un_ao_nouveau_passe_tel_quel():
    fusion = rb.fusionner_travail_humain({}, {"MX-3": {"objet": "Nettoyage", "score": 55.2}})
    assert fusion["MX-3"]["score"] == 55.2


def test_une_valeur_humaine_vide_n_ecrase_pas_la_nouvelle():
    avant = {"MX-1": {"traitement": "", "lu": False, "correction_humaine": None}}
    apres = {"MX-1": {"traitement": "nouveau", "lu": False, "correction_humaine": None}}

    fusion = rb.fusionner_travail_humain(avant, apres)

    assert fusion["MX-1"]["traitement"] == "nouveau"
