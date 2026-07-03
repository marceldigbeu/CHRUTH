"""Genere le message IA (email + script) pour UN appel d'offres, identifie par id_ao,
et l'ecrit dans output/_message_ao.txt (lu ensuite par le bouton Excel).

Usage : python outils/generer_message_ao.py <id_ao>
Appele par la macro VBA Generer_Message_AO (bouton de l'onglet AO_Nettoyage_IDF).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ao_messages  # noqa: E402
from ao_config import AO_DB_PATH, OUTPUT_DIR  # noqa: E402
from ao_db import connect  # noqa: E402

SORTIE = OUTPUT_DIR / "_message_ao.txt"


def _record(id_ao: str) -> dict | None:
    with connect(AO_DB_PATH) as conn:
        row = conn.execute("SELECT * FROM ao_records WHERE id_ao=?", (id_ao,)).fetchone()
    return dict(row) if row else None


def formater(rec: dict, msg: dict) -> str:
    def g(k):
        return str(rec.get(k) or "").strip()
    return (
        f"OBJET : {g('objet')}\n"
        f"ACHETEUR : {g('acheteur')}\n"
        f"VILLE : {g('ville')}   |   DATE LIMITE : {g('date_limite')}\n"
        f"SOURCE : {msg.get('source', '')} (ia = redige par le modele ; defaut = brouillon type)\n\n"
        f"===== EMAIL =====\n{msg.get('email', '')}\n\n"
        f"===== SCRIPT D'APPEL =====\n{msg.get('script', '')}\n"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    id_ao = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    rec = _record(id_ao)
    if not rec:
        SORTIE.write_text(f"AO introuvable : {id_ao}\n", encoding="utf-8")
        print(f"AO introuvable : {id_ao}")
        return 1
    msg = ao_messages.generer_message_ao(rec)
    SORTIE.write_text(formater(rec, msg), encoding="utf-8")
    print(f"Message genere ({msg['source']}) -> {SORTIE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
