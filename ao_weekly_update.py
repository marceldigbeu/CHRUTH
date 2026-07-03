from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ao_config import (
    AO_API_PAGE_LIMIT,
    AO_LOOKBACK_DAYS,
    AO_MAX_EXPORT_ROWS,
    AO_MAX_PAGES,
    collecte_active,
)


BASE = Path(__file__).resolve().parent
LOG_DIR = BASE / "logs"


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_step(label: str, command: list[str], log_file) -> int:
    print(f"\n=== {label} ===")
    log_file.write(f"\n=== {label} ===\n")
    log_file.write(" ".join(command) + "\n")
    log_file.flush()
    process = subprocess.Popen(
        command,
        cwd=BASE,
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
    return process.wait()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mise a jour hebdomadaire AO CHRUTH.")
    parser.add_argument("--max-pages", type=int, default=AO_MAX_PAGES)
    parser.add_argument("--page-limit", type=int, default=AO_API_PAGE_LIMIT)
    parser.add_argument("--max-ao", type=int, default=AO_MAX_EXPORT_ROWS)
    parser.add_argument("--lookback-days", type=int, default=AO_LOOKBACK_DAYS)
    parser.add_argument("--strict-budget", action="store_true")
    parser.add_argument("--idf-only", action="store_true")
    parser.add_argument("--regions", default="",
                        help="Filtre region (noms separes par virgules), ex: \"Île-de-France\".")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    LOG_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"ao_weekly_update_{stamp}.log"

    collect_cmd = [
        sys.executable,
        str(BASE / "ao_collect_boamp.py"),
        "--max-pages",
        str(args.max_pages),
        "--page-limit",
        str(args.page_limit),
        "--max-ao",
        str(args.max_ao),
        "--lookback-days",
        str(args.lookback_days),
    ]
    if args.strict_budget:
        collect_cmd.append("--strict-budget")
    if args.idf_only:
        collect_cmd.append("--idf-only")
    if args.regions.strip():
        collect_cmd.extend(["--regions", args.regions])

    export_cmd = [sys.executable, str(BASE / "ao_export_excel.py")]
    if args.regions.strip():
        export_cmd.extend(["--regions", args.regions])

    collecte_ok = collecte_active()
    steps = []
    if collecte_ok:
        steps.extend([
            ("1. Collecte BOAMP", collect_cmd),
            ("2. Traitement DCE (liens + PDF directs + depots)", [sys.executable, str(BASE / "ao_dce_process.py")]),
        ])
    steps.extend([
        ("3. Export Excel AO", export_cmd),
        ("4. Publication dossier partage (best-effort)", [sys.executable, str(BASE / "ao_publish.py")]),
    ])

    print("=" * 70)
    print("CHRUTH - Mise a jour appels d'offres")
    print(f"Max pages    : {args.max_pages}")
    print(f"Page limit   : {args.page_limit}")
    print(f"Max AO       : {args.max_ao}")
    print(f"Strict budget: {args.strict_budget}")
    print(f"IDF only     : {args.idf_only}")
    print(f"Region(s)    : {args.regions or '-'}")
    print(f"Collecte     : {'ON' if collecte_ok else 'OFF'}")
    print(f"Log          : {log_path}")
    print("=" * 70)

    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write("CHRUTH - Mise a jour appels d'offres\n")
        log_file.write(f"Date: {datetime.now().isoformat()}\n")
        log_file.write(f"Collecte donnees: {'ON' if collecte_ok else 'OFF'}\n")
        if not collecte_ok:
            msg = "[COLLECTE] Desactivee depuis Excel -> BOAMP/DCE ignorees, export depuis les donnees locales."
            print(msg)
            log_file.write(msg + "\n")
        for label, command in steps:
            code = run_step(label, command, log_file)
            if code != 0:
                msg = f"[ERREUR] Etape echouee : {label} (code {code})"
                print(msg)
                log_file.write(msg + "\n")
                return code
        log_file.write("\nMise a jour AO terminee avec succes.\n")

    print("\nMise a jour AO terminee avec succes.")
    print(f"Log : {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
