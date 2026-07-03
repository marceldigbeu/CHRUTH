"""Pipeline unique CHRUTH.

Point d'entree stable pour generer tous les livrables du dossier output :
- cockpit appels d'offres AO_CHRUTH.xlsm ;
- base prospects, carte, KPI, controle qualite, CRM, exports Notion/Power BI ;
- modele financier autonome ;
- documentation missions/prompts ;
- pack portable a envoyer.

Usage courant :
    python CHRUTH_PIPELINE_UNIQUE.py

Usage avec pack a envoyer :
    python CHRUTH_PIPELINE_UNIQUE.py --pack

Recollecte internet optionnelle :
    python CHRUTH_PIPELINE_UNIQUE.py --collect-ao --collect-prospects
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
LOG_DIR = ROOT / "logs"
DOCS_DIR = ROOT / "docs"
PROMPTS_DIR = ROOT / "prompts"
SOURCE_PDF = Path(__file__).resolve().parent / "docs" / "source" / "Fiche de poste CHRUTH.pdf"


MISSION_OUTPUTS = {
    "1_data_foundation": [
        "output/Base_Prospects_CHRUTH.xlsm",
        "output/prospects_nettoyes.csv",
        "output/prospects_enrichis.csv",
        "output/Carte_Prospects_CHRUTH.html",
    ],
    "2_segmentation_scoring": [
        "output/KPI_CHRUTH.csv",
        "output/CONTROLE_QUALITE_CHRUTH.csv",
        "output/Base_Prospects_CHRUTH.xlsm",
        "output/powerbi_sources/",
    ],
    "3_ai_driven_sales": [
        "output/Prospects_CHAUDS_messages.xlsx",
        "output/segments_messages.json",
        "output/_message_ao.txt",
        "prompts/PROMPTS_CHRUTH.md",
    ],
    "4_crm_rentabilite": [
        "output/CRM_CHRUTH_CHAUDE.xlsx",
        "output/Modele_Financier_CHRUTH.xlsx",
        "output/notion_import_chruth/",
    ],
    "bonus_appels_offres": [
        "output/AO_CHRUTH.xlsm",
    ],
}


def run(command: list[str], label: str, log_file) -> int:
    print(f"\n=== {label} ===")
    print("Commande :", " ".join(command))
    log_file.write(f"\n=== {label} ===\n")
    log_file.write(" ".join(command) + "\n")
    log_file.flush()
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="")
        log_file.write(line)
        log_file.flush()
    code = process.wait()
    log_file.write(f"\nCode retour : {code}\n")
    if code != 0:
        raise RuntimeError(f"Etape echouee : {label} (code {code})")
    return code


def set_collecte(active: bool) -> None:
    from ao_config import set_collecte

    set_collecte(active)
    print(f"[collecte] {'ON' if active else 'OFF'}")


def write_reference_docs() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "MISSION_CHRUTH.md").write_text(MISSION_DOC, encoding="utf-8")
    (PROMPTS_DIR / "PROMPTS_CHRUTH.md").write_text(PROMPTS_DOC, encoding="utf-8")


def generate_manifest(log_path: Path) -> Path:
    rows = []
    for path in sorted(OUTPUT_DIR.rglob("*")) if OUTPUT_DIR.exists() else []:
        if path.is_file():
            rows.append({
                "path": str(path.relative_to(ROOT)),
                "size_bytes": path.stat().st_size,
                "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
            })
    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "root": str(ROOT),
        "log": str(log_path.relative_to(ROOT)),
        "missions": MISSION_OUTPUTS,
        "outputs": rows,
    }
    path = OUTPUT_DIR / "MANIFEST_CHRUTH.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_human_manifest() -> Path:
    lines = [
        "# Livrables CHRUTH",
        "",
        "Ce dossier de sortie est genere par `CHRUTH_PIPELINE_UNIQUE.py`.",
        "",
        "## Correspondance missions -> livrables",
    ]
    for mission, files in MISSION_OUTPUTS.items():
        lines.append(f"### {mission}")
        for file in files:
            lines.append(f"- `{file}`")
        lines.append("")
    lines.extend([
        "## Lancement",
        "",
        "```bat",
        "python CHRUTH_PIPELINE_UNIQUE.py",
        "```",
        "",
        "Par defaut, la collecte reseau est desactivee. Pour recollecter :",
        "",
        "```bat",
        "python CHRUTH_PIPELINE_UNIQUE.py --collect-ao --collect-prospects",
        "```",
    ])
    path = OUTPUT_DIR / "LIRE_MOI_LIVRABLES.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "logs",
    "tmp",
    "venv",
    ".venv",
}
EXCLUDED_FILES = {
    "alertes_secrets.json",
    "destinataires.txt",
}


def should_skip(path: Path, target: Path) -> bool:
    try:
        path.resolve().relative_to(target.resolve())
        return True
    except ValueError:
        pass
    if path.name in EXCLUDED_DIRS or path.name in EXCLUDED_FILES:
        return True
    if path.name.startswith("~$"):
        return True
    if path.suffix.lower() in {".pyc", ".pyo"}:
        return True
    return False


def copy_tree_filtered(src: Path, dst: Path, target_root: Path) -> None:
    if should_skip(src, target_root):
        return
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        for child in src.iterdir():
            copy_tree_filtered(child, dst / child.name, target_root)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def package_portable(target: Path | None = None) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    target = target or (ROOT.parent / f"CHRUTH_LIVRAISON_UNIFIEE_{stamp}")
    target.mkdir(parents=True, exist_ok=True)

    for child in ROOT.iterdir():
        copy_tree_filtered(child, target / child.name, target)

    if SOURCE_PDF.exists():
        pdf_target = target / "docs" / "source" / SOURCE_PDF.name
        pdf_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE_PDF, pdf_target)

    (target / "collecte_active.flag").write_text("OFF", encoding="utf-8")
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pipeline unique CHRUTH.")
    parser.add_argument("--collect-ao", action="store_true",
                        help="Recollecter les appels d'offres BOAMP/DCE avant l'export AO.")
    parser.add_argument("--collect-prospects", action="store_true",
                        help="Recollecter les prospects via l'API Recherche Entreprises.")
    parser.add_argument("--scope", choices=["france", "region", "departements", "test"], default="france",
                        help="Perimetre prospects si --collect-prospects.")
    parser.add_argument("--regions", default="", help="Regions prospects/AO separees par virgules.")
    parser.add_argument("--departements", default="69", help="Departements si --scope departements.")
    parser.add_argument("--skip-ao", action="store_true", help="Ne pas generer le cockpit AO.")
    parser.add_argument("--skip-prospects", action="store_true", help="Ne pas generer prospects/carte/CRM/KPI.")
    parser.add_argument("--skip-finance", action="store_true", help="Ne pas generer le modele financier autonome.")
    parser.add_argument("--generer-messages", action="store_true",
                        help="Activer les brouillons IA par segment si un LLM local/cloud est disponible.")
    parser.add_argument("--pack", action="store_true", help="Creer un dossier portable pret a envoyer.")
    parser.add_argument("--package-dir", type=Path, default=None, help="Dossier cible du pack portable.")
    parser.add_argument("--leave-collecte-on", action="store_true",
                        help="Laisser le drapeau collecte ON a la fin si une recollecte a ete demandee.")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    write_reference_docs()

    os.environ["CHRUTH_GENERER_MESSAGES"] = "1" if args.generer_messages else "0"
    log_path = LOG_DIR / f"pipeline_unique_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    try:
        with log_path.open("w", encoding="utf-8") as log_file:
            log_file.write("CHRUTH - Pipeline unique\n")
            log_file.write(f"Date: {datetime.now().isoformat(timespec='seconds')}\n")
            log_file.write(f"Arguments: {vars(args)}\n")

            if not args.skip_ao:
                set_collecte(args.collect_ao)
                ao_cmd = [sys.executable, str(ROOT / "ao_weekly_update.py")]
                if args.regions.strip():
                    ao_cmd.extend(["--regions", args.regions])
                run(ao_cmd, "1. Appels d'offres - cockpit AO", log_file)

            if not args.skip_prospects:
                set_collecte(args.collect_prospects)
                prospects_cmd = [sys.executable, str(ROOT / "chruth_pipeline_master.py")]
                if args.collect_prospects:
                    prospects_cmd.extend(["--collect", "--scope", args.scope])
                    if args.scope == "region" and args.regions.strip():
                        prospects_cmd.extend(["--regions", args.regions])
                    if args.scope == "departements":
                        prospects_cmd.extend(["--departements", args.departements])
                run(prospects_cmd, "2. Prospects - base, carte, CRM, KPI, exports", log_file)

            if not args.skip_finance:
                set_collecte(False)
                run([sys.executable, str(ROOT / "outils" / "generer_modele_financier.py")],
                    "3. Modele financier autonome", log_file)

            if not args.leave_collecte_on:
                set_collecte(False)

            manifest = generate_manifest(log_path)
            human_manifest = write_human_manifest()
            print(f"\nManifest JSON : {manifest}")
            print(f"Notice livrables : {human_manifest}")

            if args.pack:
                target = package_portable(args.package_dir)
                print(f"\nPack portable : {target}")
                log_file.write(f"\nPack portable : {target}\n")

        print("\n[OK] Pipeline CHRUTH terminee.")
        print(f"Log : {log_path}")
        return 0
    except Exception as exc:  # noqa: BLE001
        if not args.leave_collecte_on:
            try:
                set_collecte(False)
            except Exception:
                pass
        print(f"\n[ERREUR] {exc}")
        print(f"Log : {log_path}")
        return 1


MISSION_DOC = """# Missions CHRUTH - correspondance pipeline

