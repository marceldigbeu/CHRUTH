"""Lancement sûr du pipeline de collecte depuis Streamlit."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


MODES = {"ao", "prospects", "complete"}
SCOPES = {"test", "france", "region", "departements"}


@dataclass(frozen=True)
class ProgressionCollecte:
    pourcentage: int
    etape: str
    details: str = ""


ETAPES = {
    "ao": [
        ("Collecte lancée depuis Streamlit", 5, "Préparation de la collecte"),
        ("[collecte] ON", 10, "Connexion aux sources"),
        ("CHRUTH - Mise a jour appels d'offres", 15, "Préparation des avis"),
        ("=== 1. Collecte BOAMP ===", 25, "Analyse des avis BOAMP"),
        ("Collecte BOAMP CHRUTH terminee", 55, "Sélection des appels d'offres"),
        ("=== 2. Traitement DCE", 62, "Vérification des dossiers de consultation"),
        ("Traitement DCE termine", 72, "Dossiers de consultation vérifiés"),
        ("=== 3. Export Excel AO", 78, "Mise à jour du tableur"),
        ("Excel AO exporte", 88, "Tableur mis à jour"),
        ("=== 4. Publication", 92, "Préparation des résultats"),
        ("Mise a jour AO terminee", 96, "Finalisation"),
        ("Manifest JSON", 98, "Contrôle final"),
        ("[OK] Pipeline CHRUTH terminee", 100, "Collecte terminée"),
    ],
    "prospects": [
        ("Collecte lancée depuis Streamlit", 5, "Préparation de la collecte"),
        ("[collecte] ON", 10, "Connexion aux sources"),
        ("=== 2. Prospects", 15, "Préparation des prospects"),
        ("=== Collecte API ===", 25, "Collecte des entreprises"),
        ("=== Nettoyage + classification ===", 42, "Nettoyage et classement"),
        ("=== Enrichissement FINESS ===", 52, "Enrichissement des données"),
        ("=== Scoring + export Excel ===", 64, "Calcul des priorités"),
        ("Carte prospects generee", 74, "Mise à jour de la carte"),
        ("Controle qualite exporte", 80, "Contrôle de la qualité"),
        ("KPI exportes", 85, "Calcul des indicateurs"),
        ("CRM cree", 90, "Mise à jour du suivi commercial"),
        ("Notice Notion", 95, "Préparation des livrables"),
        ("Manifest JSON", 98, "Contrôle final"),
        ("[OK] Pipeline CHRUTH terminee", 100, "Collecte terminée"),
    ],
    "complete": [
        ("Collecte lancée depuis Streamlit", 3, "Préparation de la collecte"),
        ("=== 1. Collecte BOAMP ===", 10, "Analyse des avis BOAMP"),
        ("Collecte BOAMP CHRUTH terminee", 28, "Sélection des appels d'offres"),
        ("Traitement DCE termine", 36, "Dossiers de consultation vérifiés"),
        ("Excel AO exporte", 43, "Tableur des appels d'offres mis à jour"),
        ("=== 2. Prospects", 48, "Préparation des prospects"),
        ("=== Collecte API ===", 55, "Collecte des entreprises"),
        ("=== Nettoyage + classification ===", 65, "Nettoyage et classement"),
        ("=== Enrichissement FINESS ===", 72, "Enrichissement des données"),
        ("=== Scoring + export Excel ===", 80, "Calcul des priorités"),
        ("Carte prospects generee", 86, "Mise à jour de la carte"),
        ("CRM cree", 91, "Mise à jour du suivi commercial"),
        ("Notice Notion", 95, "Préparation des livrables"),
        ("Manifest JSON", 98, "Contrôle final"),
        ("[OK] Pipeline CHRUTH terminee", 100, "Collecte terminée"),
    ],
}


def construire_commande(
    racine: Path,
    mode: str,
    *,
    scope: str = "region",
    regions: str = "Île-de-France",
    departements: str = "",
) -> list[str]:
    """Construit la commande sans shell : les champs utilisateur restent des arguments."""
    if mode not in MODES:
        raise ValueError(f"Mode de collecte inconnu : {mode}")
    if scope not in SCOPES:
        raise ValueError(f"Périmètre inconnu : {scope}")

    script = racine / "CHRUTH_PIPELINE_UNIQUE.py"
    if not script.is_file():
        raise FileNotFoundError(script)

    commande = [sys.executable, "-u", str(script)]
    collecte_ao = mode in {"ao", "complete"}
    collecte_prospects = mode in {"prospects", "complete"}

    commande.append("--collect-ao" if collecte_ao else "--skip-ao")
    if collecte_prospects:
        commande.extend(["--collect-prospects", "--scope", scope])
    else:
        commande.append("--skip-prospects")
    commande.append("--skip-finance")
    commande.append("--leave-collecte-on")

    regions = regions.strip()
    departements = departements.strip()
    if regions and (collecte_ao or (collecte_prospects and scope == "region")):
        commande.extend(["--regions", regions])
    if collecte_prospects and scope == "departements" and departements:
        commande.extend(["--departements", departements])
    return commande


def classeurs_concernes(output: Path, mode: str) -> list[Path]:
    fichiers: list[Path] = []
    if mode in {"ao", "complete"}:
        fichiers.append(output / "AO_CHRUTH.xlsm")
    if mode in {"prospects", "complete"}:
        fichiers.append(output / "Base_Prospects_CHRUTH.xlsm")
    return fichiers


def classeurs_verrouilles(output: Path, mode: str) -> list[Path]:
    return [path for path in classeurs_concernes(output, mode)
            if path.with_name("~$" + path.name).exists()]


def lancer(racine: Path, commande: list[str]) -> tuple[subprocess.Popen, Path]:
    """Lance la collecte en arrière-plan et renvoie le processus et son journal."""
    logs = racine / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    journal = logs / f"streamlit_collecte_{horodatage}.log"
    flux = journal.open("w", encoding="utf-8")
    flux.write("Collecte lancée depuis Streamlit\n")
    flux.write("Commande : " + " ".join(commande) + "\n\n")
    flux.flush()
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    environnement = os.environ.copy()
    environnement["PYTHONUNBUFFERED"] = "1"
    try:
        processus = subprocess.Popen(
            commande,
            cwd=str(racine),
            stdout=flux,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
            env=environnement,
        )
    finally:
        flux.close()
    return processus, journal


def progression_depuis_texte(
    texte: str, mode: str = "ao", code_retour: int | None = None
) -> ProgressionCollecte:
    """Traduit le journal technique en progression compréhensible."""
    etapes = ETAPES.get(mode, ETAPES["ao"])
    pourcentage = 2
    etape = "Démarrage"
    for marqueur, valeur, libelle in etapes:
        if marqueur in texte and valeur >= pourcentage:
            pourcentage, etape = valeur, libelle

    analyses = re.search(r"^fetched:\s*(\d+)", texte, re.MULTILINE)
    retenus = re.search(r"^kept:\s*(\d+)", texte, re.MULTILINE)
    details = ""
    if analyses and retenus:
        details = (
            f"{int(retenus.group(1))} appels d'offres retenus "
            f"sur {int(analyses.group(1))} avis analysés."
        )

    if code_retour == 0:
        return ProgressionCollecte(100, "Collecte terminée", details)
    if code_retour is not None:
        return ProgressionCollecte(min(pourcentage, 99), "Collecte interrompue", details)
    return ProgressionCollecte(pourcentage, etape, details)


def progression_journal(
    path: Path | None, mode: str = "ao", code_retour: int | None = None
) -> ProgressionCollecte:
    if path is None or not path.is_file():
        return progression_depuis_texte("", mode, code_retour)
    texte = path.read_text(encoding="utf-8", errors="replace")
    return progression_depuis_texte(texte, mode, code_retour)


def fin_journal(path: Path, lignes: int = 100) -> str:
    """Conservé pour les outils de diagnostic, jamais affiché dans l'interface normale."""
    if not path.is_file():
        return "Journal en attente."
    contenu = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(contenu[-lignes:]) or "Journal vide."
