"""Genere un classeur Excel INTERACTIF du modele financier previsionnel CHRUTH :
output/Modele_Financier_CHRUTH.xlsx. Les cellules jaunes sont editables, le reste
se recalcule (formules Excel). Leger et rapide a ouvrir (independant du cockpit).

Usage : python outils/generer_modele_financier.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import Workbook  # noqa: E402

import previsions  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "output" / "Modele_Financier_CHRUTH.xlsx"


def main() -> int:
    import rentabilite_marche
    wb = Workbook()
    # Feuille 1 : previsionnel global (entonnoir) — conserve.
    ws = wb.active
    ws.title = "Previsionnel_Global"
    previsions.ecrire_feuille(ws)
    # Feuilles 2-5 : simulateur de rentabilite par marche (demande Sonia 2026-06-23).
    rentabilite_marche.ecrire_feuilles(wb)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"Modele financier interactif : {OUT}")
    print("  Onglets : Previsionnel_Global, Charges_Fixes, Hypotheses_Marche, "
          "Marches, Synthese_Rentabilite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
