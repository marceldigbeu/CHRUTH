"""Un AO sans lien vers son avis oblige a le rechercher a la main : on verifie
que toutes les colonnes d'adresse sont reconnues, quel que soit l'onglet."""
from __future__ import annotations

from liens_source import (colonnes_de_lien, est_colonne_de_lien, libelle,
                          premiere_source)


def test_les_colonnes_d_adresse_sont_reconnues():
    assert est_colonne_de_lien("url_avis")
    assert est_colonne_de_lien("URL_DCE")
    assert est_colonne_de_lien("Lien avis")
    assert est_colonne_de_lien("url_profil_acheteur")


def test_les_colonnes_ordinaires_ne_le_sont_pas():
    for nom in ("objet", "acheteur", "score_chruth", "date_limite", "ville"):
        assert not est_colonne_de_lien(nom)


def test_les_colonnes_de_lien_sont_extraites_dans_l_ordre():
    colonnes = ["objet", "url_avis", "acheteur", "url_dce", "score_chruth"]
    assert colonnes_de_lien(colonnes) == ["url_avis", "url_dce"]


def test_un_onglet_sans_lien_ne_produit_rien():
    assert colonnes_de_lien(["objet", "acheteur"]) == []


def test_les_libelles_connus_sont_lisibles():
    assert libelle("url_avis") == "Avis d'origine"
    assert libelle("url_dce") == "Dossier de consultation"
    assert libelle("url_profil_acheteur") == "Profil acheteur"


def test_une_colonne_de_lien_inconnue_garde_un_libelle_utilisable():
    assert libelle("url_plateforme_depot") == "Url plateforme depot"


def test_la_premiere_source_privilegie_l_avis_sur_le_dce():
    ligne = {"url_dce": "https://dce.example/1", "url_avis": "https://boamp.fr/1"}
    assert premiere_source(ligne) == "https://boamp.fr/1"


def test_la_premiere_source_se_rabat_sur_le_dce():
    assert premiere_source({"url_avis": "", "url_dce": "https://dce.example/1"}) \
        == "https://dce.example/1"


def test_une_valeur_qui_n_est_pas_une_adresse_est_ignoree():
    """Le champ contient parfois « a verifier » ou un identifiant : en faire un
    lien produirait un clic mort."""
    assert premiere_source({"url_avis": "a verifier", "url_dce": "26-74949"}) == ""


def test_un_ao_sans_aucune_adresse_ne_casse_rien():
    assert premiere_source({}) == ""
    assert premiere_source({"url_avis": None}) == ""
