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
