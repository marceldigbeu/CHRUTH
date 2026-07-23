from ao_collect_boamp import record_to_ao


def test_record_to_ao_fills_url_dce():
    record = {
        "idweb": "26-1", "objet": "nettoyage des locaux",
        "nature_libelle": "avis d'appel public a la concurrence",
        "donnees": {"docs": "retrait du dossier sur https://www.marches-publics.info/annonce/26-1"},
    }
    ao = record_to_ao(record)
    assert "marches-publics.info" in ao["url_dce"]
    assert ao["url_profil_acheteur"] == ao["url_dce"]
