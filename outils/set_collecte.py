"""Active / desactive la collecte reseau CHRUTH (appele par les boutons Excel)."""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from ao_config import collecte_active, set_collecte  # noqa: E402


def appliquer(actif: bool) -> bool:
    """Pose l'interrupteur de collecte dans les reglages partages ET le drapeau local."""
    import reglages
    reglages.ecrire({"collecte": bool(actif)})
    set_collecte(bool(actif))
    return bool(actif)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1 or args[0].upper() not in {"ON", "OFF"}:
        print("Usage: python outils/set_collecte.py ON|OFF")
        return 2

    actif = args[0].upper() == "ON"
    appliquer(actif)
    print(f"Collecte donnees : {'ON' if collecte_active() else 'OFF'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
