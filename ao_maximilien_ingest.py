from __future__ import annotations

import hashlib
import imaplib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from pathlib import Path
from typing import Any

from ao_config import (
    ALERTE_SECRETS_FILE,
    BASE_DIR,
    LOG_DIR,
)
from ao_db import upsert_records
from ao_extract_fields import extract_basic_fields, normalize_text
from ao_scoring import compute_ao_score

logger = logging.getLogger(__name__)

MAXIMILIEN_SENDERS = [
    "maximilien.fr",
    "marches.maximilien.fr",
    "atexo.com",
    "ne-pas-repondre@",
]

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
MAX_EMAILS_TO_SCAN = 50
SCAN_LOOKBACK_DAYS = 7
LINK_RE = re.compile(r"https?://marches\.maximilien\.fr[^\s<>\"']+")
LINK_RE_ALT = re.compile(r"https?://www\.maximilien\.fr[^\s<>\"']+")


def _lire_secrets() -> dict[str, Any]:
    p = Path(ALERTE_SECRETS_FILE)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _is_maximilien_email(msg: Any) -> bool:
    sender = str(msg.get("From", "")).lower()
    subject = str(msg.get("Subject", "")).lower()
    for s in MAXIMILIEN_SENDERS:
        if s in sender:
            return True
    if "maximilien" in subject:
        return True
    body = _get_body(msg)
    if "maximilien" in body.lower():
        return True
    return False


def _get_body(msg: Any) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    return part.get_payload(decode=True).decode("utf-8", errors="replace")
                except Exception:
                    continue
            if ctype == "text/html":
                try:
                    return part.get_payload(decode=True).decode("utf-8", errors="replace")
                except Exception:
                    continue
    try:
        return msg.get_payload(decode=True).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extraire_liens(body: str) -> list[str]:
    liens = LINK_RE.findall(body) + LINK_RE_ALT.findall(body)
    propres = []
    for lien in liens:
        lien = lien.rstrip(".)>\"'")
        if lien not in propres:
            propres.append(lien)
    return propres


def _extraire_acheteur(body: str, subject: str) -> str:
    text = normalize_text(body)
    for pattern in [
        r"publi[ée]\s*(?:par|pour)\s*[:\s]+([^\n,.]+)",
        r"acheteur[:\s]+([^\n,.]+)",
        r"organisme[:\s]+([^\n,.]+)",
    ]:
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip().title()
    return ""


def _extraire_date_limite(body: str) -> str:
    for pattern in [
        r"date\s*limite[:\s]+(\d{2}/\d{2}/\d{4})",
        r"date\s*limite[:\s]+(\d{4}-\d{2}-\d{2})",
    ]:
        m = re.search(pattern, body, re.I)
        if m:
            return m.group(1)
    return ""


def _categoriser_depuis_objet(objet: str) -> str:
    t = normalize_text(objet)
    if any(m in t for m in ["vitre", "vitrerie"]):
        return "Vitres"
    if any(m in t for m in ["bureau", "bureaux"]):
        return "Bureaux"
    return "Batiments/Locaux"


def _detecter_secteur(objet: str, acheteur: str) -> str:
    from ao_config import AO_SECTEURS
    t = normalize_text(f"{objet} {acheteur}")
    for secteur, mots in AO_SECTEURS.items():
        if any(m in t for m in mots):
            return secteur
    return "Autre"


def _generer_id_ao(url: str, objet: str) -> str:
    cle = f"MAXIMILIEN|{url}|{objet}"
    return "MX-" + hashlib.md5(cle.encode()).hexdigest()[:12]


