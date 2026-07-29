"""Prepare un depot neuf, sans historique, sans donnees et sans nom.

Le depot de travail ne peut pas etre publie tel quel : son historique suit
364 Mo de livrables, dont une base de 132 502 societes avec leurs adresses, et
une regle `.gitignore` posee apres coup n'en sort pas un fichier deja commite.
Reecrire cet historique serait long et risque pour un resultat inferieur.

On produit donc un depot vierge : le code, les tests, la documentation et les
modeles, un seul commit, une identite neutre. Les donnees n'y entrent jamais,
ce qui rend la question de l'historique sans objet.

Usage :  python outils/preparer_depot_public.py [dossier_cible]
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

IDENTITE_NOM = "CHRUTH Maintainers"
IDENTITE_MAIL = "maintainers@users.noreply.github.com"

# Ce qui constitue le projet : du code, des tests, de la documentation, des
# modeles vierges. Rien qui contienne de la donnee collectee.
DOSSIERS_INCLUS = ("tests", "outils", "docs", "prompts", "config_chruth",
                   "assets", ".github", ".streamlit")
EXTENSIONS_RACINE = (".py", ".md", ".html", ".pdf", ".bat", ".txt", ".ipynb",
                     ".bas", ".ps1", ".template")

# Ce qui ne doit jamais entrer, meme si un motif ci-dessus le ramenait.
DOSSIERS_EXCLUS = {"output", "data", "logs", "suivi", "etat", "dce_auto",
                   "dce_manuel", "__pycache__", ".git", "venv", ".pytest_cache",
                   "ao_raw", "source"}
FICHIERS_EXCLUS = {".env", "alertes_secrets.json", "destinataires.txt",
                   "secrets.toml", "reglages_cache.json",
                   "alertes_actives.flag", "collecte_active.flag"}
# Le miroir embarque les marches collectes : il part vide, comme un modele que
# `generer_plateforme_html.py` remplit sur le poste.
A_VIDER = "CHRUTH_PLATEFORME.html"
MOTIFS_EXCLUS = ("~$",)
# Les classeurs de `assets/` sont des modeles porteurs de macros, donc du
# code : ils restent. La donnee vit dans `output/` et `data/`, exclus par dossier.
SUFFIXES_EXCLUS = (".bak", ".backup", ".old", ".sqlite", ".csv")

# Les noms a traquer ne sont pas ecrits ici : on les deduit des auteurs de
# l'historique. Les inscrire en dur ferait de ce fichier meme le dernier
# endroit ou le nom subsiste — et la verification echouerait sur elle-meme.
#
# « anthropic » et « claude-... » ne sont pas des noms d'auteur mais le
# fournisseur d'IA et un identifiant de modele : les retirer casserait le moteur.
# Le nom du dossier personnel : il apparait dans tout chemin absolu recopie
# dans une documentation. Deduit du systeme, jamais ecrit en dur.


def noms_des_auteurs(depot: Path = BASE) -> set[str]:
    """Noms et identifiants tires des auteurs de l'historique.

    On en extrait aussi la partie locale des adresses : « prenom.nom@fai.fr »
    laisse « prenom.nom », qui se retrouve souvent dans un chemin ou une URL.
    """
    try:
        sortie = subprocess.run(["git", "log", "--format=%an|%ae"], cwd=depot,
                                capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, OSError):
        return set()

    # L'identite retenue pour la publication ne se traque pas elle-meme.
    neutres = {m.casefold() for m in IDENTITE_NOM.split()} | {"chruth"}

    noms: set[str] = set()
    dossier_personnel = Path.home().name
    if len(dossier_personnel) > 3 and dossier_personnel.casefold() not in neutres:
        noms.add(dossier_personnel)
    for ligne in sortie.splitlines():
        nom, _, mail = ligne.partition("|")
        for mot in nom.replace("-", " ").split():
            if len(mot) > 3 and mot.casefold() not in neutres:
                noms.add(mot)
        local = mail.split("@")[0]
        if len(local) > 3 and local.casefold() not in neutres                 and not local.startswith(("contact", "maintainers", "noreply")):
            noms.add(local)
            for mot in re.split(r"[._-]", local):
                if len(mot) > 3:
                    noms.add(mot)
    return noms


def _effacer(dossier: Path) -> None:
    """Supprime un dossier, y compris un depot git.

    Sous Windows, les objets git sont en lecture seule : `rmtree` echoue sur
    eux tant qu'on n'a pas retire l'attribut.
    """
    import os
    import stat

    def forcer(fonction, chemin, _exc):
        os.chmod(chemin, stat.S_IWRITE)
        fonction(chemin)

    shutil.rmtree(dossier, onexc=forcer)


def _accepte(chemin: Path) -> bool:
    nom = chemin.name
    if nom in FICHIERS_EXCLUS or nom.startswith(MOTIFS_EXCLUS):
        return False
    if any(s in nom for s in SUFFIXES_EXCLUS):
        return False
    return True


def _copier_dossier(source: Path, cible: Path) -> int:
    """Copie un dossier en ecartant ce qui ne doit pas etre publie."""
    copies = 0
    for chemin in source.rglob("*"):
        if not chemin.is_file() or not _accepte(chemin):
            continue
        relatif = chemin.relative_to(source)
        if any(p in DOSSIERS_EXCLUS for p in relatif.parts):
            continue
        destination = cible / relatif
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(chemin, destination)
        copies += 1
    return copies


def noms_restants(dossier: Path, noms: set[str] | None = None) -> list[str]:
    """Fichiers ou un nom propre subsiste. Liste vide attendue."""
    noms = noms_des_auteurs() if noms is None else noms
    interdits = tuple(noms)
    trouves = []
    for chemin in dossier.rglob("*"):
        if not chemin.is_file() or chemin.suffix.lower() in (".pdf", ".xlsm", ".xlsx"):
            continue
        try:
            texte = chemin.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(n.casefold() in texte.casefold() for n in interdits):
            trouves.append(chemin.relative_to(dossier).as_posix())
    return sorted(trouves)


def adresses_restantes(dossier: Path) -> list[str]:
    """Adresses email autres que celles des exemples et de l'identite retenue."""
    motif = re.compile(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}")
    tolerees = ("exemple.fr", "example.com", "chruth.fr", "users.noreply.github.com",
                "anthropic.com", "b.fr", "x.fr", "d.fr")
    trouvees = set()
    for chemin in dossier.rglob("*"):
        if not chemin.is_file() or chemin.suffix.lower() in (".pdf", ".xlsm", ".xlsx"):
            continue
        try:
            texte = chemin.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for adresse in motif.findall(texte):
            if not adresse.lower().endswith(tolerees):
                trouvees.add(adresse)
    return sorted(trouvees)


