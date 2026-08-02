from __future__ import annotations

import pandas as pd

import veille_sources


def _ligne(**modifications):
    ligne = {
        "id_ao": "BOAMP-1",
        "objet": "Nettoyage de locaux",
        "acheteur": "Commune exemple",
        "departement": "75",
        "date_publication": "2026-08-02",
        "date_limite": "2026-09-01",
        "score_chruth": "72.5",
        "priorite": "CHAUD",
        "url_avis": "https://exemple.fr/avis",
    }
    ligne.update(modifications)
    return ligne


def test_la_base_boamp_alimente_un_etat_vide():
    etat, ajoutes = veille_sources.fusionner_boamp(
        {"aos": {}}, pd.DataFrame([_ligne()])
    )

    assert ajoutes == 1
    assert etat["aos"]["BOAMP-1"]["objet"] == "Nettoyage de locaux"
    assert etat["aos"]["BOAMP-1"]["tri"]["verdict"] == "PERTINENT"


def test_un_ao_partage_existant_n_est_jamais_ecrase():
    existant = {"objet": "Version corrigée", "correction_humaine": {"verdict": "PERTINENT"}}
    etat, ajoutes = veille_sources.fusionner_boamp(
        {"aos": {"BOAMP-1": existant}}, pd.DataFrame([_ligne(objet="Version brute")])
    )

    assert ajoutes == 0
    assert etat["aos"]["BOAMP-1"] == existant


def test_les_valeurs_vides_et_les_urls_de_repli_sont_nettoyees():
    convertie = veille_sources.entree_boamp(
        _ligne(objet=float("nan"), url_avis="", url_dce="https://exemple.fr/dce")
    )

    assert convertie is not None
    _, entree = convertie
    assert entree["objet"] == ""
    assert entree["url"] == "https://exemple.fr/dce"


def test_une_base_vide_ne_modifie_pas_l_etat():
    initial = {"aos": {"M-1": {"objet": "Marché existant"}}, "version": 1}
    etat, ajoutes = veille_sources.fusionner_boamp(initial, pd.DataFrame())

    assert ajoutes == 0
    assert etat == initial
