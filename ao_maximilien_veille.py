"""Veilleur Maximilien : c'est ce que GitHub Actions execute.

Scrape pagine -> tri -> comparaison a l'etat -> un email par nouvel AO -> etat.
Aucune regle metier ici : le tri est dans ao_pertinence, l'etat dans veille_etat,
le scrape dans ao_maximilien_scrape. Ce module ne fait qu'assembler.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

import ao_maximilien_scrape as scrape
import ao_pertinence
import veille_etat
from ao_alertes import charger_config_smtp, envoyer_email

logger = logging.getLogger(__name__)

BASE = Path(__file__).resolve().parent
ETAT_PATH = Path(os.environ.get("CHRUTH_VEILLE_ETAT") or (BASE / "etat" / "veille.json"))


def collecter() -> list[dict[str, Any]]:
    """Toutes les consultations publiques, toutes pages, dedupliquees.

    On rattache `objet_desc` a l'AO : _to_ao ne le transporte pas (il ne produit
    que des colonnes de la base), or le tri en a besoin comme detail. Meme raison
    pour les alias `url` / `score`, noms sous lesquels l'etat et l'email les lisent.
    """
    session = scrape._session()
    brutes: dict[str, dict[str, Any]] = {}
    for kw in scrape.KEYWORDS:
        try:
            for html in scrape._pages_resultats(session, kw):
                for b in scrape._parse_resultats(html):
                    brutes.setdefault(b["cid"], b)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Recherche '%s' echouee : %s", kw, exc)

    aos = []
    for b in brutes.values():
        ao = scrape._to_ao(b)
        ao["objet_desc"] = b.get("objet_desc", "")
        ao["url"] = ao.get("url_avis", "")
        ao["score"] = ao.get("score_chruth", "")
        aos.append(ao)
    return aos


def construire_email_ao(ao: dict[str, Any], verdict) -> tuple[str, str, str]:
    objet = str(ao.get("objet") or "Consultation Maximilien")
    ville = str(ao.get("ville") or "")
    sujet = f"[Maximilien] {objet[:60]}" + (f" — {ville}" if ville else "")

    champs = [
        ("Acheteur", ao.get("acheteur")),
        ("Ville", f"{ville} ({ao.get('departement') or '--'})"),
        ("Publié le", ao.get("date_publication") or "non precisee"),
        ("Date limite", ao.get("date_limite") or "non precisee"),
        ("Procedure", ao.get("procedure")),
        ("Priorite", f"{ao.get('priorite')} ({ao.get('score')})"),
        ("Tri", f"{verdict.verdict} — {verdict.motif} [{verdict.etage}]"),
    ]
    url = str(ao.get("url") or "")

    lignes_html = "".join(
        f"<tr><td style='padding:4px 10px 4px 0'><b>{escape(k)}</b></td>"
        f"<td style='padding:4px 0'>{escape(str(v or ''))}</td></tr>"
        for k, v in champs
    )
    html = (
        f"<p style='font-size:15px'><b>{escape(objet)}</b></p>"
        f"<table style='border-collapse:collapse;font-size:14px'>{lignes_html}</table>"
        f"<p><a href='{escape(url)}'>Ouvrir la consultation sur Maximilien</a></p>"
    )
    texte = objet + "\n" + "\n".join(f"{k} : {v or ''}" for k, v in champs) + f"\n{url}\n"
    return sujet, html, texte


def _envoyer(sujet: str, html: str, texte: str) -> None:
    """Indirection deliberee : les tests la remplacent, aucun SMTP n'est joue."""
    envoyer_email(sujet, html, texte, charger_config_smtp())


def veiller(etat_path: Path | None = None, envoyer: bool = True, client=None) -> int:
    """Un passage de veille. Renvoie le nombre d'AO effectivement notifies."""
    chemin = Path(etat_path or ETAT_PATH)
    etat = veille_etat.charger(chemin)
    guide = etat.get("guide_messages", "")
    corrections = [
        {"objet": e.get("objet", ""), "verdict": (e.get("correction_humaine") or {}).get("verdict", "")}
        for e in etat.get("aos", {}).values()
        if e.get("correction_humaine")
    ]

    notifies = 0
    for ao in veille_etat.nouveaux(etat, collecter()):
        verdict = ao_pertinence.trier(ao.get("objet", ""), ao.get("objet_desc", ""),
                                      guide=guide, client=client, corrections=corrections)
        notifie_le = None
        if verdict.verdict == ao_pertinence.PERTINENT and envoyer:
            try:
                _envoyer(*construire_email_ao(ao, verdict))
                notifie_le = datetime.now(timezone.utc).isoformat()
                notifies += 1
            except Exception as exc:  # noqa: BLE001
                # On n'enregistre PAS l'AO : il sera retente au run suivant.
                logger.error("Envoi echoue pour %s : %s", ao.get("id_ao"), exc)
                continue
        veille_etat.ajouter(etat, ao, verdict, notifie_le)

    veille_etat.enregistrer(etat, chemin)
    return notifies


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    if os.environ.get("CHRUTH_NOTIFICATIONS", "").strip().upper() == "OFF":
        print("[VEILLE] suspendue (CHRUTH_NOTIFICATIONS=OFF)")
        return 0
    n = veiller()
    print(f"[VEILLE-MAXIMILIEN] {n} AO notifies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
