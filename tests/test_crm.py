import pandas as pd

import crm


def test_charger_vide_retourne_colonnes(tmp_path):
    df = crm.charger(tmp_path / "x.csv")
    assert list(df.columns) == crm.COLONNES
    assert df.empty


def test_ajouter_cree_fichier_avec_id_et_date(tmp_path):
    p = tmp_path / "crm.csv"
    crm.ajouter({"denomination": "Alpha", "statut": "DEVIS_ENVOYE",
                 "montant_devis_eur": "1200"}, path=p)
    df = crm.charger(p)
    assert len(df) == 1
    row = df.iloc[0]
    assert row["denomination"] == "Alpha"
    assert row["id"] and row["date_saisie"]   # auto-renseignes


def test_ajouter_append(tmp_path):
    p = tmp_path / "crm.csv"
    crm.ajouter({"denomination": "Alpha", "statut": "GAGNE"}, path=p)
    crm.ajouter({"denomination": "Beta", "statut": "PERDU"}, path=p)
    assert len(crm.charger(p)) == 2


def test_kpis_conversion_ca_et_churn():
    df = pd.DataFrame([
        {"statut": "GAGNE", "montant_contrat_annuel_eur": "10000", "montant_devis_eur": "10000"},
        {"statut": "CLIENT_ACTIF", "montant_contrat_annuel_eur": "20000", "montant_devis_eur": ""},
        {"statut": "CLIENT_PERDU", "montant_contrat_annuel_eur": "5000", "montant_devis_eur": ""},
        {"statut": "DEVIS_ENVOYE", "montant_contrat_annuel_eur": "", "montant_devis_eur": "3000"},
        {"statut": "PERDU", "montant_contrat_annuel_eur": "", "montant_devis_eur": ""},
    ])
    k = crm.kpis(df)
    assert k["nb_total"] == 5
    assert k["nb_gagnes"] == 2                       # GAGNE + CLIENT_ACTIF
    assert k["ca_signe_annuel_eur"] == 30000.0       # 10000 + 20000
    assert k["ca_pipeline_devis_eur"] == 3000.0      # DEVIS_ENVOYE
    assert k["taux_conversion"] == round(2 / 5, 3)
    assert k["taux_churn"] == round(1 / 2, 3)        # 1 perdu / (1 actif + 1 perdu)
