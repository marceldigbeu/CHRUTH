from datetime import date

import acheteurs_semaine as asem


def _fake_chercher(siret):
    if siret.endswith("0019"):
        return {"adresse": "PLACE X 75004 PARIS", "code_postal": "75004", "libelle_commune": "PARIS",
                "tranche_effectif_salarie": "42", "nature_juridique": "7210"}
    return None


def test_enrichir_remplit_et_classe():
    a = {"acheteur": "Mairie", "siret": "21750001600019", "departement": "75"}
    out = asem.enrichir(a, chercher=_fake_chercher)
    assert out["enrichi"] is True
    assert out["code_postal"] == "75004"
    assert out["type"] == "public" and out["type_incertain"] is False


def test_enrichir_best_effort_si_pas_de_fiche():
    a = {"acheteur": "Immobilière 3F", "siret": "", "departement": "93"}
    out = asem.enrichir(a, chercher=_fake_chercher)   # pas de SIRET -> pas de fiche
    assert out["enrichi"] is False
    assert out["type"] == "prive" and out["type_incertain"] is True  # repli sur le nom


def test_construire_pipeline_complet():
    boamp = [{"objet": "Nettoyage", "acheteur": "Mairie", "siret_acheteur": "21750001600019",
              "siren_acheteur": "217500016", "ville": "Paris", "departement": "75",
              "date_publication": "2026-07-24", "url_avis": "u", "priorite": "CHAUD"}]
    df = asem.construire(aujourd_hui=date(2026, 7, 27), records_boamp=boamp,
                         etat_maximilien={"aos": {}}, chercher=_fake_chercher)
    assert len(df) == 1
    assert set(["acheteur", "type", "nb_ao_semaine", "code_postal", "enrichi"]).issubset(df.columns)
    assert df.iloc[0]["type"] == "public"


def test_enrichir_best_effort_chercher_leve():
    """Test que enrichir() attrape les exceptions du chercher et conserve la ligne avec fallback nom."""
    def chercher_qui_leve(siret):
        raise RuntimeError("API indisponible")

    a = {"acheteur": "Mairie de Paris", "siret": "21750001600019", "departement": "75"}
    out = asem.enrichir(a, chercher=chercher_qui_leve)

    # Row conservée malgré l'exception
    assert out["acheteur"] == "Mairie de Paris"
    assert out["siret"] == "21750001600019"
    assert out["departement"] == "75"
    # Pas d'enrichissement via SIRET (chercher a levé)
    assert out["enrichi"] is False
    # Classe via nom (Mairie -> public)
    assert out["type"] == "public"
    assert out["type_incertain"] is True


def test_construire_tri_multi_acheteur():
    """Test que construire() trie les acheteurs par priorité (CHAUD>TIEDE) puis nb_ao_semaine desc."""
    boamp = [
        # Acheteur TIEDE, 1 AO
        {"objet": "Service 1", "acheteur": "Acheteur TIEDE", "siret_acheteur": "11111111111111",
         "siren_acheteur": "111111111", "ville": "Ville1", "departement": "01",
         "date_publication": "2026-07-26", "url_avis": "u1", "priorite": "TIEDE"},
        # Acheteur CHAUD, 1 AO
        {"objet": "Service 2", "acheteur": "Acheteur CHAUD 1", "siret_acheteur": "22222222222222",
         "siren_acheteur": "222222222", "ville": "Ville2", "departement": "02",
         "date_publication": "2026-07-27", "url_avis": "u2", "priorite": "CHAUD"},
        # Acheteur CHAUD, 2ème AO (même acheteur)
        {"objet": "Service 3", "acheteur": "Acheteur CHAUD 2", "siret_acheteur": "33333333333333",
         "siren_acheteur": "333333333", "ville": "Ville3", "departement": "03",
         "date_publication": "2026-07-27", "url_avis": "u3", "priorite": "CHAUD"},
        # Acheteur CHAUD, 2ème AO (pour avoir 2 AOs)
        {"objet": "Service 4", "acheteur": "Acheteur CHAUD 2", "siret_acheteur": "33333333333333",
         "siren_acheteur": "333333333", "ville": "Ville3", "departement": "03",
         "date_publication": "2026-07-27", "url_avis": "u4", "priorite": "CHAUD"},
    ]

    def chercher_neutre(siret):
        # Pas d'enrichissement via API (retourne None)
        return None

    df = asem.construire(aujourd_hui=date(2026, 7, 27), records_boamp=boamp,
                         etat_maximilien={"aos": {}}, chercher=chercher_neutre)

    # 3 acheteurs après déduplication par clé (siret ou nom|dept)
    assert len(df) == 3

    # Vérifie l'ordre: CHAUD(2 AOs) -> CHAUD(1 AO) -> TIEDE
    assert df.iloc[0]["acheteur"] == "Acheteur CHAUD 2"
    assert df.iloc[0]["nb_ao_semaine"] == 2
    assert df.iloc[0]["priorite"] == "CHAUD"

    assert df.iloc[1]["acheteur"] == "Acheteur CHAUD 1"
    assert df.iloc[1]["nb_ao_semaine"] == 1
    assert df.iloc[1]["priorite"] == "CHAUD"

    assert df.iloc[2]["acheteur"] == "Acheteur TIEDE"
    assert df.iloc[2]["nb_ao_semaine"] == 1
    assert df.iloc[2]["priorite"] == "TIEDE"
