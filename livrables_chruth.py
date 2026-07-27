"""Resolution des livrables utilises par la plateforme Streamlit."""
from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parent
LIVRAISON_NO_CODE = Path.home() / "Downloads" / "CHRUTH_LIVRAISON_NO_CODE"

FICHIERS_IMPORTANTS = {
    "Cockpit appels d'offres": "AO_CHRUTH.xlsm",
    "Base prospects": "Base_Prospects_CHRUTH.xlsm",
    "Carte prospects": "Carte_Prospects_CHRUTH.html",
    "CRM prospects chauds": "CRM_CHRUTH_CHAUDE.xlsx",
    "Messages prospects": "Prospects_CHAUDS_messages.xlsx",
    "Modele financier": "Modele_Financier_CHRUTH.xlsx",
    "Prospects enrichis": "prospects_enrichis.csv",
    "Prospects nettoyes": "prospects_nettoyes.csv",
    "Indicateurs": "KPI_CHRUTH.csv",
    "Controle qualite": "CONTROLE_QUALITE_CHRUTH.csv",
    "Manifeste": "MANIFEST_CHRUTH.json",
}


def dossier_output() -> Path:
    """Dossier reel : variable explicite, livraison locale, puis repli du depot."""
    explicite = os.environ.get("CHRUTH_OUTPUT_DIR", "").strip()
    if explicite:
        return Path(explicite).expanduser().resolve()
    local = LIVRAISON_NO_CODE / "output"
    if (local / "AO_CHRUTH.xlsm").exists():
        return local
    return RACINE / "output"


def fichier(nom: str) -> Path:
    return dossier_output() / nom


def racine_livraison() -> Path:
    """Racine du projet qui possede le dossier output selectionne."""
    return dossier_output().parent


def verrou_excel(path: Path) -> Path:
    return path.with_name("~$" + path.name)


def informations(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"existe": False, "taille": 0, "modifie": "", "chemin": str(path)}
    stat = path.stat()
    return {
        "existe": True,
        "taille": stat.st_size,
        "modifie": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M"),
        "chemin": str(path),
    }


def taille_humaine(octets: int) -> str:
    valeur = float(octets)
    for unite in ("o", "Ko", "Mo", "Go"):
        if valeur < 1024 or unite == "Go":
            return f"{valeur:.0f} {unite}" if unite == "o" else f"{valeur:.1f} {unite}"
        valeur /= 1024
    return f"{valeur:.1f} Go"


def empreinte(path: Path) -> str:
    """SHA-256 compact pour verifier que Streamlit lit bien la bonne version."""
    h = hashlib.sha256()
    with path.open("rb") as flux:
        for bloc in iter(lambda: flux.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()