Source : `Fiche de poste CHRUTH.pdf`.

## Mission 1 - Data Foundation

Objectif : construire une base prospects B2B reutilisable.

Livrables :
- `output/Base_Prospects_CHRUTH.xlsm`
- `output/prospects_nettoyes.csv`
- `output/prospects_enrichis.csv`
- `output/Carte_Prospects_CHRUTH.html`

## Mission 2 - Segmentation et scoring

Objectif : ne plus prospecter a l'aveugle.

Livrables :
- scoring `signal_besoin` et `priorite`
- `output/KPI_CHRUTH.csv`
- `output/CONTROLE_QUALITE_CHRUTH.csv`
- `output/powerbi_sources/`

## Mission 3 - AI-Driven Sales

Objectif : generer des brouillons de prospection personnalises par segment.

Livrables :
- `output/Prospects_CHAUDS_messages.xlsx` : feuilles Messages + Suivi_Envois (saisie statut) + Perf_Messages (taux par variante A/B, variante recommandee)
- `output/segments_messages.json`
- `prompts/PROMPTS_CHRUTH.md`
- `suivi/suivi_envois.csv` : source de verite du suivi (prive, hors pack)

Boucle d'optimisation : 2 variantes par segment, suivi des resultats saisi a la main, bascule automatique sur la meilleure variante au-dela de 20 resultats.

