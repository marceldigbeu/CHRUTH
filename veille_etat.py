"""Etat de la veille Maximilien : anti-doublon, suivi et guide.

Un simple fichier JSON, versionne sur la branche ao-state. Lisible, diff propre,
quelques kilo-octets : delibere, contre une base SQLite binaire recommittee a
chaque run. Ce module ne connait ni le tri, ni le web, ni l'email.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ETAT_VERSION = 1

CHAMPS_AO = ("objet", "acheteur", "ville", "departement", "date_publication",
             "date_limite", "procedure", "url", "score", "priorite")

# Statuts de suivi, alignes sur le CRM deja present dans app_messages.
TRAITEMENTS = ("nouveau", "a_traiter", "repondu", "abandonne")
VERDICTS = ("PERTINENT", "REJETE")


def _vide() -> dict[str, Any]:
    return {"version": ETAT_VERSION, "maj_le": "", "aos": {}, "guide_messages": ""}


def charger(chemin: Path) -> dict[str, Any]:
    """Etat sur disque, ou structure vide si absent/illisible.

    Un etat corrompu ne doit jamais arreter la veille : au pire on renotifie.
    """
    p = Path(chemin)
    if not p.exists():
        return _vide()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return _vide()
    if not isinstance(data, dict) or "aos" not in data:
        return _vide()
    data.setdefault("version", ETAT_VERSION)
    data.setdefault("guide_messages", "")
    data.setdefault("maj_le", "")
    return data


def enregistrer(etat: dict[str, Any], chemin: Path) -> None:
    p = Path(chemin)
    p.parent.mkdir(parents=True, exist_ok=True)
    etat["maj_le"] = datetime.now(timezone.utc).isoformat()
    p.write_text(json.dumps(etat, ensure_ascii=False, indent=2, sort_keys=True),
                 encoding="utf-8")


def nouveaux(etat: dict[str, Any], aos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    connus = set(etat.get("aos", {}))
    return [a for a in aos if str(a.get("id_ao")) not in connus]


def ajouter(etat: dict[str, Any], ao: dict[str, Any], verdict,
            notifie_le: str | None = None) -> None:
    """Enregistre un AO et son verdict. N'ecrase jamais une correction humaine."""
    id_ao = str(ao.get("id_ao"))
    ancien = etat.setdefault("aos", {}).get(id_ao, {})
    entree = {c: ao.get(c, "") for c in CHAMPS_AO}
    entree.update({
        "vu_le": ancien.get("vu_le") or datetime.now(timezone.utc).isoformat(),
        "tri": {"verdict": verdict.verdict, "etage": verdict.etage, "motif": verdict.motif,
                "terme": getattr(verdict, "terme", "")},
        "correction_humaine": ancien.get("correction_humaine"),
        "traitement": ancien.get("traitement", "nouveau"),
        "notifie_le": notifie_le if notifie_le is not None else ancien.get("notifie_le"),
        "lu": ancien.get("lu", False),
    })
    etat["aos"][id_ao] = entree


# --- Ecritures humaines ----------------------------------------------------

def _entree(etat: dict[str, Any], id_ao: str) -> dict[str, Any]:
    aos = etat.setdefault("aos", {})
    if id_ao not in aos:
        raise KeyError(f"AO inconnu de l'etat : {id_ao}")
    return aos[id_ao]


def corriger(etat: dict[str, Any], id_ao: str, verdict: str, par: str = "app") -> None:
    """Enregistre un jugement humain. Il prime ensuite sur le tri, definitivement."""
    if verdict not in VERDICTS:
        raise ValueError(f"verdict inconnu : {verdict} (attendus : {VERDICTS})")
    _entree(etat, id_ao)["correction_humaine"] = {
        "verdict": verdict,
        "le": datetime.now(timezone.utc).isoformat(),
        "par": par,
    }


def verdict_effectif(entree: dict[str, Any]) -> str:
    """Verdict qui fait foi : la correction humaine d'abord, le tri ensuite."""
    correction = entree.get("correction_humaine") or {}
    if correction.get("verdict"):
        return correction["verdict"]
    return (entree.get("tri") or {}).get("verdict", "")


def marquer_lu(etat: dict[str, Any], id_ao: str, lu: bool = True) -> None:
    _entree(etat, id_ao)["lu"] = bool(lu)


def definir_traitement(etat: dict[str, Any], id_ao: str, statut: str) -> None:
    if statut not in TRAITEMENTS:
        raise ValueError(f"statut inconnu : {statut} (attendus : {TRAITEMENTS})")
    _entree(etat, id_ao)["traitement"] = statut


def notifications_actives(etat: dict[str, Any]) -> bool:
    """Les emails partent-ils ? Actives par defaut : un etat muet serait un piege.

    La verite est dans le bloc `reglages` de l'etat, celui que lisent aussi la page
    Reglages et le pipeline local. L'ancienne cle de premier niveau reste lue en
    repli, le temps que les etats en service migrent — et une coupure qu'elle porte
    l'emporte : un coupe-circuit deja pose ne se rouvre jamais tout seul.

    Pas d'import de `reglages` ici : ce serait une boucle
    (reglages -> veille_depot -> veille_etat). L'etat porte deja le bloc.
    """
    reg = etat.get("reglages") or {}
    ancienne = etat.get("notifications")
    if ancienne is False:
        return False
    if "notifications" in reg:
        return bool(reg["notifications"])
    return True if ancienne is None else bool(ancienne)


def definir_notifications(etat: dict[str, Any], actif: bool) -> None:
    """Interrupteur des emails. La collecte et le tri continuent quoi qu'il arrive :
    en pause, les AO entrent dans l'etat sans email et repartent a la reactivation.

    Ecrit dans le bloc `reglages` et efface l'ancienne cle : la laisser derriere
    soi recreerait les deux commutateurs divergents qu'on vient de fusionner.
    """
    etat.setdefault("reglages", {})["notifications"] = bool(actif)
    etat.pop("notifications", None)


def definir_guide(etat: dict[str, Any], texte: str) -> None:
    """Guide qui pilote la redaction des messages ET le prompt de tri (spec 6.3)."""
    etat["guide_messages"] = texte or ""
