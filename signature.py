"""Signature des messages CHRUTH : coordonnees lues dans la fiche, jamais inventees.

Le bloc est appose APRES la generation. Un modele de langage a qui l'on demande
une signature produit un numero de telephone plausible et faux : c'est pour cela
que cette etape est deterministe et vit hors du prompt.
"""
from __future__ import annotations

import re

TITRE = re.compile(r"^\s*#+\s*coordonn", re.IGNORECASE)
LIGNE = re.compile(r"^\s*[-*]?\s*(site|email|e-mail|courriel|telephone|téléphone|tel|tél)\s*:\s*(.+?)\s*$",
                   re.IGNORECASE)
COMMENTAIRE = re.compile(r"<!--.*?-->", re.DOTALL)

CHAMPS = {"site": "site", "email": "email", "e-mail": "email", "courriel": "email",
          "telephone": "telephone", "téléphone": "telephone", "tel": "telephone",
          "tél": "telephone"}
LIBELLES = [("site", "Site"), ("email", "Email"), ("telephone", "Téléphone")]


def coordonnees(fiche: str) -> dict[str, str]:
    """Coordonnees de la section « Coordonnees ». Dictionnaire vide si absente."""
    texte = COMMENTAIRE.sub("", fiche or "")
    trouve: dict[str, str] = {}
    dans_section = False
    for ligne in texte.splitlines():
        if ligne.lstrip().startswith("#"):
            dans_section = bool(TITRE.match(ligne))
            continue
        if not dans_section:
            continue
        m = LIGNE.match(ligne)
        if m:
            cle = CHAMPS[m.group(1).lower()]
            valeur = m.group(2).strip()
            if valeur:
                trouve.setdefault(cle, valeur)
    return trouve


def bloc(fiche: str) -> str:
    """Bloc de signature, ou chaine vide si aucune coordonnee n'est renseignee."""
    c = coordonnees(fiche)
    lignes = [f"{libelle} : {c[cle]}" for cle, libelle in LIBELLES if c.get(cle)]
    if not lignes:
        return ""
    return "CHRUTH\n" + "\n".join(lignes)


def apposer(texte: str, fiche: str) -> str:
    """Ajoute la signature a la fin du texte. Sans coordonnees, rend le texte tel quel."""
    b = bloc(fiche)
    if not b:
        return texte
    if b in (texte or ""):
        return texte
    return (texte or "").rstrip() + "\n\n" + b
