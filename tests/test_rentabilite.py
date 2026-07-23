import pandas as pd

import rentabilite as r
from config import TARIF_NETTOYAGE_PAR_SALARIE, TAUX_MARGE_NETTOYAGE


def _df():
    return pd.DataFrame([
        {"categorie_chruth": "PRIV_BUREAU", "priorite": "CHAUDE", "effectif_nombre": "100"},
        {"categorie_chruth": "PRIV_SANTE_CABINET", "priorite": "TIEDE", "effectif_nombre": "10"},
        {"categorie_chruth": "PRIV_BUREAU", "priorite": "CHAUDE", "effectif_nombre": "50"},
        {"categorie_chruth": "AUTRE", "priorite": "FROIDE", "effectif_nombre": ""},
    ])


def test_ca_estime_proportionnel_effectif_et_categorie():
    ca = r.ca_estime({"categorie_chruth": "PRIV_BUREAU", "effectif_nombre": "100"})
    assert ca == 100 * TARIF_NETTOYAGE_PAR_SALARIE["PRIV_BUREAU"]


def test_ca_estime_categorie_inconnue_utilise_defaut():
    from config import TARIF_NETTOYAGE_DEFAUT
    assert r.ca_estime({"categorie_chruth": "AUTRE", "effectif_nombre": "10"}) == 10 * TARIF_NETTOYAGE_DEFAUT


def test_ca_estime_effectif_vide_donne_zero():
    assert r.ca_estime({"categorie_chruth": "PRIV_BUREAU", "effectif_nombre": ""}) == 0


def test_enrichir_ajoute_colonnes_ca_et_marge():
    out = r.enrichir(_df())
    assert "ca_estime_eur" in out.columns and "marge_estimee_eur" in out.columns
    row = out.iloc[0]
    assert round(row["marge_estimee_eur"]) == round(row["ca_estime_eur"] * TAUX_MARGE_NETTOYAGE)


def test_table_segments_agrege_et_classe_par_marge():
    t = r.table_segments(_df())
    assert {"categorie_chruth", "priorite", "nb_prospects",
            "ca_potentiel_total", "marge_potentielle_total"}.issubset(t.columns)
    assert t.iloc[0]["rang"] == 1
    assert t["marge_potentielle_total"].iloc[0] >= t["marge_potentielle_total"].iloc[-1]
