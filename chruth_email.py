"""Utilitaires email CHRUTH.

Compatible avec la configuration existante :
- alertes_secrets.json : smtp_user / smtp_password / host / port
- destinataires.txt : une adresse par ligne

Les secrets restent locaux et ne sont pas copies dans les packs de livraison.
"""
from __future__ import annotations

import json
import re
from email.message import EmailMessage
from pathlib import Path
from smtplib import SMTP
from typing import Any

from ao_config import (
    ALERTE_DESTINATAIRES_FILE,
    ALERTE_SECRETS_FILE,
    ALERTE_SMTP_HOST,
    ALERTE_SMTP_PORT,
)


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(str(value or "").strip()))


def read_secrets(path: Path = ALERTE_SECRETS_FILE) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_secrets(
    smtp_user: str,
    smtp_password: str,
    host: str = ALERTE_SMTP_HOST,
    port: int = ALERTE_SMTP_PORT,
    path: Path = ALERTE_SECRETS_FILE,
) -> None:
    smtp_user = str(smtp_user or "").strip()
    smtp_password = str(smtp_password or "").strip()
    if not valid_email(smtp_user):
        raise ValueError("Adresse expediteur invalide.")
    if not smtp_password:
        raise ValueError("Mot de passe d'application manquant.")
    data = read_secrets(path)
    data.update({
        "smtp_user": smtp_user,
        "smtp_password": smtp_password,
        "host": host or ALERTE_SMTP_HOST,
        "port": int(port or ALERTE_SMTP_PORT),
    })
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_recipients(path: Path = ALERTE_DESTINATAIRES_FILE) -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    emails = []
    for line in p.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value and not value.startswith("#") and valid_email(value):
            emails.append(value)
    return list(dict.fromkeys(emails))


def save_recipients(emails: list[str] | str, path: Path = ALERTE_DESTINATAIRES_FILE) -> list[str]:
    if isinstance(emails, str):
        raw = re.split(r"[,;\n]", emails)
    else:
        raw = emails
    clean = []
    for email in raw:
        value = str(email or "").strip()
        if value:
            if not valid_email(value):
                raise ValueError(f"Adresse destinataire invalide : {value}")
            clean.append(value)
    clean = list(dict.fromkeys(clean))
    if not clean:
        raise ValueError("Aucun destinataire valide.")
    header = "# Destinataires CHRUTH - une adresse email par ligne.\n"
    Path(path).write_text(header + "\n".join(clean) + "\n", encoding="utf-8")
    return clean


def config_ready() -> tuple[bool, str]:
    data = read_secrets()
    user = str(data.get("smtp_user") or "").strip()
    password = str(data.get("smtp_password") or "").strip()
    if not valid_email(user):
        return False, "Adresse expediteur manquante ou invalide."
    if not password:
        return False, "Mot de passe d'application manquant."
    return True, user


def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: str | None = None,
    secrets_path: Path = ALERTE_SECRETS_FILE,
) -> None:
    to_email = str(to_email or "").strip()
    subject = str(subject or "").strip()
    body = str(body or "").strip()
    if not valid_email(to_email):
        raise ValueError("Adresse destinataire invalide.")
    if not subject:
        raise ValueError("Sujet manquant.")
    if not body:
        raise ValueError("Message vide.")

    data = read_secrets(secrets_path)
    smtp_user = str(data.get("smtp_user") or "").strip()
    smtp_password = str(data.get("smtp_password") or "").strip()
    host = str(data.get("host") or ALERTE_SMTP_HOST)
    port = int(data.get("port") or ALERTE_SMTP_PORT)
    if not valid_email(smtp_user) or not smtp_password:
        raise ValueError("Configuration SMTP incomplete. Renseigne Gmail + mot de passe d'application.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    with SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)
