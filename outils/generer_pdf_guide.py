"""Produit le PDF d'un guide, depuis sa version HTML ou Markdown.

Le PDF et le HTML sont deux vues du meme document, et jusqu'ici seul le HTML
etait tenu a jour : le PDF livre au client decrivait une application qui avait
change. Ce script supprime la derive en faisant du HTML la seule source.

Deux moteurs, dans cet ordre :
  1. un navigateur sans interface (Chrome ou Edge), qui respecte les regles
     `@media print` et `@page A4` deja ecrites dans la feuille de style ;
  2. PyMuPDF a defaut, qui rend un PDF correct mais ignore ces regles.

Une source Markdown est d'abord habillee de la feuille de style du guide de
reference, pour que tous les documents livres se ressemblent.

Usage :  python outils/generer_pdf_guide.py [source.html|.md] [cible.pdf]
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SOURCE_DEFAUT = BASE / "GUIDE_UTILISATION_CHRUTH.html"
CIBLE_DEFAUT = BASE / "GUIDE_UTILISATION_CHRUTH.pdf"

NAVIGATEURS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)


def trouver_navigateur() -> str | None:
    """Chemin d'un navigateur utilisable, ou None."""
    for chemin in NAVIGATEURS:
        if Path(chemin).is_file():
            return chemin
    for nom in ("chrome", "msedge", "chromium"):
        trouve = shutil.which(nom)
        if trouve:
            return trouve
    return None


def _style_de_reference() -> str:
    """Feuille de style du guide HTML, reprise telle quelle.

    On ne recopie pas le CSS ici : deux copies divergeraient, et les documents
    livres cesseraient de se ressembler apres la premiere retouche.
    """
    if not SOURCE_DEFAUT.is_file():
        return ""
    texte = SOURCE_DEFAUT.read_text(encoding="utf-8")
    trouve = re.search(r"<style>.*?</style>", texte, re.S)
    return trouve.group(0) if trouve else ""


def markdown_vers_html(source: Path, cible: Path) -> Path:
    """Habille un Markdown de la mise en forme des guides et l'ecrit en HTML."""
    import markdown

    corps = markdown.markdown(
        source.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", "toc", "sane_lists"])
    titre = source.stem.replace("_", " ").title()
    cible.write_text(
        '<!DOCTYPE html>\n<html lang="fr"><head><meta charset="utf-8">'
        f"<title>{titre}</title>{_style_de_reference()}</head>"
        f'<body><div class="page">{corps}</div></body></html>',
        encoding="utf-8")
    return cible


def _via_navigateur(source: Path, cible: Path, navigateur: str) -> bool:
    """Impression sans interface. Renvoie False si le navigateur n'a rien produit."""
    # Profil jetable : sans lui, une instance de Chrome deja ouverte capte la
    # commande et rend la main sans jamais ecrire le PDF.
    with tempfile.TemporaryDirectory() as profil:
        commande = [
            navigateur, "--headless", "--disable-gpu", "--no-sandbox",
            f"--user-data-dir={profil}",
            "--no-pdf-header-footer",
            # Chemin absolu : le navigateur ecrit sinon dans SON dossier courant,
            # le controle plus bas ne trouve rien, et on retombe en silence sur
            # le moteur de repli — qui ignore la mise en page d'impression.
            f"--print-to-pdf={cible.resolve()}",
            source.resolve().as_uri(),
        ]
        try:
            subprocess.run(commande, timeout=180, capture_output=True, check=False)
        except (subprocess.TimeoutExpired, OSError):
            return False
    return cible.is_file() and cible.stat().st_size > 5000


def _via_pymupdf(source: Path, cible: Path) -> bool:
    """Repli sans navigateur. Rend le texte et les tableaux, pas la mise en page print."""
    try:
        import fitz
    except ImportError:
        return False
    html = source.read_text(encoding="utf-8")
    story = fitz.Story(html=html)
    writer = fitz.DocumentWriter(str(cible))
    zone = fitz.paper_rect("a4")
    utile = zone + (50, 50, -50, -50)
    encore = True
    while encore:
        dispositif = writer.begin_page(zone)
        encore, _ = story.place(utile)
        story.draw(dispositif)
        writer.end_page()
    writer.close()
    return cible.is_file() and cible.stat().st_size > 5000


def generer(source: Path = SOURCE_DEFAUT, cible: Path = CIBLE_DEFAUT) -> tuple[bool, str]:
    """Produit le PDF. Renvoie (succes, moteur utilise)."""
    source, cible = Path(source), Path(cible)
    if not source.is_file():
        return False, f"source introuvable : {source}"

    temporaire = None
    if source.suffix.lower() in (".md", ".markdown"):
        temporaire = source.with_suffix(".rendu.html")
        source = markdown_vers_html(source, temporaire)

    navigateur = trouver_navigateur()
    try:
        if navigateur and _via_navigateur(source, cible, navigateur):
            return True, Path(navigateur).stem
        if _via_pymupdf(source, cible):
            return True, "pymupdf (mise en page print ignoree)"
        return False, "aucun moteur disponible"
    finally:
        if temporaire is not None and temporaire.is_file():
            temporaire.unlink()


def main(argv: list[str]) -> int:
    source = Path(argv[1]) if len(argv) > 1 else SOURCE_DEFAUT
    cible = Path(argv[2]) if len(argv) > 2 else CIBLE_DEFAUT
    ok, moteur = generer(source, cible)
    if not ok:
        print(f"Echec : {moteur}")
        return 1
    taille = cible.stat().st_size / 1024
    print(f"PDF regenere : {cible.name} ({taille:.0f} Ko) via {moteur}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONUTF8", "1")
    raise SystemExit(main(sys.argv))
