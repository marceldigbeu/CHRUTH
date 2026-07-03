"""Génère le notebook de pilotage unique CHRUTH.

Le notebook ne remplace pas les modules métier : il sert d'interface simple
pour lancer CHRUTH_PIPELINE_UNIQUE.py avec des interrupteurs lisibles.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nb_build import code, md, save_notebook  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "CHRUTH_Pipeline_Unique.ipynb"


def build(out_path: str | Path | None = None) -> Path:
    cells = [
        md(
            "# CHRUTH - Pipeline unique\n\n"
            "Ce notebook est le point d'entrée principal pour générer les livrables CHRUTH.\n\n"
            "Il pilote le moteur `CHRUTH_PIPELINE_UNIQUE.py`, qui régénère :\n"
            "- le cockpit appels d'offres `output/AO_CHRUTH.xlsm` ;\n"
            "- la base prospects `output/Base_Prospects_CHRUTH.xlsm` ;\n"
            "- la carte `output/Carte_Prospects_CHRUTH.html` ;\n"
            "- le CRM, les KPI, les exports Notion/Power BI ;\n"
            "- le modèle financier ;\n"
            "- les documents de mission et prompts ;\n"
            "- un dossier portable si demandé.\n\n"
            "Par défaut, la collecte réseau est désactivée : le notebook retraite les données locales.",
            "intro",
        ),
        md(
            "## 1. Installer les dépendances\n\n"
            "À exécuter une fois sur un nouveau poste. Si tout est déjà installé, cette cellule ne change rien d'important.",
            "deps-md",
        ),
        code(
            "%pip install -q -r requirements.txt",
            "deps-code",
        ),
        md(
            "## 2. Régler les options\n\n"
            "- `COLLECTE_AO` : recollecte BOAMP/DCE.\n"
            "- `COLLECTE_PROSPECTS` : recollecte API Entreprises, potentiellement longue.\n"
            "- `GENERER_MESSAGES` : active la génération de brouillons par segment si un LLM est disponible.\n"
            "- `CREER_PACK` : copie le dossier en version portable prête à envoyer.\n"
            "- `SCOPE_PROSPECTS` : `france`, `region`, `departements` ou `test`.",
            "options-md",
        ),
        code(
            "COLLECTE_AO = False\n"
            "COLLECTE_PROSPECTS = False\n"
            "GENERER_MESSAGES = False\n"
            "CREER_PACK = True\n"
            "\n"
            "SCOPE_PROSPECTS = \"france\"\n"
            "REGIONS = \"\"\n"
            "DEPARTEMENTS = \"69\"\n"
            "\n"
            "SKIP_AO = False\n"
            "SKIP_PROSPECTS = False\n"
            "SKIP_FINANCE = False",
            "options-code",
        ),
        md(
            "## 3. Lancer toute la pipeline\n\n"
            "Ferme les fichiers Excel ouverts dans `output/` avant de lancer si tu veux que les classeurs soient réécrits.",
            "run-md",
        ),
        code(
            "import subprocess\n"
            "import sys\n"
            "from pathlib import Path\n"
            "\n"
            "cmd = [sys.executable, \"CHRUTH_PIPELINE_UNIQUE.py\"]\n"
            "if COLLECTE_AO:\n"
            "    cmd.append(\"--collect-ao\")\n"
            "if COLLECTE_PROSPECTS:\n"
            "    cmd.extend([\"--collect-prospects\", \"--scope\", SCOPE_PROSPECTS])\n"
            "    if SCOPE_PROSPECTS == \"region\" and REGIONS.strip():\n"
            "        cmd.extend([\"--regions\", REGIONS])\n"
            "    if SCOPE_PROSPECTS == \"departements\":\n"
            "        cmd.extend([\"--departements\", DEPARTEMENTS])\n"
            "elif REGIONS.strip():\n"
            "    cmd.extend([\"--regions\", REGIONS])\n"
            "if SKIP_AO:\n"
            "    cmd.append(\"--skip-ao\")\n"
            "if SKIP_PROSPECTS:\n"
            "    cmd.append(\"--skip-prospects\")\n"
            "if SKIP_FINANCE:\n"
            "    cmd.append(\"--skip-finance\")\n"
            "if GENERER_MESSAGES:\n"
            "    cmd.append(\"--generer-messages\")\n"
            "if CREER_PACK:\n"
            "    cmd.append(\"--pack\")\n"
            "\n"
            "print(\"Commande:\", \" \".join(cmd))\n"
            "result = subprocess.run(cmd, cwd=Path.cwd(), text=True)\n"
            "if result.returncode != 0:\n"
            "    raise SystemExit(result.returncode)",
            "run-code",
        ),
        md(
            "## 4. Contrôler les sorties\n\n"
            "Cette cellule liste les livrables principaux attendus.",
            "check-md",
        ),
        code(
            "from pathlib import Path\n"
            "\n"
            "attendus = [\n"
            "    \"output/AO_CHRUTH.xlsm\",\n"
            "    \"output/Base_Prospects_CHRUTH.xlsm\",\n"
            "    \"output/Carte_Prospects_CHRUTH.html\",\n"
            "    \"output/CRM_CHRUTH_CHAUDE.xlsx\",\n"
            "    \"output/Prospects_CHAUDS_messages.xlsx\",\n"
            "    \"output/Modele_Financier_CHRUTH.xlsx\",\n"
            "    \"output/MANIFEST_CHRUTH.json\",\n"
            "    \"output/LIRE_MOI_LIVRABLES.md\",\n"
            "    \"docs/MISSION_CHRUTH.md\",\n"
            "    \"prompts/PROMPTS_CHRUTH.md\",\n"
            "]\n"
            "for item in attendus:\n"
            "    path = Path(item)\n"
            "    print((\"OK   \" if path.exists() else \"MISS \") + item)",
            "check-code",
        ),
        md(
            "## 5. Lecture rapide\n\n"
            "- `output/LIRE_MOI_LIVRABLES.md` explique les fichiers générés.\n"
            "- `docs/MISSION_CHRUTH.md` relie les sorties aux missions de la fiche de poste.\n"
            "- `prompts/PROMPTS_CHRUTH.md` regroupe les prompts utiles.\n"
            "- Le dossier portable est créé dans `Downloads/CHRUTH_LIVRAISON_UNIFIEE_YYYYMMDD_HHMM` si `CREER_PACK=True`.",
            "end",
        ),
    ]
    return save_notebook(cells, out_path or OUT)


if __name__ == "__main__":
    print(build())
