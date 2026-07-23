from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from html import escape
from pathlib import Path
from smtplib import SMTP
from typing import Any

from ao_config import (
    AO_DB_PATH,
    ALERTE_DESTINATAIRES_FILE,
    ALERTE_PRIORITES,
    ALERTE_SECRETS_FILE,
    ALERTE_SMTP_HOST,
    ALERTE_SMTP_PORT,
    LOG_DIR,
    notifications_actives,
)
from ao_db import connect, init_db
import ao_messages


def _lire_secrets() -> dict[str, Any]:
    p = Path(ALERTE_SECRETS_FILE)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def charger_destinataires(secrets: dict[str, Any] | None = None) -> list[str]:
    """Liste des destinataires (dedupliquee). Priorite :
    1) destinataires.txt (une adresse par ligne ; lignes vides / # ignorees) ;
    2) env CHRUTH_ALERTE_DEST ; 3) 'destinataire' de alertes_secrets.json. (separateurs , ou ;)"""
    f = Path(ALERTE_DESTINATAIRES_FILE)
    if f.exists():
        lignes = [l.strip() for l in f.read_text(encoding="utf-8").splitlines()]
        emails = [l for l in lignes if l and not l.startswith("#") and "@" in l]
        if emails:
            return list(dict.fromkeys(emails))
    secrets = secrets if secrets is not None else _lire_secrets()
    brut = os.environ.get("CHRUTH_ALERTE_DEST") or str(secrets.get("destinataire") or "")
    emails = [e.strip() for e in re.split(r"[,;]", brut) if e.strip()]
    return list(dict.fromkeys(emails))


def charger_config_smtp() -> dict[str, Any]:
    """Identifiants SMTP (env > secrets) + liste de destinataires. Leve si incomplet."""
    secrets = _lire_secrets()
    user = os.environ.get("CHRUTH_SMTP_USER") or secrets.get("smtp_user")
    password = os.environ.get("CHRUTH_SMTP_PASSWORD") or secrets.get("smtp_password")
    destinataires = charger_destinataires(secrets)
    if not (user and password):
        raise ValueError(
            "Config SMTP incomplète : définir CHRUTH_SMTP_USER / CHRUTH_SMTP_PASSWORD "
            f"(ou les renseigner dans {ALERTE_SECRETS_FILE})."
        )
    if not destinataires:
        raise ValueError(
            f"Aucun destinataire : ajouter au moins une adresse dans {ALERTE_DESTINATAIRES_FILE} "
            "(une par ligne) ou le champ 'destinataire' de alertes_secrets.json."
        )
    return {"smtp_user": user, "smtp_password": password, "destinataires": destinataires,
            "host": ALERTE_SMTP_HOST, "port": ALERTE_SMTP_PORT}


def nouveaux_ao_a_alerter(db_path: Path = AO_DB_PATH) -> list[dict[str, Any]]:
    """AO CHAUD/TIEDE jamais alertes, tries par score decroissant."""
    init_db(db_path)
    placeholders = ",".join("?" for _ in ALERTE_PRIORITES)
    sql = (
        f"SELECT * FROM ao_records "
        f"WHERE priorite IN ({placeholders}) "
        f"AND (alerte_envoyee IS NULL OR alerte_envoyee = '') "
        f"AND COALESCE(verdict_tri, '') <> 'REJETE' "
        f"ORDER BY CAST(score_chruth AS INTEGER) DESC"
    )
    with connect(db_path) as conn:
        rows = conn.execute(sql, tuple(ALERTE_PRIORITES)).fetchall()
    return [dict(r) for r in rows]


