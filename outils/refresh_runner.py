from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# cle -> (fichier de sortie relatif, arguments apres l'interpreteur)
CIBLES = {
    "ao": ("output/AO_CHRUTH.xlsm", ["ao_weekly_update.py"]),
    "prospects_vite": ("output/Base_Prospects_CHRUTH.xlsm", ["chruth_pipeline_master.py"]),
    "prospects_complet": ("output/Base_Prospects_CHRUTH.xlsm",
                          ["chruth_pipeline_master.py", "--collect", "--scope", "france"]),
}


def resoudre(cible: str, mode: str | None):
    cle = cible if cible != "prospects" else f"prospects_{mode or 'vite'}"
    if cle not in CIBLES:
        raise SystemExit(f"Cible inconnue : {cle}")
    rel, args = CIBLES[cle]
    commande = [sys.executable, str(BASE / args[0]), *args[1:]]
    # Pour AO, le 2e argument (mode) est le nom de region a mettre a jour (optionnel).
    if cible == "ao" and mode and mode.strip():
        commande += ["--regions", mode]
    return BASE / rel, commande


def attendre_deverrouillage(fichier, timeout: int = 60) -> bool:
    f = Path(fichier)
    if not f.exists():
        return True
    for _ in range(timeout):
        try:
            with open(f, "r+b"):
                return True
        except PermissionError:
            time.sleep(1)
    return False


def main() -> int:
    cible = sys.argv[1] if len(sys.argv) > 1 else "ao"
    mode = sys.argv[2] if len(sys.argv) > 2 else None
    fichier, commande = resoudre(cible, mode)
    print(f"[refresh] cible={cible} mode={mode} -> {fichier.name}")
    print("[refresh] attente de la fermeture du fichier Excel...")
    if not attendre_deverrouillage(fichier):
        print("[refresh] Fichier toujours verrouille. Ferme Excel puis relance.")
        return 1
    code = subprocess.call(commande, cwd=str(BASE))
    if code == 0 and fichier.exists():
        try:
            os.startfile(str(fichier))  # noqa: S606 (Windows : rouvre le fichier)
        except Exception:
            pass
    return code


if __name__ == "__main__":
    raise SystemExit(main())
