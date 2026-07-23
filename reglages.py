"""Reglages CHRUTH : une seule verite, plusieurs fenetres.

Sept endroits portaient jusqu'ici des reglages (destinataires.txt, les .flag, la
colonne du tableur, la fiche, l'etat de veille...) sans qu'aucun fasse autorite.
Ce module est desormais le seul point d'acces : il lit l'etat partage sur la
branche ao-state, retombe sur un cache local, et ecrit toujours les deux.

Ce qui n'est PAS ici : le mot de passe SMTP. L'etat est versionne.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import veille_depot
from ao_config import BASE_DIR

CACHE = BASE_DIR / "reglages_cache.json"

DEFAUTS: dict[str, Any] = {
    "destinataires": [],
    "expediteur": "",
    "notifications": True,
    "collecte": True,
    "fiche_chruth": "",
    "mots_cles_rh_actifs": True,
}

# Jamais dans un fichier versionne.
CLES_INTERDITES = ("smtp_password", "password", "mot_de_passe", "token", "jeton")

# Memoire de processus. `lire()` est appele DANS la boucle de tri (via
# ao_pertinence._mots_cles) : en mode cloud, chaque lecture est une requete HTTP
# vers l'API GitHub avec 20 s de timeout, et un run de 14 AO en faisait 14 pour la
# meme reponse. On ne relit qu'une fois par processus ; `ecrire()` et
# `rafraichir()` invalident, de sorte qu'une valeur perimee par nos soins n'est
# jamais servie. Une surface qui tourne longtemps (l'app) appelle `rafraichir()`
# pour reprendre les changements venus d'ailleurs.
_memo: dict[str, Any] | None = None


def invalider() -> None:
    """Oublie la memoire de processus : la prochaine lecture repart de l'etat partage."""
    global _memo
    _memo = None


def _cache_lu() -> dict[str, Any]:
    try:
        data = json.loads(Path(CACHE).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _cache_ecrit(valeurs: dict[str, Any]) -> None:
    Path(CACHE).parent.mkdir(parents=True, exist_ok=True)
    Path(CACHE).write_text(json.dumps(valeurs, ensure_ascii=False, indent=2,
                                      sort_keys=True), encoding="utf-8")


def _depuis_etat(etat: dict[str, Any]) -> dict[str, Any]:
    reg = dict(etat.get("reglages") or {})
    # Migration douce : guide_messages et fiche_chruth sont la meme chose.
    if not reg.get("fiche_chruth") and etat.get("guide_messages"):
        reg["fiche_chruth"] = etat["guide_messages"]
    # Idem pour l'interrupteur des emails, longtemps porte par une cle de premier
    # niveau que la page Veille ecrivait seule. Une coupure qu'elle porte l'emporte :
    # un coupe-circuit deja pose ne se rouvre jamais tout seul.
    ancienne = etat.get("notifications")
    if ancienne is False or (ancienne is not None and "notifications" not in reg):
        reg["notifications"] = bool(ancienne)
    return reg


def lire() -> dict[str, Any]:
    """Reglages effectifs : etat partage, sinon cache local, sinon defauts du code.

    Memorise pour la duree du processus (voir `_memo`).
    """
    global _memo
    if _memo is not None:
        return dict(_memo)

    valeurs = dict(DEFAUTS)
    valeurs.update(_cache_lu())
    try:
        etat, _ = veille_depot.lire()
        valeurs.update({k: v for k, v in _depuis_etat(etat).items() if v not in (None, "")})
    except Exception:  # noqa: BLE001
        pass  # hors ligne : le cache fait le travail, la veille continue
    _memo = dict(valeurs)
    return valeurs


def ecrire(modifs: dict[str, Any]) -> dict[str, Any]:
    """Applique des modifications. Le cache local est ecrit AVANT le reseau.

    Ainsi une panne reseau ne fait jamais perdre une saisie : elle est deja sur
    disque et repartira a la prochaine ecriture reussie.
    """
    for cle in modifs:
        if any(interdit in cle.lower() for interdit in CLES_INTERDITES):
            raise ValueError(
                f"'{cle}' ne peut pas entrer dans les reglages : l'etat est versionne. "
                "Les secrets restent dans alertes_secrets.json et les secrets GitHub."
            )

    global _memo
    valeurs = lire()
    valeurs.update(modifs)
    _cache_ecrit(valeurs)
    _memo = dict(valeurs)  # nos propres ecritures sont immediatement visibles

    try:
        etat, sha = veille_depot.lire()
        etat["reglages"] = valeurs
        veille_depot.ecrire(etat, sha, "reglages")
    except Exception:  # noqa: BLE001
        pass  # conserve en cache, repousse a la prochaine ecriture reussie
    return valeurs


def rafraichir() -> dict[str, Any]:
    """Recopie l'etat partage dans le cache local. Appele au debut d'un run local."""
    invalider()
    valeurs = lire()
    _cache_ecrit(valeurs)
    return valeurs
