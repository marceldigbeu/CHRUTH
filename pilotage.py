"""Calculs de la page Pilotage, hors Streamlit et hors Excel.

`ao_pilotage` rend l'onglet du classeur et ne bouge pas : ses quatre KPI sont
partages avec le tableur. Ce module ajoute ce que la page web peut montrer de
plus, et qui manquait — la page se contentait de quatre nombres dont un,
« AO en Ile-de-France », vaut toujours le total puisque la collecte est
filtree sur l'Ile-de-France.

Principe de construction : ne montrer que ce qui est reellement rempli. Le
suivi commercial (statut de contact, RDV) est vide dans la base ; un entonnoir
commercial n'afficherait que des zeros. L'entonnoir de collecte, lui, est
entierement renseigne par le journal des passages.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import pandas as pd

PALIERS_ECHEANCE = (7, 15, 30)
SEMAINES_AFFICHEES = 8


def _jours(valeur, aujourd_hui: date) -> int | None:
    texte = str(valeur or "").strip()[:10]
    if not texte:
        return None
    try:
        return (date.fromisoformat(texte) - aujourd_hui).days
    except ValueError:
        return None


def echeances(df: pd.DataFrame, aujourd_hui: date | None = None) -> dict[str, int]:
    """Combien de marches arrivent a echeance, par palier.

    Les paliers sont cumulatifs — « sous 15 jours » contient « sous 7 jours » —
    parce que c'est ainsi qu'on decide : ce qui tombe dans la quinzaine est ce
    qu'il faut regarder, y compris l'urgent.
    """
    aujourd_hui = aujourd_hui or date.today()
    vide = {f"sous_{p}j": 0 for p in PALIERS_ECHEANCE} | {"expirees": 0, "ouvertes": 0}
    if df is None or df.empty or "date_limite" not in df.columns:
        return vide

    restants = [_jours(v, aujourd_hui) for v in df["date_limite"]]
    connus = [j for j in restants if j is not None]
    resultat = {f"sous_{p}j": sum(1 for j in connus if 0 <= j <= p) for p in PALIERS_ECHEANCE}
    resultat["expirees"] = sum(1 for j in connus if j < 0)
    resultat["ouvertes"] = sum(1 for j in connus if j >= 0)
    return resultat


def attente_de_tri(df: pd.DataFrame) -> int:
    """AO collectes mais jamais juges : c'est du travail en attente, pas un etat."""
    if df is None or df.empty or "verdict_tri" not in df.columns:
        return 0
    return int((df["verdict_tri"].fillna("").astype(str).str.strip() == "").sum())


def flux_hebdomadaire(df: pd.DataFrame, semaines: int = SEMAINES_AFFICHEES) -> pd.DataFrame:
    """Nombre d'AO publies par semaine, de la plus ancienne a la plus recente.

    Ordre chronologique et non decroissant : un graphique se lit de gauche a
    droite dans le sens du temps.
    """
    colonnes = ["semaine", "appels d'offres"]
    if df is None or df.empty or "date_publication" not in df.columns:
        return pd.DataFrame(columns=colonnes)
    dates = pd.to_datetime(df["date_publication"], errors="coerce").dropna()
    if dates.empty:
        return pd.DataFrame(columns=colonnes)
    par_semaine = dates.dt.strftime("%Y-S%V").value_counts().sort_index()
    recentes = par_semaine.tail(semaines)
    return pd.DataFrame({colonnes[0]: recentes.index, colonnes[1]: recentes.values})


def _details(brut: Any) -> dict:
    """Le champ `details` du journal est du JSON pour BOAMP, du texte libre ailleurs."""
    if isinstance(brut, dict):
        return brut
    try:
        charge = json.loads(str(brut or ""))
    except (ValueError, TypeError):
        return {}
    return charge if isinstance(charge, dict) else {}