def calculer_verdicts_manquants(db_path: Path = AO_DB_PATH, guide: str = "",
                                client=None) -> int:
    """Trie les AO qui n'ont pas encore de verdict. Renvoie le nombre traites.

    Marque, ne supprime jamais : les AO rejetes restent visibles dans le cockpit.
    """
    import ao_pertinence

    init_db(db_path)
    with connect(db_path) as conn:
        lignes = conn.execute(
            "SELECT id_ao, objet, resume_commercial FROM ao_records "
            "WHERE verdict_tri IS NULL OR verdict_tri = ''"
        ).fetchall()

        traites = 0
        for ligne in lignes:
            r = dict(ligne)
            v = ao_pertinence.trier(r.get("objet") or "", r.get("resume_commercial") or "",
                                    guide=guide, client=client)
            conn.execute("UPDATE ao_records SET verdict_tri=?, motif_tri=? WHERE id_ao=?",
                         (v.verdict, v.motif, r["id_ao"]))
            traites += 1
        conn.commit()
    return traites


def creneau_label(now: datetime) -> str:
    return "matin" if now.hour < 12 else "après-midi"


def _budget_affiche(r: dict[str, Any]) -> str:
    val = str(r.get("budget_annuel_eur") or "").strip()
    if val in ("", "nan"):
        val = str(r.get("budget_estime_eur") or "").strip()
    return val if val not in ("", "nan") else "à vérifier"


def _brouillons_pour(records: list[dict[str, Any]], cache_path=None) -> dict[str, dict]:
    """Brouillon {email, script} par id_ao : cache ao_messages.json (rechauffe par le
    pipeline) sinon repli deterministe. Aucun appel LLM (envoi non bloquant)."""
    cache = ao_messages._charger_cache(cache_path or ao_messages.CACHE_PATH)
    out: dict[str, dict] = {}
    for r in records:
        key = str(r.get("id_ao") or "")
        out[key] = cache.get(key) or ao_messages._repli(r)
    return out


def construire_email(records: list[dict[str, Any]], now: datetime,
                     brouillons: dict[str, dict] | None = None) -> tuple[str, str, str]:
    creneau = creneau_label(now)
    sujet = f"CHRUTH - {len(records)} nouveaux AO nettoyage IDF ({creneau} {now.strftime('%d/%m')})"

    cols = [
        ("objet", "Objet"), ("acheteur", "Acheteur"), ("secteur", "Secteur"),
        ("categorie", "Catégorie"), ("ville", "Ville"),
        ("date_publication", "Publication"), ("date_limite", "Date limite"),
        ("priorite", "Priorité"),
    ]
    head = "".join(f"<th style='text-align:left;padding:4px;border:1px solid #ccc'>{escape(label)}</th>" for _, label in cols)
    head += "<th style='text-align:left;padding:4px;border:1px solid #ccc'>Budget (EUR)</th>"
    head += "<th style='text-align:left;padding:4px;border:1px solid #ccc'>DCE</th>"
    head += "<th style='text-align:left;padding:4px;border:1px solid #ccc'>Avis BOAMP</th>"

    lignes_html = []
    lignes_txt = []
    for r in records:
        cells = "".join(f"<td style='padding:4px;border:1px solid #ccc'>{escape(str(r.get(key) or ''))}</td>" for key, _ in cols)
        cells += f"<td style='padding:4px;border:1px solid #ccc'>{escape(_budget_affiche(r))}</td>"
        dce = str(r.get("url_dce") or "").strip()
        avis = str(r.get("url_avis") or "").strip()
        lien_dce = f"<a href='{escape(dce)}'>DCE</a>" if dce else "-"
        lien_avis = f"<a href='{escape(avis)}'>avis</a>" if avis else "-"
        cells += f"<td style='padding:4px;border:1px solid #ccc'>{lien_dce}</td>"
        cells += f"<td style='padding:4px;border:1px solid #ccc'>{lien_avis}</td>"
        lignes_html.append(f"<tr>{cells}</tr>")
        lignes_txt.append(
            f"- [{r.get('priorite')}] {r.get('objet')} | {r.get('acheteur')} | {r.get('ville')} | "
            f"limite {r.get('date_limite')} | budget {_budget_affiche(r)} | DCE: {dce or '-'}"
        )

    if brouillons is None:
        brouillons = _brouillons_pour(records)
    blocs_html, blocs_txt = [], []
    for r in records:
        b = brouillons.get(str(r.get("id_ao") or "")) or {}
        titre = f"{r.get('objet', '')} — {r.get('acheteur', '')}"
        blocs_html.append(
            "<hr><h3 style='font-family:sans-serif;font-size:14px'>" + escape(titre) + "</h3>"
            "<p style='font-family:sans-serif;font-size:13px;margin:2px 0'><b>Email :</b></p>"
            "<pre style='white-space:pre-wrap;font-family:sans-serif;font-size:13px'>"
            + escape(b.get("email", "")) + "</pre>"
            "<p style='font-family:sans-serif;font-size:13px;margin:2px 0'><b>Script d'appel :</b></p>"
            "<pre style='white-space:pre-wrap;font-family:sans-serif;font-size:13px'>"
            + escape(b.get("script", "")) + "</pre>"
        )
        blocs_txt.append(
            "\n--- BROUILLON : " + titre + " ---\nEMAIL :\n" + b.get("email", "")
            + "\n\nSCRIPT :\n" + b.get("script", "")
        )

    html = (
        f"<p>Bonjour,</p><p>{len(records)} nouveaux appels d'offres nettoyage Île-de-France "
        f"(priorité CHAUD/TIEDE) détectés ce {creneau} :</p>"
        f"<table style='border-collapse:collapse;font-family:sans-serif;font-size:13px'>"
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(lignes_html)}</tbody></table>"
        f"<h2 style='font-family:sans-serif;font-size:15px'>Brouillons de messages (à relire)</h2>"
        f"{''.join(blocs_html)}"
        f"<p>-- Veille automatique CHRUTH</p>"
    )
    texte = (
        f"{len(records)} nouveaux AO nettoyage IDF (CHAUD/TIEDE) - {creneau} {now.strftime('%d/%m')}\n\n"
        + "\n".join(lignes_txt)
        + "\n\n=== BROUILLONS DE MESSAGES (à relire) ==="
        + "".join(blocs_txt)
        + "\n\n-- Veille automatique CHRUTH"
    )
    return sujet, html, texte


