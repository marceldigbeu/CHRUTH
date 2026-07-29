"""Regenere le miroir HTML autonome avec les donnees reelles du poste.

`CHRUTH_PLATEFORME.html` reproduit la plateforme dans un fichier unique,
ouvrable sans Python, sans serveur et sans internet — utile pour consulter la
veille sur un telephone ou l'envoyer a quelqu'un. Il portait huit appels
d'offres ecrits a la main : une maquette figee.

Ce script y injecte la base reelle. Le fichier reste autonome : les donnees
sont ecrites dedans, jamais chargees a cote.

Le fichier de sortie est aussi le modele : on remplace les tableaux de donnees
sur place, ce qui preserve la mise en page et le JavaScript ecrits a la main.

Usage :  python outils/generer_plateforme_html.py [--verifier]
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plateforme_html as ph  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
FICHIER = BASE / "CHRUTH_PLATEFORME.html"


def _acheteurs_de_la_semaine() -> list[dict]:
    """Acheteurs recents, ou liste vide si le calcul echoue.

    Best-effort deliberement : le miroir doit se regenerer meme quand
    l'enrichissement par SIRET est indisponible (reseau coupe, API en panne).
    """
    try:
        import acheteurs_semaine
        return acheteurs_semaine.construire()
    except Exception:  # noqa: BLE001
        return []


def _horodatage(html: str) -> str:
    """Inscrit la date de generation dans le sous-titre du fichier."""
    import re
    marque = datetime.now().strftime("%d/%m/%Y à %H:%M")
    nouveau = f"Données au {marque}"
    if "Données au " in html:
        return re.sub(r"Données au [^<\"']*", nouveau, html, count=1)
    return html.replace("</h1>", f"</h1>\n<p class=\"aide\">{nouveau}</p>", 1)


def generer(fichier: Path = FICHIER) -> dict:
    """Injecte les donnees reelles dans le miroir. Renvoie un compte rendu."""
    import ao_db
    import reglages

    fichier = Path(fichier)
    if not fichier.is_file():
        raise SystemExit(f"Modele introuvable : {fichier}")

    df = ao_db.fetch_records()
    aos = ph.donnees_aos(df)
    acheteurs = ph.donnees_acheteurs(_acheteurs_de_la_semaine())

    html = fichier.read_text(encoding="utf-8")
    html = ph.remplacer_tableau(html, "AOS", aos)
    if acheteurs:
        html = ph.remplacer_tableau(html, "ACH", acheteurs)
    # Les destinataires sont ecrits dans l'objet des reglages par defaut, hors
    # de tout `var` : sans ce passage, le garde-fou ci-dessous refuse d'ecrire.
    html = ph.vider_destinataires(html)
    html = _horodatage(html)

    # Garde-fou : ce fichier est fait pour etre envoye. Une adresse qui s'y
    # glisserait serait publiee avec lui.
    if ph.contient_une_adresse_email(html):
        raise SystemExit("Abandon : une adresse email subsiste dans le fichier genere.")

    fichier.write_text(html, encoding="utf-8")
    return {"aos": len(aos), "acheteurs": len(acheteurs),
            "taille_ko": fichier.stat().st_size / 1024,
            "total_base": 0 if df is None or df.empty else len(df)}


def verifier(fichier: Path = FICHIER) -> int:
    """Controle sans ecrire : le miroir est-il encore d'exemple ou expurge ?"""
    html = Path(fichier).read_text(encoding="utf-8")
    if ph.contient_une_adresse_email(html):
        print("ECHEC : le fichier contient une adresse email.")
        return 1
    exemple = html.count('id:"MX-1"') + html.count('"id": "MX-1"')
    if exemple:
        print("ECHEC : le fichier porte encore les donnees d'exemple.")
        return 1
    print("OK : ni adresse email, ni donnees d'exemple.")
    return 0


def main(argv: list[str]) -> int:
    if "--verifier" in argv:
        return verifier()
    r = generer()
    print(f"Miroir regenere : {FICHIER.name} ({r['taille_ko']:.0f} Ko)")
    print(f"  {r['aos']} appels d'offres embarques sur {r['total_base']} en base")
    print(f"  {r['acheteurs']} acheteurs de la semaine")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main(sys.argv))
