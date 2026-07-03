from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, datetime
from typing import Any

import pandas as pd

from ao_config import (
    AO_BUDGET_MIN_EUR,
    AO_KEYWORDS_CORE,
    AO_KEYWORDS_SECONDARY,
    AO_CATEGORIE_VITRES,
    AO_CATEGORIE_BUREAUX,
    AO_CATEGORIE_BATIMENTS,
    AO_SECTEURS,
)


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.I)
PHONE_RE = re.compile(r"(?:(?:\+33|0)\s*[1-9](?:[\s.\-]?\d{2}){4})")
SIRET_RE = re.compile(r"\b\d{14}\b")
SIREN_RE = re.compile(r"\b\d{9}\b")


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def parse_json_field(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return {}
    text = str(value).strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        return {}


def flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten_text(v) for v in value)
    return str(value)


def iter_key_values(value: Any):
    if isinstance(value, dict):
        for key, val in value.items():
            yield str(key), val
            yield from iter_key_values(val)
    elif isinstance(value, list):
        for item in value:
            yield from iter_key_values(item)


def first_json_value(value: Any, keys: set[str]) -> str:
    for key, val in iter_key_values(value):
        clean_key = normalize_text(key).replace("_", "").replace("-", "")
        if clean_key in keys:
            if isinstance(val, (dict, list)):
                continue
            text = str(val or "").strip()
            if text:
                return text
    return ""


def normalize_department(value: Any) -> str:
    if isinstance(value, list):
        parts = [str(v).strip() for v in value if str(v).strip()]
        return ",".join(parts)
    text = str(value or "").strip()
    return text


def first_department(value: Any) -> str:
    text = normalize_department(value)
    return text.split(",")[0].strip() if text else ""