def envoyer_email(sujet: str, html: str, texte: str, cfg: dict[str, Any]) -> None:
    msg = EmailMessage()
    msg["Subject"] = sujet
    msg["From"] = cfg["smtp_user"]
    # To = compte expediteur (copie/monitoring) ; les destinataires sont en Cci (ne se voient pas).
    msg["To"] = cfg["smtp_user"]
    msg["Bcc"] = ", ".join(cfg["destinataires"])
    msg.set_content(texte)
    msg.add_alternative(html, subtype="html")
    with SMTP(cfg["host"], cfg["port"]) as smtp:
        smtp.starttls()
        smtp.login(cfg["smtp_user"], cfg["smtp_password"])
        smtp.send_message(msg)


def marquer_alertes(ids: list[str], db_path: Path = AO_DB_PATH) -> None:
    stamp = datetime.now(timezone.utc).isoformat()
    with connect(db_path) as conn:
        conn.executemany("UPDATE ao_records SET alerte_envoyee=? WHERE id_ao=?", [(stamp, i) for i in ids])
        conn.commit()


def envoyer_alertes(db_path: Path = AO_DB_PATH, now: datetime | None = None) -> int:
    now = now or datetime.now()
    calculer_verdicts_manquants(db_path)
    records = nouveaux_ao_a_alerter(db_path)
    if not records:
        return 0
    cfg = charger_config_smtp()
    sujet, html, texte = construire_email(records, now)
    envoyer_email(sujet, html, texte, cfg)
    marquer_alertes([r["id_ao"] for r in records], db_path)
    return len(records)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not notifications_actives():
        print("[ALERTE] Notifications désactivées (bouton OFF / Parametres!B2) -> aucun email envoyé.")
        return 0
    try:
        n = envoyer_alertes()
    except Exception as exc:  # noqa: BLE001
        print(f"[ALERTE] échec : {exc}")
        return 1
    print(f"[ALERTE] {n} AO envoyés" if n else "[ALERTE] aucun nouveau AO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