def entonnoir_collecte(logs: pd.DataFrame) -> dict[str, Any]:
    """Dernier passage de collecte : examines, retenus, et pourquoi on ecarte.

    C'est le seul entonnoir que la base permette de tracer honnetement, et il
    repond a la vraie question : le filtre laisse-t-il passer ce qu'il faut ?
    """
    vide = {"source": "", "quand": "", "examines": 0, "retenus": 0,
            "enregistres": 0, "raisons": []}
    if logs is None or logs.empty:
        return vide

    travail = logs.copy()
    if "run_at" in travail.columns:
        travail = travail.sort_values("run_at", ascending=False)
    # On cherche le dernier passage qui a reellement examine un volume : un
    # passage Maximilien ne rapporte que ses quinze consultations et masquerait
    # le tri de fond.
    detaillees = [l for _, l in travail.iterrows() if _details(l.get("details")).get("skipped_reasons")]
    ligne = detaillees[0] if detaillees else travail.iloc[0]
    details = _details(ligne.get("details"))

    raisons = sorted(details.get("skipped_reasons", {}).items(),
                     key=lambda couple: couple[1], reverse=True)
    quand = str(ligne.get("run_at") or "")[:16].replace("T", " ")
    return {
        "source": str(ligne.get("source") or ""),
        "quand": quand,
        "examines": int(ligne.get("fetched") or 0),
        "retenus": int(ligne.get("kept") or 0),
        "enregistres": int(ligne.get("inserted_or_updated") or 0),
        "raisons": [{"motif": m, "nombre": int(n)} for m, n in raisons],
    }


def derniers_passages(logs: pd.DataFrame, nombre: int = 5) -> pd.DataFrame:
    """Historique court des collectes, pour voir si la veille tourne encore."""
    colonnes = ["quand", "source", "examinés", "retenus", "nouveaux"]
    if logs is None or logs.empty:
        return pd.DataFrame(columns=colonnes)
    travail = logs.sort_values("run_at", ascending=False).head(nombre)
    return pd.DataFrame({
        "quand": [str(v)[:16].replace("T", " ") for v in travail["run_at"]],
        "source": travail["source"].astype(str).values,
        "examinés": travail["fetched"].fillna(0).astype(int).values,
        "retenus": travail["kept"].fillna(0).astype(int).values,
        "nouveaux": travail["inserted_or_updated"].fillna(0).astype(int).values,
    })


def repartition(df: pd.DataFrame, colonne: str, limite: int = 8) -> pd.DataFrame:
    """Repartition des AO sur un axe, du plus fourni au moins fourni."""
    entetes = [colonne, "appels d'offres"]
    if df is None or df.empty or colonne not in df.columns:
        return pd.DataFrame(columns=entetes)
    valeurs = df[colonne].fillna("").astype(str).str.strip()
    valeurs = valeurs[valeurs != ""]
    if valeurs.empty:
        return pd.DataFrame(columns=entetes)
    comptes = valeurs.value_counts().head(limite)
    return pd.DataFrame({entetes[0]: comptes.index, entetes[1]: comptes.values})


def qualite_donnees(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Points a reprendre a la main, chacun avec son volume.

    Presente comme une liste de taches et non comme des indicateurs : ce sont
    des choses a faire, pas des chiffres a contempler.
    """
    if df is None or df.empty:
        return []
    total = len(df)

    def compte(masque) -> int:
        return int(masque.sum())

    colonne = df.get("budget_statut", pd.Series([""] * total))
    budget = compte(colonne.fillna("").astype(str) == "A_VERIFIER_BUDGET")
    dce = compte(df.get("statut_extraction", pd.Series([""] * total))
                 .fillna("").astype(str) == "DCE_A_TELECHARGER")
    email = df.get("email", pd.Series([""] * total)).fillna("").astype(str).str.strip()
    tel = df.get("telephone", pd.Series([""] * total)).fillna("").astype(str).str.strip()
    sans_contact = compte((email == "") & (tel == ""))

    lignes = [
        {"point": "Budget à vérifier", "nombre": budget,
         "detail": "montant non affiché dans l'avis"},
        {"point": "Sans email ni téléphone", "nombre": sans_contact,
         "detail": "contact à retrouver avant de démarcher"},
        {"point": "Dossier de consultation à récupérer", "nombre": dce,
         "detail": "pièces du marché non téléchargées"},
        {"point": "En attente de tri", "nombre": attente_de_tri(df),
         "detail": "jamais jugés pertinents ou non"},
    ]
    return [l for l in lignes if l["nombre"] > 0]


def age_de_la_base(logs: pd.DataFrame, maintenant: datetime | None = None) -> str:
    """Depuis quand la derniere collecte a-t-elle tourne, en clair."""
    if logs is None or logs.empty or "run_at" not in logs.columns:
        return "jamais"
    valeurs = logs["run_at"].dropna()
    if valeurs.empty:
        return "jamais"
    dernier = pd.to_datetime(valeurs, errors="coerce", utc=True).max()
    if pd.isna(dernier):
        return "jamais"
    maintenant = maintenant or datetime.now(dernier.tzinfo)
    heures = (maintenant - dernier.to_pydatetime()).total_seconds() / 3600
    if heures < 1:
        return "il y a moins d'une heure"
    if heures < 24:
        return f"il y a {int(heures)} h"
    return f"il y a {int(heures // 24)} j"