def parse_date(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return pd.to_datetime(text[:10], errors="coerce").date()
    except Exception:
        return None


def days_until(value: Any) -> int | None:
    parsed = parse_date(value)
    if parsed is None:
        return None
    return (parsed - date.today()).days


def is_active_notice(record: dict[str, Any]) -> bool:
    nature = normalize_text(record.get("nature"))
    nature_label = normalize_text(record.get("nature_libelle"))
    categorized = normalize_text(record.get("nature_categorise"))
    if "attribution" in nature or "resultat" in nature_label:
        return False
    if "appel" in nature or "appel" in nature_label or "appel" in categorized:
        return True
    deadline_days = days_until(record.get("datelimitereponse"))
    return deadline_days is not None and deadline_days >= 0


def find_keywords(text: str) -> tuple[list[str], list[str]]:
    normalized = normalize_text(text)
    core = [kw for kw in AO_KEYWORDS_CORE if keyword_in_text(kw, normalized)]
    secondary = [kw for kw in AO_KEYWORDS_SECONDARY if keyword_in_text(kw, normalized)]
    return core, secondary


def classify_categorie(text: str) -> str:
    """Classe l'AO en Vitres / Bureaux / Batiments / Mixte (priorite Vitres > Bureaux > Batiments)."""
    normalized = normalize_text(text)
    if any(keyword_in_text(kw, normalized) for kw in AO_CATEGORIE_VITRES):
        return "Vitres"
    if any(keyword_in_text(kw, normalized) for kw in AO_CATEGORIE_BUREAUX):
        return "Bureaux"
    if any(keyword_in_text(kw, normalized) for kw in AO_CATEGORIE_BATIMENTS):
        return "Batiments"
    return "Mixte/Autre"


def detect_secteur(acheteur: str, objet: str) -> str:
    """Detecte le secteur cible (bonus de score, jamais un filtre). 'Autre' par defaut."""
    normalized = normalize_text(f"{acheteur} {objet}")
    for secteur, markers in AO_SECTEURS.items():
        if any(keyword_in_text(marker, normalized) for marker in markers):
            return secteur
    return "Autre"


def keyword_in_text(keyword: str, normalized_text: str) -> bool:
    clean = normalize_text(keyword).strip()
    if not clean:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(clean).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
    return bool(re.search(pattern, normalized_text))


def parse_amount(raw: str) -> float:
    text = str(raw)
    text = text.replace("\u00a0", " ").replace(" ", "").replace(".", "")
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def extract_budget(text: str) -> tuple[float | None, str]:
    normalized = normalize_text(text)
    amounts = []

    for match in re.finditer(r"(\d+(?:[,.]\d+)?)\s*k\s*(?:eur|euros?|euro|€)", normalized):
        amounts.append(parse_amount(match.group(1)) * 1000)

    money_patterns = [
        r"(\d{1,3}(?:[\s\u00a0.]\d{3})+(?:,\d{1,2})?|\d{5,})(?:\s*)(?:eur|euros?|euro|€|ht|ttc)",
    ]
    for pattern in money_patterns:
        for match in re.finditer(pattern, normalized):
            amount = parse_amount(match.group(1))
            if amount >= 10_000:
                amounts.append(amount)

    if not amounts:
        return None, "A_VERIFIER_BUDGET"

    best = max(amounts)
    if best >= AO_BUDGET_MIN_EUR:
        return best, "BUDGET_EXPLICITE_OK"
    return best, "BUDGET_SOUS_SEUIL"


def extract_duree_mois(text: str) -> int | None:
    """Extrait une duree de marche en mois depuis le texte (ans -> *12). None si absente."""
    normalized = normalize_text(text)
    m = re.search(r"(\d{1,2})\s*(?:an|ans|annee|annees)\b", normalized)
    if m:
        return int(m.group(1)) * 12
    m = re.search(r"(\d{1,3})\s*mois\b", normalized)
    if m:
        return int(m.group(1))
    return None


def annualize_budget(total: float | None, duree_mois: int | None) -> tuple[float | None, bool]:
    """Retourne (budget_annuel, annualise?). Ramene le total a un taux annuel des qu'une
    duree positive est connue (y compris < 12 mois). Sinon, renvoie le total tel quel."""
    if total is None:
        return None, False
    if duree_mois and duree_mois > 0:
        annees = duree_mois / 12.0
        return round(total / annees), True
    return total, False


def extract_basic_fields(record: dict[str, Any]) -> dict[str, Any]:
    donnees = parse_json_field(record.get("donnees"))
    gestion = parse_json_field(record.get("gestion"))
    full_text = " ".join(
        [
            str(record.get("objet") or ""),
            str(record.get("nomacheteur") or ""),
            str(record.get("criteres") or ""),
            str(record.get("descripteur_libelle") or ""),
            str(record.get("procedure_libelle") or ""),
            str(record.get("nature_libelle") or ""),
            flatten_text(donnees),
            flatten_text(gestion),
        ]
    )

    email = first_json_value(donnees, {"email", "courriel", "adresseemail", "mail"})
    if not email:
        found = EMAIL_RE.findall(full_text)
        email = found[0] if found else ""

    telephone = first_json_value(donnees, {"telephone", "tel", "fax"})
    if not telephone:
        found = PHONE_RE.findall(full_text)
        telephone = found[0] if found else ""

    siret = first_json_value(donnees, {"siret", "codeidentificationnational"})
    if not siret:
        found = SIRET_RE.findall(full_text)
        siret = found[0] if found else ""
    siren = siret[:9] if len(siret) == 14 else ""
    if not siren:
        found = SIREN_RE.findall(full_text)
        siren = found[0] if found else ""

    ville = first_json_value(donnees, {"ville", "localite"})
    code_postal = first_json_value(donnees, {"cp", "codepostal", "codepostale"})
    adresse = first_json_value(donnees, {"adresse", "adressepostale", "lieu", "lieuexecution"})

    nom_contact = first_json_value(donnees, {"nom", "nomcontact", "contactnom"})
    prenom_contact = first_json_value(donnees, {"prenom", "prenomcontact", "contactprenom"})

    budget, budget_status = extract_budget(full_text)
    core_keywords, secondary_keywords = find_keywords(full_text)

    info_count = sum(bool(x) for x in [siret, email, telephone, adresse, ville, code_postal])
    confiance = min(100, 30 + info_count * 10 + len(core_keywords) * 8 + len(secondary_keywords) * 4)

    if info_count >= 4 and budget_status == "BUDGET_EXPLICITE_OK":
        statut = "INFO_COMPLETE"
    elif info_count >= 2:
        statut = "INFO_PARTIELLE"
    else:
        statut = "DCE_A_TELECHARGER"

    return {
        "siret_acheteur": siret,
        "siren_acheteur": siren,
        "nom_contact": nom_contact,
        "prenom_contact": prenom_contact,
        "email": email,
        "telephone": telephone,
        "adresse": adresse,
        "code_postal": code_postal,
        "ville": ville,
        "budget_estime_eur": budget,
        "budget_statut": budget_status,
        "mots_cles_detectes": ", ".join(dict.fromkeys(core_keywords + secondary_keywords)),
        "nb_infos_disponibles": info_count,
        "niveau_confiance": confiance,
        "statut_extraction": statut,
        "texte_extraction": full_text[:8000],
    }


def commercial_summary(row: dict[str, Any]) -> str:
    objet = str(row.get("objet") or "AO").strip()
    acheteur = str(row.get("acheteur") or "acheteur public").strip()
    ville = str(row.get("ville") or row.get("departement") or "").strip()
    budget = row.get("budget_estime_eur")
    budget_text = f"Budget detecte environ {int(budget):,} EUR".replace(",", " ") if budget else "Budget a verifier"
    return (
        f"{acheteur} publie un AO potentiellement pertinent pour CHRUTH : {objet}. "
        f"Zone : {ville or 'a verifier'}. {budget_text}. "
        "Verifier le lien source avant contact."
    )


def email_template(row: dict[str, Any]) -> str:
    acheteur = str(row.get("acheteur") or "votre structure").strip()
    objet = str(row.get("objet") or "votre appel d'offres").strip()
    return (
        "Bonjour,\n\n"
        f"Je me permets de vous contacter au sujet de votre appel d'offres : {objet}.\n\n"
        "CHRUTH accompagne les structures publiques et privées sur les besoins de nettoyage, "
        "d'entretien des locaux et d'organisation de prestations de service.\n\n"
        "Serait-il possible d'échanger rapidement afin de vérifier les modalités de réponse "
        f"et les attentes de {acheteur} ?\n\n"
        "Cordialement,"
    )


def call_script(row: dict[str, Any]) -> str:
    acheteur = str(row.get("acheteur") or "l'acheteur").strip()
    return (
        f"Bonjour, je vous appelle concernant un appel d'offres publié par {acheteur}. "
        "Je souhaite vérifier les informations pratiques : périmètre des prestations, "
        "date limite, modalités de visite, contact technique et pièces attendues. "
        "Pouvez-vous m'indiquer la bonne personne à contacter ?"
    )