Note A/B : par defaut les templates A et B sont deterministes et genuinement distincts (A = accroche directe, B = benefice prospect) — aucun appel LLM. La generation IA est opt-in via `generate_messages(utiliser_ia=True)` ; en mode IA les deux variantes partagent actuellement le meme prompt (a affiner dans une prochaine iteration).

## Mission 4 - CRM et rentabilite

Objectif : piloter l'activite avec les donnees.

Livrables :
- `output/CRM_CHRUTH_CHAUDE.xlsx`
- `output/Modele_Financier_CHRUTH.xlsx`
- `output/notion_import_chruth/`

## Extension utile - Appels d'offres

Le projet ajoute un cockpit AO pour detecter les marches publics pertinents, alerter
par email, et rediger un message structure par AO (style SEKOIA : profil CHRUTH injecte).

Livrables :
- `output/AO_CHRUTH.xlsm` : cockpit (AO chauds/tiedes, scoring, brouillons email/script)
- `config_chruth/fiche_chruth.md` : fiche CHRUTH a remplir (faits reels injectes dans l'IA)
- `CHRUTH_Messages_AO.ipynb` : notebook de redaction par AO, sortie sectionnee editable
  (`output/messages_ao/AO_<id>.md`)
- mail d'alerte : chaque nouvel AO chaud/tiede arrive avec son brouillon (email + script)

Moteur IA automatique : une cle cloud dans `.env` (anthropic > mistral > groq, une seule
suffit) sinon Ollama local sinon brouillon deterministe. La fiche CHRUTH rend les messages
precis et evite l'invention (garde-fous anti-hallucination).
"""


PROMPTS_DOC = """# Prompts CHRUTH

Ces prompts sont integres dans les scripts et servent de reference modifiable.

## Prompt systeme - prospection B2B

Tu es un expert en prospection commerciale B2B pour CHRUTH, societe francaise specialisee dans le nettoyage et la proprete des locaux. Tu ecris un francais professionnel, clair et concis. Tu reponds uniquement par un objet JSON valide avec les cles `email` et `script`.

## Prompt segment - email + script d'appel

Genere un email de prospection et un script d'appel telephonique pour ce segment.

Variables obligatoires :
- `{denomination}`
- `{ville}`
- `{effectif}`

Contraintes :
- adapter l'accroche au secteur ;
- rester factuel ;
- ne pas inventer de references client, certifications, prix ou chiffres ;
- produire un email court et un script oral naturel ;
- finir par une demande de rendez-vous.

## Prompt analyse AO

Pour un appel d'offres donne, produire :
- un resume de l'opportunite ;
- les risques ;
- les informations manquantes ;
- un brouillon d'email ;
- un script d'appel.

Contraintes :
- ne jamais inventer les donnees absentes ;
- citer les champs disponibles ;
- signaler les points a verifier.
"""


if __name__ == "__main__":
    raise SystemExit(main())
