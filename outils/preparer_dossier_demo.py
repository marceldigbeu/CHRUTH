"""Copie du dossier de livraison expurgee de tout secret, prete a etre envoyee.

Le dossier de travail contient de quoi faire tourner la veille pour de vrai :
mot de passe SMTP, adresses des destinataires, journaux d'envoi. Rien de tout
cela n'a sa place chez un tiers. Plutot que de vider ces fichiers sur place — ce
qui casserait les alertes du poste — on produit une copie propre.

Deux mecanismes, parce que deux natures de secret :
  - EXCLUS : fichiers entierement secrets, on ne les copie pas.
  - EXPURGES : fichiers utiles a la demo (l'etat de la veille porte les 101 AO)
    mais qui trainent des adresses email dans leur bloc de reglages.

Usage :  python outils/preparer_dossier_demo.py [dossier_source] [dossier_cible]
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

# Fichiers a ne jamais copier : ils ne contiennent que des secrets ou du bruit.
EXCLUS = {
    ".env",                       # cles API
    "alertes_secrets.json",       # mot de passe d'application SMTP
    "destinataires.txt",          # adresses des destinataires des alertes
    "secrets.toml",               # identifiants OAuth et liste des acces
}
DOSSIERS_EXCLUS = {
    "logs",            # journaux d'envoi : objets d'AO et adresses
    "suivi",           # suivi commercial reel, hors pack par construction
    "__pycache__",
    ".git",
    "venv",
    ".pytest_cache",
    "dce_auto",        # pieces de marches telechargees, volumineuses
    "dce_manuel",
    "ao_raw",          # 2,3 Go de reponses BOAMP brutes : la base sqlite en est le produit
}
# Fichiers de travail Excel (~$ = classeur ouvert) : jamais dans une livraison.
MOTIFS_EXCLUS = ("~$",)
# Sauvegardes horodatees : elles contiennent l'etat d'avant, adresses comprises.
SUFFIXES_EXCLUS = (".bak", ".backup", ".old")

# Fichiers ou une adresse peut se cacher hors des JSON de reglages : exports
# statiques, documentation, exemples. On y masque les adresses reelles du poste.
EXTENSIONS_TEXTE = (".md", ".txt", ".html", ".htm", ".csv", ".json")
REMPLACEMENT = "adresse-retiree@exemple.fr"
# Cles a vider dans les JSON conserves : l'app les relira comme « non configure ».
CLES_A_VIDER = {"destinataires": [], "expediteur": ""}


def _expurger_reglages(bloc: dict) -> bool:
    """Vide les adresses d'un bloc de reglages. Renvoie True si quelque chose a change."""
    change = False
    for cle, vide in CLES_A_VIDER.items():
        if bloc.get(cle):
            bloc[cle] = vide
            change = True
    return change


def expurger_json(chemin: Path) -> bool:
    """Retire les adresses email d'un fichier de reglages ou d'etat de veille.

    Le bloc `reglages` vit a deux endroits : a la racine de reglages_cache.json,
    et sous la cle `reglages` de etat/veille.json. On traite les deux.
    """
    try:
        data = json.loads(chemin.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False
    if not isinstance(data, dict):
        return False
    change = _expurger_reglages(data)
    if isinstance(data.get("reglages"), dict):
        change = _expurger_reglages(data["reglages"]) or change
    if change:
        chemin.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
                          encoding="utf-8")
    return change


def _ignorer(_dossier: str, noms: list[str]) -> set[str]:
    return {n for n in noms
            if n in EXCLUS or n in DOSSIERS_EXCLUS or n.startswith(MOTIFS_EXCLUS)
            or any(s in n for s in SUFFIXES_EXCLUS)}


def adresses_du_poste(source: Path) -> set[str]:
    """Adresses email reellement configurees sur ce poste.

    On les apprend des fichiers que l'on exclut par ailleurs — destinataires des
    alertes, expediteur, reglages. C'est plus sur que d'enumerer les fichiers a
    nettoyer : un export statique ou une note de documentation qui recopie une
    adresse sera couvert sans qu'on ait pense a lui.
    """
    adresses: set[str] = set()

    fichier = source / "destinataires.txt"
    if fichier.is_file():
        adresses.update(l.strip() for l in fichier.read_text(encoding="utf-8").splitlines()
                        if "@" in l)

    for nom in ("reglages_cache.json", "alertes_secrets.json"):
        chemin = source / nom
        if not chemin.is_file():
            continue
        try:
            data = json.loads(chemin.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for cle in ("destinataires", "expediteur", "destinataire", "smtp_user"):
            valeur = data.get(cle)
            if isinstance(valeur, str) and "@" in valeur:
                adresses.add(valeur.strip())
            elif isinstance(valeur, list):
                adresses.update(v.strip() for v in valeur if isinstance(v, str) and "@" in v)

    return {a for a in adresses if a}


def expurger_adresses(cible: Path, adresses: set[str]) -> list[str]:
    """Masque les adresses dans les fichiers texte de la copie. Renvoie les fichiers touches."""
    if not adresses:
        return []
    touches = []
    for chemin in cible.rglob("*"):
        if not chemin.is_file() or chemin.suffix.lower() not in EXTENSIONS_TEXTE:
            continue
        try:
            texte = chemin.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        remplace = texte
        for adresse in adresses:
            remplace = remplace.replace(adresse, REMPLACEMENT)
        if remplace != texte:
            chemin.write_text(remplace, encoding="utf-8")
            touches.append(chemin.relative_to(cible).as_posix())
    return sorted(touches)


def preparer(source: Path, cible: Path) -> dict:
    """Copie source vers cible sans les secrets. Renvoie un compte rendu."""
    source, cible = Path(source), Path(cible)
    if not source.is_dir():
        raise SystemExit(f"Dossier source introuvable : {source}")
    # Les adresses se lisent AVANT la copie : les fichiers qui les portent en
    # sont exclus, on ne pourrait plus les apprendre depuis la cible.
    adresses = adresses_du_poste(source)
    if cible.exists():
        shutil.rmtree(cible)
    shutil.copytree(source, cible, ignore=_ignorer)

    expurges = [p.name for p in (cible / "reglages_cache.json", cible / "etat" / "veille.json")
                if p.exists() and expurger_json(p)]
    expurges += expurger_adresses(cible, adresses)
    restants = sorted(p.relative_to(cible).as_posix()
                      for n in EXCLUS for p in cible.rglob(n))
    taille = sum(p.stat().st_size for p in cible.rglob("*") if p.is_file())
    return {"cible": cible, "expurges": expurges, "restants": restants,
            "taille_mo": taille / 1_048_576,
            "fichiers": sum(1 for p in cible.rglob("*") if p.is_file())}


def main(argv: list[str]) -> int:
    base = Path(__file__).resolve().parent.parent
    source = Path(argv[1]) if len(argv) > 1 else base
    cible = Path(argv[2]) if len(argv) > 2 else source.parent / f"{source.name}_DEMO"
    r = preparer(source, cible)
    print(f"Copie propre : {r['cible']}")
    print(f"  {r['fichiers']} fichiers, {r['taille_mo']:.1f} Mo")
    print(f"  fichiers expurges : {', '.join(r['expurges']) or 'aucun'}")
    if r["restants"]:
        print(f"  ATTENTION, secrets encore presents : {r['restants']}")
        return 1
    print("  aucun fichier secret dans la copie.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
