import pandas as pd

import perf_messages as perf


def _suivi(rows):
    cols = ["siret", "segment", "variante", "statut"]
    return pd.DataFrame([dict(zip(cols, r)) for r in rows])


def test_calculer_perf_taux_corrects():
    df = _suivi([
        ("1", "S|CHAUDE", "A", "RDV"),
        ("2", "S|CHAUDE", "A", "REPONDU"),
        ("3", "S|CHAUDE", "A", "REFUS"),
        ("4", "S|CHAUDE", "A", "ENVOYE"),
    ])
    p = perf.calculer_perf(df)
    ligne = p[(p["segment"] == "S|CHAUDE") & (p["variante"] == "A")].iloc[0]
    assert ligne["nb_envoyes"] == 4        # tout sauf A_ENVOYER
    assert ligne["nb_resultats"] == 3      # RDV+REPONDU+REFUS
    assert round(ligne["taux_reponse"], 2) == 0.50   # (RDV+REPONDU)/envoyes
    assert round(ligne["taux_rdv"], 2) == 0.25


def test_calculer_perf_ignore_a_envoyer_au_denominateur():
    df = _suivi([("1", "S|CHAUDE", "A", "A_ENVOYER")])
    p = perf.calculer_perf(df)
    ligne = p[(p["segment"] == "S|CHAUDE") & (p["variante"] == "A")].iloc[0]
    assert ligne["nb_envoyes"] == 0
    assert ligne["taux_rdv"] == 0.0        # pas de division par zero


def test_variante_recommandee_none_sous_le_seuil():
    rows = [("x", "S|CHAUDE", "A", "RDV"), ("y", "S|CHAUDE", "B", "REPONDU")]
    p = perf.calculer_perf(_suivi(rows))
    assert perf.variante_recommandee(p, seuil=20) == {}


def test_variante_recommandee_bascule_au_dessus_du_seuil():
    rows = []
    # A : 20 resultats, 10 RDV (taux_rdv 0.5) ; B : 20 resultats, 2 RDV (0.1)
    for i in range(10):
        rows.append((f"a{i}", "S|CHAUDE", "A", "RDV"))
    for i in range(10):
        rows.append((f"a2{i}", "S|CHAUDE", "A", "REFUS"))
    rows.append(("b0", "S|CHAUDE", "B", "RDV"))
    rows.append(("b1", "S|CHAUDE", "B", "RDV"))
    for i in range(18):
        rows.append((f"b{i}x", "S|CHAUDE", "B", "REFUS"))
    p = perf.calculer_perf(_suivi(rows))
    assert perf.variante_recommandee(p, seuil=20) == {"S|CHAUDE": "A"}


def test_variante_recommandee_egalite_choisit_a():
    rows = []
    for i in range(20):
        rows.append((f"a{i}", "S|CHAUDE", "A", "RDV"))
    for i in range(20):
        rows.append((f"b{i}", "S|CHAUDE", "B", "RDV"))
    p = perf.calculer_perf(_suivi(rows))
    assert perf.variante_recommandee(p, seuil=20) == {"S|CHAUDE": "A"}
