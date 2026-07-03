"""Genere CHRUTH_Alertes.ipynb : interface pour lancer/apercevoir les alertes AO.

Le notebook ne remplace pas ao_alertes.py : il l'importe pour afficher l'etat,
apercevoir l'email (sans envoi) et, sur demande explicite, l'envoyer.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nb_build import code, md, save_notebook  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "CHRUTH_Alertes.ipynb"


def build(out_path: str | Path | None = None) -> Path:
    cells = [
        md(
            "# CHRUTH - Alertes appels d'offres\n\n"
            "Interface pour `ao_alertes.py`. Envoie par email les **nouveaux AO CHAUD/TIEDE**\n"
            "(avec le brouillon de message), piloté par le drapeau notifications ON/OFF.\n\n"
            "Secrets SMTP : `alertes_secrets.json` (ou variables d'environnement). "
            "Destinataires : `destinataires.txt`.\n\n"
            "Par défaut ce notebook est en **aperçu** : rien n'est envoyé tant que `ENVOYER=False`.",
            "intro",
        ),
        md("## 1. Setup", "setup-md"),
        code(
            "import sys, pathlib\n"
            "sys.path.insert(0, str(pathlib.Path.cwd()))\n"
            "from datetime import datetime\n"
            "import ao_alertes, ao_config\n"
            "print('Modules charges.')",
            "setup-code",
        ),
        md("## 2. État actuel", "etat-md"),
        code(
            "print('Notifications actives :', ao_config.notifications_actives())\n"
            "print('Destinataires        :', ao_alertes.charger_destinataires() or '(aucun)')\n"
            "en_attente = ao_alertes.nouveaux_ao_a_alerter()\n"
            "print('Nouveaux AO a alerter :', len(en_attente))",
            "etat-code",
        ),
        md(
            "## 3. Aperçu de l'email (sans envoi)\n\n"
            "Construit l'email des AO en attente et l'écrit dans `output/apercu_alerte.html` "
            "(ouvrir dans un navigateur). N'envoie rien, ne marque rien.",
            "apercu-md",
        ),
        code(
            "en_attente = ao_alertes.nouveaux_ao_a_alerter()\n"
            "if not en_attente:\n"
            "    print('Aucun nouvel AO CHAUD/TIEDE a alerter pour le moment.')\n"
            "else:\n"
            "    sujet, html, texte = ao_alertes.construire_email(en_attente, datetime.now())\n"
            "    chemin = pathlib.Path('output') / 'apercu_alerte.html'\n"
            "    chemin.parent.mkdir(parents=True, exist_ok=True)\n"
            "    chemin.write_text(html, encoding='utf-8')\n"
            "    print('Sujet   :', sujet)\n"
            "    print('Apercu HTML ecrit :', chemin)\n"
            "    print('\\n' + texte)",
            "apercu-code",
        ),
        md(
            "## 4. Envoyer réellement (opt-in)\n\n"
            "Mets `ENVOYER = True` pour envoyer vraiment. Respecte le drapeau notifications "
            "(rien n'est envoyé si OFF) et marque les AO envoyés.",
            "envoi-md",
        ),
        code(
            "ENVOYER = False   # passe a True pour envoyer pour de vrai\n"
            "if ENVOYER:\n"
            "    n = ao_alertes.envoyer_alertes()\n"
            "    print(n, 'AO envoyes.' if n else 'aucun nouvel AO (ou notifications OFF).')\n"
            "else:\n"
            "    print('Mode apercu : ENVOYER=False, aucun email envoye.')",
            "envoi-code",
        ),
    ]
    return save_notebook(cells, out_path or OUT)


if __name__ == "__main__":
    print(build())
