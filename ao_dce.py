from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import requests

PROFIL_DOMAINS = (
    "marches-publics.info", "marches-publics.gouv.fr", "aws-achat", "achatpublic",
    "e-marchespublics", "megalis", "maximilien", "atexo", "dematis", "klekoon",
    "xmarches", "poste-marches", "synapse-entreprises",
)

_URL_RE = re.compile(r'https?://[^\s"\\\],<>\)]+')


def _collect_urls(obj: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(obj, str):
        urls.extend(_URL_RE.findall(obj))
    elif isinstance(obj, dict):
        for value in obj.values():
            urls.extend(_collect_urls(value))
    elif isinstance(obj, list):
        for value in obj:
            urls.extend(_collect_urls(value))
    return urls


def _parse_donnees(donnees: Any) -> Any:
    if isinstance(donnees, (dict, list)):
        return donnees
    if not donnees:
        return {}
    try:
        return json.loads(donnees)
    except (ValueError, TypeError):
        return {"_raw": str(donnees)}


def extract_dce_links(donnees: Any) -> dict:
    urls = [u.rstrip(".,;") for u in _collect_urls(_parse_donnees(donnees))]
    urls = list(dict.fromkeys(u for u in urls if "boamp" not in u.lower()))
    direct = [u for u in urls if u.lower().split("?")[0].endswith((".pdf", ".zip"))]
    profil = [u for u in urls if any(d in u.lower() for d in PROFIL_DOMAINS)]
    best_list = direct or profil or urls
    return {
        "url_dce": best_list[0] if best_list else "",
        "url_profil_acheteur": profil[0] if profil else "",
    }


_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_TEL_RE = re.compile(r"(?:\+33|0)\s*[1-9](?:[\s.\-]*\d{2}){4}")
_AMOUNT_RE = re.compile(r"(\d[\d\s. ]{2,}\d)\s*(?:€|eur|euros)", re.IGNORECASE)
_BUDGET_CTX = ("estim", "valeur", "montant", "budget", "accord-cadre", "maximum")
_GENERIC_EMAIL = ("no-reply", "noreply", "ne-pas-repondre", "nepasrepondre")


def _parse_amount(raw: str) -> float | None:
    digits = re.sub(r"[^\d]", "", raw)
    return float(digits) if digits else None


def extract_fields_from_text(text: str) -> dict:
    text = text or ""
    low = text.lower()

    emails = [e for e in _EMAIL_RE.findall(text)
              if not any(g in e.lower() for g in _GENERIC_EMAIL)]
    tels = _TEL_RE.findall(text)

    budget = ""
    for match in _AMOUNT_RE.finditer(text):
        context = low[max(0, match.start() - 90):match.start()]
        if any(k in context for k in _BUDGET_CTX):
            value = _parse_amount(match.group(1))
            if value and value >= 1000:
                budget = str(int(value))
                break

    contact = ""
    cm = re.search(r"(?:contact|correspondant|responsable)\s*[:\-]\s*([A-Z][\w .'\-]{2,40})", text)
    if cm:
        contact = cm.group(1).strip()

    resume = " ".join(text.split())[:300]
    return {
        "dce_email": emails[0] if emails else "",
        "dce_tel": tels[0].strip() if tels else "",
        "dce_budget": budget,
        "dce_contact": contact,
        "dce_resume": resume,
        "dce_texte_extrait": text[:8000],
    }


REQUEST_TIMEOUT = 20
USER_AGENT = "CHRUTH-AO-Pipeline/1.0"


def match_manual_pdf(id_ao: str, dce_manuel_dir: Path) -> Path | None:
    dce_manuel_dir = Path(dce_manuel_dir)
    if not id_ao or not dce_manuel_dir.exists():
        return None
    for path in sorted(dce_manuel_dir.glob("*.pdf")):
        if path.name.startswith(str(id_ao)):
            return path
    return None


def extract_pdf_text(path: Path) -> str:
    path = Path(path)
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages)
    except Exception:
        pass
    try:
        import fitz
        doc = fitz.open(path)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception:
        return ""


def try_download_direct(url: str, dest_dir: Path, filename: str | None = None) -> Path | None:
    if not url or url.lower().split("?")[0].rsplit(".", 1)[-1] not in ("pdf", "zip"):
        return None
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception:
        return None
    ctype = resp.headers.get("content-type", "").lower()
    body = resp.content
    is_pdf = "pdf" in ctype or body[:4] == b"%PDF"
    is_zip = "zip" in ctype or body[:2] == b"PK"
    if not (is_pdf or is_zip):
        return None
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    ext = "pdf" if is_pdf else "zip"
    out = dest_dir / (filename or f"download.{ext}")
    out.write_bytes(body)
    return out
