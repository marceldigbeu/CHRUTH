import pandas as pd

import suivi_messages as sm


def _prospects(sirets):
    return pd.DataFrame([
        {"siret": s, "denomination": f"Soc{s}", "libelle_commune": "Paris",
         "categorie_chruth": "PRIV_BUREAU", "priorite": "CHAUDE"}
        for s in sirets
    ])


def test_synchroniser_cree_le_csv_et_assigne_variantes(tmp_path):
    path = tmp_path / "suivi.csv"
    df = sm.synchroniser(_prospects(["1", "2", "3", "4"]), path=path)
    assert path.exists()
    assert set(df.columns) == set(sm.COLONNES)
    assert (df["statut"] == "A_ENVOYER").all()
    # alternance 50/50 deterministe (ordre par siret) : A,B,A,B
    par_siret = dict(zip(df["siret"], df["variante"]))
    assert {par_siret["1"], par_siret["2"]} == {"A", "B"}
    assert sorted(df["variante"]).count("A") == 2
    assert df.loc[df["siret"] == "1", "template_id"].iloc[0] == "PRIV_BUREAU|CHAUDE|" + par_siret["1"]


def test_synchroniser_preserve_statut_saisi(tmp_path):
    path = tmp_path / "suivi.csv"
    sm.synchroniser(_prospects(["1", "2"]), path=path)
    # le commercial saisit un statut a la main
    df = pd.read_csv(path, dtype=str)
    df.loc[df["siret"] == "1", "statut"] = "RDV"
    df.loc[df["siret"] == "1", "date_resultat"] = "2026-06-30"
    df.to_csv(path, index=False, encoding="utf-8")
    # nouvelle regeneration (avec un prospect en plus)
    df2 = sm.synchroniser(_prospects(["1", "2", "3"]), path=path)
    ligne1 = df2[df2["siret"] == "1"].iloc[0]
    assert ligne1["statut"] == "RDV"          # PRESERVE (anti-regression bug AO)
    assert ligne1["date_resultat"] == "2026-06-30"
    assert (df2["siret"] == "3").any()         # nouveau ajoute
    assert df2[df2["siret"] == "3"].iloc[0]["statut"] == "A_ENVOYER"


def test_synchroniser_ne_reassigne_pas_la_variante_existante(tmp_path):
    path = tmp_path / "suivi.csv"
    df1 = sm.synchroniser(_prospects(["1", "2"]), path=path)
    var1 = dict(zip(df1["siret"], df1["variante"]))
    df2 = sm.synchroniser(_prospects(["1", "2", "3", "4"]), path=path)
    var2 = dict(zip(df2["siret"], df2["variante"]))
    assert var2["1"] == var1["1"] and var2["2"] == var1["2"]


def test_synchroniser_applique_recommandation_aux_nouveaux(tmp_path):
    path = tmp_path / "suivi.csv"
    sm.synchroniser(_prospects(["1", "2"]), path=path)
    reco = {"PRIV_BUREAU|CHAUDE": "B"}
    df2 = sm.synchroniser(_prospects(["1", "2", "5", "6"]), recommandations=reco, path=path)
    nouveaux = df2[df2["siret"].isin(["5", "6"])]
    assert (nouveaux["variante"] == "B").all()  # gagnante poussee 100% aux nouveaux


def test_synchroniser_siret_float_ne_cree_pas_de_doublon(tmp_path):
    """Un siret arrivant comme float 123.0 doit matcher '123' dans le CSV existant."""
    import pandas as pd
    path = tmp_path / "suivi.csv"
    # Premiere synchronisation : siret string "123"
    df_str = pd.DataFrame([{
        "siret": "123", "denomination": "Soc123", "libelle_commune": "Paris",
        "categorie_chruth": "PRIV_BUREAU", "priorite": "CHAUDE",
    }])
    sm.synchroniser(df_str, path=path)
    avant = pd.read_csv(path, dtype=str)
    assert len(avant) == 1

    # Deuxieme synchronisation : meme prospect mais siret arrive en float
    df_float = pd.DataFrame([{
        "siret": 123.0,  # float -> str naive donne "123.0"
        "denomination": "Soc123", "libelle_commune": "Paris",
        "categorie_chruth": "PRIV_BUREAU", "priorite": "CHAUDE",
    }])
    sm.synchroniser(df_float, path=path)
    apres = pd.read_csv(path, dtype=str)
    assert len(apres) == 1, "Le float 123.0 ne doit pas creer un doublon de '123'"
