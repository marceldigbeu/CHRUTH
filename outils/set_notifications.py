"""Active / desactive les alertes email CHRUTH (appele par le bouton VBA du cockpit).

Usage : python outils/set_notifications.py ON|OFF|toggle
Sans argument : affiche l'etat courant.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ao_config import notifications_actives, set_notifications  # noqa: E402


def main() -> int:
    arg = (sys.argv[1] if len(sys.argv) > 1 else "").strip().upper()
    if arg == "TOGGLE":
        actif = not notifications_actives()
    elif arg in ("ON", "OFF"):
        actif = arg == "ON"
    elif arg == "":
        print("ON" if notifications_actives() else "OFF")
        return 0
    else:
        print(f"Argument invalide : {arg!r} (attendu ON, OFF ou toggle).")
        return 2
    set_notifications(actif)
    print("Notifications email : " + ("ON" if actif else "OFF"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
