"""Mission 3 (perf) - mesure des taux par variante et selection du gagnant.

Garde-fou : on ne bascule sur une variante que si CHAQUE variante du segment a
au moins `seuil` resultats saisis (sinon on garde l'alternance 50/50)."""
from __future__ import annotations

import pandas as pd

SEUIL_DEFAUT = 20
_RESULTATS = {"REPONDU", "RDV", "REFUS"}


def calculer_perf(df_suivi: pd.DataFrame) -> pd.DataFrame:
    lignes = []
    if df_suivi.empty:
        return pd.DataFrame(columns=[
            "segment", "variante", "nb_envoyes", "nb_resultats",
            "taux_reponse", "taux_rdv"])
    for (seg, var), sub in df_suivi.groupby(["segment", "variante"]):
        statuts = sub["statut"].astype(str)
        nb_envoyes = int((statuts != "A_ENVOYER").sum())
        nb_resultats = int(statuts.isin(_RESULTATS).sum())
        nb_rdv = int((statuts == "RDV").sum())
        nb_reponse = int(statuts.isin({"REPONDU", "RDV"}).sum())
        taux_reponse = nb_reponse / nb_envoyes if nb_envoyes else 0.0
        taux_rdv = nb_rdv / nb_envoyes if nb_envoyes else 0.0
        lignes.append({
            "segment": seg, "variante": var, "nb_envoyes": nb_envoyes,
            "nb_resultats": nb_resultats, "taux_reponse": round(taux_reponse, 4),
            "taux_rdv": round(taux_rdv, 4)})
    return pd.DataFrame(lignes).sort_values(["segment", "variante"]).reset_index(drop=True)


def variante_recommandee(df_perf: pd.DataFrame, seuil: int = SEUIL_DEFAUT) -> dict[str, str]:
    reco = {}
    if df_perf.empty:
        return reco
    for seg, sub in df_perf.groupby("segment"):
        if len(sub) < 2 or (sub["nb_resultats"] < seuil).any():
            continue  # pas assez de donnees sur au moins une variante
        # meilleur taux_rdv ; egalite => 'A' (ordre alphabetique stable)
        sub = sub.sort_values(["taux_rdv", "variante"], ascending=[False, True])
        reco[seg] = str(sub.iloc[0]["variante"])
    return reco
