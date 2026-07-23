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

CHAMPS_AO = ("objet", "acheteur", "ville", "departement", "date_limite",
             "procedure", "url", "score", "priorite")


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
        "tri": {"verdict": verdict.verdict, "etage": verdict.etage, "motif": verdict.motif},
        "correction_humaine": ancien.get("correction_humaine"),
        "traitement": ancien.get("traitement", "nouveau"),
        "notifie_le": notifie_le if notifie_le is not None else ancien.get("notifie_le"),
        "lu": ancien.get("lu", False),
    })
    etat["aos"][id_ao] = entree
