"""Mission 4 — CRM de capture : enregistre le suivi commercial reel (prospect
contacte -> devis -> contrat) au fur et a mesure. Sert d'instrumentation : une
fois quelques mois de donnees accumules, on pourra analyser la rentabilite REELLE
par client et le churn (ce que le modele estime ne fait qu'approcher).

Stockage : crm/suivi_clients.csv (donnees commerciales -> gitignore).
"""
from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
CRM_PATH = BASE_DIR / "crm" / "suivi_clients.csv"

COLONNES = [
    "id", "date_saisie", "siret", "denomination", "categorie", "statut",
    "montant_devis_eur", "montant_contrat_annuel_eur", "type_prestation",
    "date_debut", "date_fin", "canal", "commentaire",
]
STATUTS = [
    "PROSPECT_CONTACTE", "DEVIS_ENVOYE", "GAGNE", "PERDU",
    "CLIENT_ACTIF", "CLIENT_PERDU",
]


def charger(path: Path = CRM_PATH) -> pd.DataFrame:
    p = Path(path)
    if p.exists():
        df = pd.read_csv(p, dtype=str).fillna("")
        for c in COLONNES:
            if c not in df.columns:
                df[c] = ""
        return df[COLONNES]
    return pd.DataFrame(columns=COLONNES)


def ajouter(record: dict, path: Path = CRM_PATH) -> pd.DataFrame:
    df = charger(path)
    ligne = {c: "" for c in COLONNES}
    ligne.update({k: str(v) for k, v in record.items() if k in COLONNES})
    ligne["id"] = ligne["id"] or uuid.uuid4().hex[:8]
    ligne["date_saisie"] = ligne["date_saisie"] or date.today().isoformat()
    df = pd.concat([df, pd.DataFrame([ligne])[COLONNES]], ignore_index=True)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    return df


def _num(serie) -> pd.Series:
    return pd.to_numeric(serie, errors="coerce").fillna(0)


def kpis(df: pd.DataFrame) -> dict:
    n = len(df)
    if n == 0:
        return {"nb_total": 0, "nb_gagnes": 0, "taux_conversion": 0.0,
                "ca_signe_annuel_eur": 0.0, "ca_pipeline_devis_eur": 0.0, "taux_churn": 0.0}
    st = df["statut"].astype(str)
    gagnes_mask = st.isin(["GAGNE", "CLIENT_ACTIF"])
    nb_gagnes = int(gagnes_mask.sum())
    clients_actifs = int((st == "CLIENT_ACTIF").sum())
    clients_perdus = int((st == "CLIENT_PERDU").sum())
    base_clients = clients_actifs + clients_perdus
    return {
        "nb_total": n,
        "nb_gagnes": nb_gagnes,
        "taux_conversion": round(nb_gagnes / n, 3),
        "ca_signe_annuel_eur": float(_num(df.loc[gagnes_mask, "montant_contrat_annuel_eur"]).sum()),
        "ca_pipeline_devis_eur": float(_num(df.loc[st == "DEVIS_ENVOYE", "montant_devis_eur"]).sum()),
        "taux_churn": round(clients_perdus / base_clients, 3) if base_clients else 0.0,
    }
