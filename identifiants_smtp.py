"""Lecture et ecriture des identifiants d'envoi, depuis l'application.

Ces valeurs ne passent PAS par `reglages` : ce module ecrit dans l'etat de la
veille, lui-meme pousse sur une branche GitHub en mode cloud, et `reglages`
interdit d'ailleurs explicitement la cle `smtp_password`. Un mot de passe
d'application ecrit la se retrouverait en ligne.

Il vit donc dans `alertes_secrets.json`, fichier local ignore par git et exclu
des copies de livraison — le seul endroit du projet ou un secret a sa place.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ao_config import ALERTE_SECRETS_FILE

CHAMPS = ("smtp_user", "smtp_password", "destinataire")
MASQUE = "•" * 12


def lire(chemin: Path | None = None) -> dict[str, Any]:
    """Contenu du fichier de secrets. Dictionnaire vide s'il est absent ou illisible."""
    p = Path(chemin or ALERTE_SECRETS_FILE)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — fichier corrompu : on repart de zero
        return {}
    return data if isinstance(data, dict) else {}


def expediteur(chemin: Path | None = None) -> str:
    return str(lire(chemin).get("smtp_user") or "")


def mot_de_passe_defini(chemin: Path | None = None) -> bool:
    """Y a-t-il un mot de passe enregistre ? On ne le renvoie jamais.

    L'interface a besoin de savoir s'il faut en demander un, pas de l'afficher :
    un mot de passe reaffiche dans un champ finit en capture d'ecran.
    """
    return bool(str(lire(chemin).get("smtp_password") or "").strip())


def normaliser_mot_de_passe(brut: str) -> str:
    """Un mot de passe d'application Google se copie souvent avec des espaces
    (« abcd efgh ijkl mnop ») : colle tel quel, il est refuse a l'envoi."""
    return "".join(str(brut or "").split())


def ecrire(modifs: dict[str, Any], chemin: Path | None = None) -> dict[str, Any]:
    """Met a jour les identifiants sans effacer ce qui n'est pas fourni.

    Une valeur vide veut dire « ne change pas » et non « efface » : laisser le
    champ mot de passe vide est le cas normal quand on ne modifie que
    l'expediteur. Pour effacer, il y a `oublier`.
    """
    p = Path(chemin or ALERTE_SECRETS_FILE)
    valeurs = lire(p)
    for cle in CHAMPS:
        if cle not in modifs:
            continue
        brut = modifs[cle]
        valeur = normaliser_mot_de_passe(brut) if cle == "smtp_password" else str(brut or "").strip()
        if valeur:
            valeurs[cle] = valeur
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(valeurs, ensure_ascii=False, indent=2), encoding="utf-8")
    return valeurs


def oublier(cle: str, chemin: Path | None = None) -> dict[str, Any]:
    """Supprime une valeur. Le geste a faire quand un mot de passe a fuite."""
    p = Path(chemin or ALERTE_SECRETS_FILE)
    valeurs = lire(p)
    valeurs.pop(cle, None)
    p.write_text(json.dumps(valeurs, ensure_ascii=False, indent=2), encoding="utf-8")
    return valeurs
