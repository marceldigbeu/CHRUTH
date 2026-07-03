"""Genere CHRUTH_Messages_Prospects.ipynb : interface de generation de messages par segment.

Le notebook ne remplace pas prospect_messages.py : il l'importe pour generer le
template d'un segment (categorie x priorite) et le rendre sur un prospect exemple.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nb_build import code, md, save_notebook  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "CHRUTH_Messages_Prospects.ipynb"


def build(out_path: str | Path | None = None) -> Path:
    cells = [
        md(
            "# CHRUTH - Messages prospects (par segment)\n\n"
            "Interface pour `prospect_messages.py`. Génère un **email + un script d'appel**\n"
            "pour un **segment** (catégorie × priorité), rendu sur un prospect exemple.\n\n"
            "La **fiche CHRUTH** (`config_chruth/fiche_chruth.md`) et le **moteur auto**\n"
            "(clé cloud / Ollama / repli) rendent le message précis. Brouillons seulement.",
            "intro",
        ),
        md("## 1. Setup", "setup-md"),
        code(
            "import sys, pathlib\n"
            "sys.path.insert(0, str(pathlib.Path.cwd()))\n"
            "import prospect_messages as pm, llm_client\n"
            "print('Moteur IA   :', llm_client.moteur_auto() or 'aucun -> brouillon deterministe')\n"
            "print('Fiche CHRUTH:', 'chargee' if pm.fiche_chruth() else 'VIDE (remplis config_chruth/fiche_chruth.md)')",
            "setup-code",
        ),
        md(
            "## 2. Choisir le segment et un prospect exemple\n\n"
            "Catégories : ex. `PRIV_BUREAU`, `SANTE`, `COMMERCE`… Priorités : `CHAUDE` / `TIEDE`.",
            "options-md",
        ),
        code(
            "CATEGORIE = 'PRIV_BUREAU'\n"
            "PRIORITE = 'CHAUDE'\n"
            "\n"
            "DENOMINATION = 'CABINET DENTAIRE DU MARAIS'\n"
            "VILLE = 'PARIS 03'\n"
            "EFFECTIF = '10 a 19'",
            "options-code",
        ),
        md("## 3. Générer le message", "gen-md"),
        code(
            "templates = pm.generer_templates([(CATEGORIE, PRIORITE)], refresh=True)\n"
            "tpl = templates[f'{CATEGORIE}|{PRIORITE}']\n"
            "ligne = {'denomination': DENOMINATION, 'libelle_commune': VILLE, 'effectif_label': EFFECTIF}\n"
            "print('Source :', tpl.get('source', ''), '(ia = redige par le modele ; defaut = brouillon type)')\n"
            "print('\\n' + '=' * 60 + '\\nEMAIL\\n' + '=' * 60)\n"
            "print(pm.rendre(tpl['email'], ligne))\n"
            "print('\\n' + '=' * 60 + \"\\nSCRIPT D'APPEL\\n\" + '=' * 60)\n"
            "print(pm.rendre(tpl['script'], ligne))",
            "gen-code",
        ),
    ]
    return save_notebook(cells, out_path or OUT)


if __name__ == "__main__":
    print(build())
