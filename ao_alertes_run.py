from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ao_config import collecte_active

BASE = Path(__file__).resolve().parent
LOG_DIR = BASE / "logs"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _run(label: str, command: list[str], log_file) -> int:
    print(f"\n=== {label} ===")
    log_file.write(f"\n=== {label} ===\n")
    log_file.flush()
    proc = subprocess.Popen(command, cwd=BASE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
        log_file.write(line)
        log_file.flush()
    return proc.wait()


def main() -> int:
    LOG_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"ao_alerte_{stamp}.log"
    py = sys.executable
    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write(f"CHRUTH - Alerte AO\nDate: {datetime.now().isoformat()}\n")

        if collecte_active():
            # 1) Collecte (bloquant : sans collecte, rien de neuf a signaler).
            code = _run("1. Collecte BOAMP (IDF nettoyage)", [py, str(BASE / "ao_collect_boamp.py")], log_file)
            if code != 0:
                print(f"[ERREUR] Collecte echouee (code {code})")
                return code

            # 1.5) Ingestion Maximilien (BEST-EFFORT : emails non lus IMAP -> injecte dans la base).
            code_max = _run("1.5. Ingestion Maximilien (IMAP)", [py, str(BASE / "ao_maximilien_ingest.py")], log_file)
            if code_max != 0:
                log_file.write("[INFO] Maximilien non ingere (IMAP indisponible ou aucun email) -> on continue.\n")
        else:
            log_file.write("[COLLECTE] Desactivee depuis Excel -> BOAMP/IMAP ignores.\n")

        # 2) Mise a jour du tableur (BEST-EFFORT : si AO_CHRUTH.xlsm est ouvert dans Excel,
        #    l'ecriture echoue -> on log et on continue, le mail part quand meme, l'Excel
        #    se mettra a jour au prochain run libre).
        code = _run("2. Mise a jour Excel (au mieux)", [py, str(BASE / "ao_export_excel.py")], log_file)
        if code != 0:
            msg = "[INFO] Excel non regenere (probablement ouvert/verrouille) -> on continue."
            print(msg)
            log_file.write(msg + "\n")

        # 3) Notification email des nouveaux AO (bloquant pour le code retour).
        code = _run("3. Alerte email (CHAUD/TIEDE nouveaux)", [py, str(BASE / "ao_alertes.py")], log_file)
        if code != 0:
            print(f"[ERREUR] Alerte email echouee (code {code})")
            return code

    print(f"\nAlerte AO terminee. Log : {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