def initialiser_depot(cible: Path, message: str) -> None:
    """Depot vierge, un commit, identite neutre posee localement."""
    def git(*args):
        subprocess.run(["git", *args], cwd=cible, check=True,
                       capture_output=True, text=True)

    git("init", "-q", "-b", "main")
    git("config", "user.name", IDENTITE_NOM)
    git("config", "user.email", IDENTITE_MAIL)
    git("add", "-A")
    git("commit", "-q", "-m", message)


def preparer(cible: Path, avec_git: bool = True) -> dict:
    cible = Path(cible)
    if cible.exists():
        _effacer(cible)
    cible.mkdir(parents=True)

    copies = 0
    for chemin in BASE.iterdir():
        if chemin.is_dir() and chemin.name in DOSSIERS_INCLUS:
            copies += _copier_dossier(chemin, cible / chemin.name)
        elif chemin.is_file() and chemin.suffix.lower() in EXTENSIONS_RACINE and _accepte(chemin):
            shutil.copy2(chemin, cible / chemin.name)
            copies += 1
    miroir = cible / A_VIDER
    if miroir.is_file():
        sys.path.insert(0, str(BASE))
        import plateforme_html as ph
        html = miroir.read_text(encoding="utf-8")
        html = ph.remplacer_tableau(html, "AOS", [])
        html = ph.remplacer_tableau(html, "ACH", [])
        miroir.write_text(ph.vider_destinataires(html), encoding="utf-8")

    for special in (".gitignore",):
        if (BASE / special).is_file():
            shutil.copy2(BASE / special, cible / special)
            copies += 1

    rapport = {
        "cible": cible, "fichiers": copies,
        "taille_mo": sum(p.stat().st_size for p in cible.rglob("*") if p.is_file()) / 1_048_576,
        "noms": noms_restants(cible),
        "adresses": adresses_restantes(cible),
    }
    if avec_git and not rapport["noms"]:
        initialiser_depot(cible, "feat: plateforme de veille des marches publics de proprete")
    return rapport


def main(argv: list[str]) -> int:
    cible = Path(argv[1]) if len(argv) > 1 else BASE.parent / "CHRUTH_PUBLIC"
    r = preparer(cible)
    print(f"Depot prepare : {r['cible']}")
    print(f"  {r['fichiers']} fichiers, {r['taille_mo']:.1f} Mo")
    if r["noms"]:
        print(f"  ECHEC, noms encore presents : {r['noms']}")
        return 1
    print("  aucun nom propre dans les fichiers.")
    if r["adresses"]:
        print(f"  adresses a verifier : {r['adresses']}")
    else:
        print("  aucune adresse email reelle.")
    print(f"  depot git initialise, auteur « {IDENTITE_NOM} ».")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main(sys.argv))