def _email_to_ao(subject: str, body: str, url: str) -> dict[str, Any]:
    objet = subject.strip()
    if not objet:
        objet = "Consultation Maximilien"
    for prefix in ["alerte", "nouvel", "nouveau", "nouvelle", "consultation"]:
        if objet.lower().startswith(prefix):
            objet = objet[len(prefix):].strip().lstrip(" :,-")
    if not objet:
        objet = subject.strip()

    acheteur = _extraire_acheteur(body, subject)
    date_limite = _extraire_date_limite(body)
    categorie = _categoriser_depuis_objet(objet)
    secteur = _detecter_secteur(objet, acheteur)

    ao = {
        "source": "MAXIMILIEN",
        "id_ao": _generer_id_ao(url, objet),
        "objet": objet,
        "acheteur": acheteur,
        "url_avis": url,
        "url_dce": url,
        "date_limite": date_limite,
        "date_publication": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "categorie": categorie,
        "secteur": secteur,
        "budget_statut": "A_VERIFIER_BUDGET",
        "niveau_confiance": "30",
        "statut_extraction": "DCE_A_TELECHARGER",
        "mots_cles_detectes": ", ".join(
            kw for kw in ["nettoyage", "vitres", "entretien", "proprete", "hygiene"]
            if kw in normalize_text(objet)
        ),
    }

    score, priority, reasons = compute_ao_score(ao)
    ao["score_chruth"] = score
    ao["priorite"] = priority
    ao["raisons_scoring"] = reasons
    return ao


def ingerer_maximilien(
    secrets: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> int:
    secrets = secrets or _lire_secrets()
    user = secrets.get("smtp_user", "")
    password = secrets.get("smtp_password", "")
    if not user or not password:
        logger.warning("Pas d'identifiants SMTP/IMAP -> ingestion Maximilien ignorée")
        return 0

    logger.info(f"Connexion IMAP {user}...")
    ingeres = 0
    try:
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
            imap.login(user, password)
            imap.select("INBOX")

            depuis = datetime.now(timezone.utc).date()
            fmt = depuis.strftime("%d-%b-%Y")
            result, data = imap.search(None, f'(UNSEEN SINCE "{fmt}")')
            if result != "OK" or not data[0]:
                depuis_old = (depuis - timedelta(days=SCAN_LOOKBACK_DAYS)).strftime("%d-%b-%Y")
                result, data = imap.search(None, f'(UNSEEN SINCE "{depuis_old}")')
            if result != "OK" or not data[0]:
                logger.info("Aucun email non lu récent")
                return 0

            uids = data[0].split()
            logger.info(f"{len(uids)} emails non lus depuis {SCAN_LOOKBACK_DAYS} jours")
            a_traiter = uids[-MAX_EMAILS_TO_SCAN:]

            nouveaux: list[dict[str, Any]] = []
            for uid in a_traiter:
                result, data = imap.fetch(uid, "(RFC822)")
                if result != "OK":
                    continue
                msg = message_from_bytes(data[0][1])
                if not _is_maximilien_email(msg):
                    imap.store(uid, "+FLAGS", "\\Seen")
                    continue

                subject = str(msg.get("Subject", ""))
                body = _get_body(msg)
                urls = _extraire_liens(body)
                if not urls:
                    imap.store(uid, "+FLAGS", "\\Seen")
                    continue

                voie = urls[0]
                ao = _email_to_ao(subject, body, voie)

                ao_existant = False
                from ao_db import connect, AO_DB_PATH
                actuel = db_path or AO_DB_PATH
                with connect(actuel) as conn:
                    row = conn.execute(
                        "SELECT 1 FROM ao_records WHERE id_ao=?", (ao["id_ao"],)
                    ).fetchone()
                    if row:
                        ao_existant = True

                if not ao_existant:
                    nouveaux.append(ao)
                    logger.info(
                        f"  Nouveau MAXIMILIEN: {ao['objet'][:60]} | "
                        f"{ao['acheteur']} | {ao['categorie']}/{ao['secteur']}"
                    )

                imap.store(uid, "+FLAGS", "\\Seen")

            if nouveaux:
                inseres = upsert_records(nouveaux, db_path=db_path or AO_DB_PATH)
                logger.info(f"{inseres} AO Maximilien insérés dans la base")
                ingeres = inseres
            else:
                logger.info("Aucun nouvel AO Maximilien détecté")

    except Exception as exc:
        logger.error(f"Erreur ingestion Maximilien: {exc}")
        return 0

    return ingeres


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    n = ingerer_maximilien()
    print(f"[MAXIMILIEN] {n} AO ingérés")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
