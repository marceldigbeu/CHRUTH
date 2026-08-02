from __future__ import annotations

import provenance_ao


def test_un_avis_boamp_peut_etre_publie_sur_place():
    ligne = {
        "source": "BOAMP",
        "url_avis": "https://www.boamp.fr/avis/detail/1",
        "url_profil_acheteur": "https://www.marches-publics.gouv.fr/entreprise",
    }
    assert provenance_ao.detecter(ligne) == ("BOAMP", "PLACE")


def test_achatpublic_est_detecte_depuis_le_lien_dce():
    ligne = {
        "source": "BOAMP",
        "url_dce": "https://marchesonline.achatpublic.com/sdm/ent/gen/index.jsp",
    }
    assert provenance_ao.detecter(ligne) == ("BOAMP", "Achatpublic")


def test_maximilien_est_a_la_fois_source_et_plateforme():
    ligne = {
        "source": "MAXIMILIEN",
        "url": "https://marches.maximilien.fr/entreprise/consultation/42",
    }
    assert provenance_ao.detecter(ligne) == ("Maximilien", "Maximilien")


def test_les_sous_domaines_marches_publics_info_sont_reconnus():
    ligne = {
        "source": "BOAMP",
        "url_profil_acheteur": "https://agysoft.marches-publics.info/mpiaws/index.cfm",
    }
    assert provenance_ao.detecter(ligne) == ("BOAMP", "Marchés-Publics.info")


def test_un_domaine_inconnu_reste_visible_sans_fausse_attribution():
    ligne = {"source": "BOAMP", "url_dce": "https://depot.exemple.fr/dce/1"}
    assert provenance_ao.plateforme_publication(ligne) == \
        "Site externe (depot.exemple.fr)"



def test_une_plateforme_connue_prime_sur_un_site_externe():
    ligne = {
        "source": "BOAMP",
        "url_profil_acheteur": "https://acheteur.example/profil",
        "url_dce": "https://www.e-marches-publics.com/dossier/1",
    }
    assert provenance_ao.plateforme_publication(ligne) == "e-marchespublics"


def test_daco_achats_est_reconnu():
    assert provenance_ao.plateforme_url("https://daco-achats.fr/avis/1") == "Daco Achats"

def test_un_simple_avis_boamp_ne_devient_pas_une_plateforme_de_dce():
    ligne = {"source": "BOAMP", "url": "https://www.boamp.fr/avis/detail/1"}
    assert provenance_ao.plateforme_publication(ligne) == "Plateforme non identifiée"
