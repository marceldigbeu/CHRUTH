"""Publication des livrables CHRUTH vers un dossier partage (OneDrive/SharePoint
synchronise localement, Google Drive Desktop, ou partage reseau UNC).

La pipeline copie simplement les fichiers dans ce dossier ; le service de
synchronisation (OneDrive, etc.) se charge du cloud. Aucun identifiant requis.

Destination : argument `dest` > variable d'environnement CHRUTH_DOSSIER_PARTAGE
> constante DOSSIER_PARTAGE de ao_config. Si rien n'est defini, l'etape est
ignoree (best-effort : ne casse jamais la pipeline).
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from ao_config import (
    AO_OUTPUT_XLSM,
    DOSSIER_PARTAGE,
    OUTPUT_DIR,
)


def dossier_partage(dest: str | os.PathLike | None = None) -> Path | None:
    """Resout le dossier de destination (None si non configure)."""
    val = str(dest or os.environ.get("CHRUTH_DOSSIER_PARTAGE") or DOSSIER_PARTAGE or "").strip()
    return Path(val) if val else None


def publier(fichiers: list[Path] | None = None, dest: str | os.PathLike | None = None) -> list[Path]:
    """Copie les livrables dans le dossier partage. Retourne les fichiers copies."""
    cible_dir = dossier_partage(dest)
    if cible_dir is None:
        print("[PARTAGE] Aucun dossier partage configure -> etape ignoree.")
        return []
    if fichiers is None:
        fichiers = [AO_OUTPUT_XLSM]
    try:
        cible_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"[PARTAGE] Dossier inaccessible ({cible_dir}) : {exc} -> etape ignoree.")
        return []
    copies: list[Path] = []
    for f in fichiers:
        f = Path(f)
        if not f.exists():
            print(f"[PARTAGE] Introuvable, ignore : {f.name}")
            continue
        try:
            cible = cible_dir / f.name
            shutil.copy2(f, cible)
            copies.append(cible)
            print(f"[PARTAGE] Copie -> {cible}")
        except OSError as exc:
            print(f"[PARTAGE] Echec copie {f.name} : {exc}")
    return copies


def livrables_disponibles() -> list[Path]:
    """Tous les livrables presents dans output/ (AO + prospects + carte)."""
    candidats = [AO_OUTPUT_XLSM, OUTPUT_DIR / "Carte_Prospects_CHRUTH.html"]
    candidats += sorted(OUTPUT_DIR.glob("Base_Prospects_CHRUTH_France_*.xlsx"))
    return [c for c in candidats if Path(c).exists()]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    publier(fichiers=livrables_disponibles() or None)
    return 0  # best-effort : ne fait jamais echouer la pipeline


if __name__ == "__main__":
    raise SystemExit(main())
