"""Lancement sûr du pipeline de collecte depuis Streamlit."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


MODES = {"ao", "prospects", "complete"}
SCOPES = {"test", "france", "region", "departements"}


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


def fin_journal(path: Path, lignes: int = 100) -> str:
    if not path.is_file():
        return "Journal en attente."
    contenu = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(contenu[-lignes:]) or "Journal vide."
