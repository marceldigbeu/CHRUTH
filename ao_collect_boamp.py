from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from ao_config import (
    AO_API_OFFSET_CAP,
    AO_API_PAGE_LIMIT,
    AO_IDF_ONLY,
    AO_KEYWORDS_CORE,
    AO_KEYWORDS_RH,
    AO_KEYWORDS_SECONDARY,
    AO_LOOKBACK_DAYS,
    AO_MAX_EXPORT_ROWS,
    AO_MAX_PAGES,
    AO_RAW_DIR,
    AO_EXCLUSION_KEYWORDS,
    AO_EXCLUSION_DURES,
    BOAMP_API_URL,
    IDF_DEPARTEMENTS,
    REQUEST_TIMEOUT_SECONDS,
    REQUEST_USER_AGENT,
)
from config import departements_des_regions
from ao_db import log_update, upsert_records
from ao_extract_fields import (
    commercial_summary,
    email_template,
    extract_basic_fields,
    find_keywords,
    find_keywords_rh,
    is_active_notice,
    keyword_in_text,
    normalize_department,
    normalize_text,
    call_script,
    classify_categorie,
    detect_secteur,
    extract_duree_mois,
    annualize_budget,
)
from ao_dce import extract_dce_links
from ao_scoring import compute_ao_score


def build_where_clause(keywords: list[str], lookback_days: int, today: date | None = None) -> str:
    """Clause ODSQL : (full-text OR sur mots-cles) AND dateparution >= cutoff."""
    today = today or date.today()
    cutoff = today - timedelta(days=lookback_days)
    seen: list[str] = []
    for kw in keywords:
        k = (kw or "").strip()
        if k and k not in seen:
            seen.append(k)
    or_clause = " OR ".join('"' + k.replace('"', '\\"') + '"' for k in seen)
    return f"({or_clause}) AND dateparution >= date'{cutoff.isoformat()}'"


def fetch_page(limit: int, offset: int, where: str | None = None) -> list[dict[str, Any]]:
    params = {
        "limit": limit,
        "offset": offset,
        "order_by": "dateparution desc",
    }
    if where:
        params["where"] = where
    headers = {"User-Agent": REQUEST_USER_AGENT}
    response = requests.get(BOAMP_API_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    return data.get("results", [])


def text_for_filter(record: dict[str, Any], extracted: dict[str, Any]) -> str:
    return " ".join(
        [
            str(record.get("objet") or ""),
            str(record.get("nomacheteur") or ""),
            str(record.get("procedure_libelle") or ""),
            str(record.get("nature_libelle") or ""),
            str(record.get("descripteur_libelle") or ""),
            str(record.get("criteres") or ""),
            str(extracted.get("texte_extraction") or ""),
        ]
    )


def is_relevant(record: dict[str, Any], extracted: dict[str, Any], strict_budget: bool, idf_only: bool,
                region_departements: list[str] | None = None) -> tuple[bool, str]:
    if not is_active_notice(record):
        return False, "avis non actif ou attribution"

    full_text = text_for_filter(record, extracted)
    core_keywords, secondary_keywords = find_keywords(full_text)
    rh_keywords = find_keywords_rh(full_text)
    if core_keywords:
        match_reason = "ok"
    elif secondary_keywords:
        match_reason = "ok mot-cle secondaire"
    elif rh_keywords:
        match_reason = "ok personnel"
    else:
        return False, "aucun mot-cle CHRUTH"

    # Levier 3 : barriere "mot-cle seulement dans donnees detaillees" supprimee.

    normalized = normalize_text(full_text)
    # Exclusion DURE : activites hors cible (voirie, graffitis, CVC, fourniture...) ->
    # on ecarte meme si "nettoyage" figure dans l'objet.
    if any(keyword_in_text(word, normalized) for word in AO_EXCLUSION_DURES):
        return False, "exclusion dure"
    # Exclusion metier : on ne droppe que si AUCUN mot-cle nettoyage FORT (core) n'est present.
    # On s'appuie directement sur core_keywords (issu de AO_KEYWORDS_CORE) pour rester
    # synchronise avec la liste de mots-cles, meme apres resserrement.
    if any(normalize_text(word) in normalized for word in AO_EXCLUSION_KEYWORDS):
        if not core_keywords:
            return False, "exclusion metier"

    dept = normalize_department(record.get("code_departement_prestation") or record.get("code_departement"))
    first_dept = dept.split(",")[0].strip() if dept else ""
    if idf_only and first_dept not in IDF_DEPARTEMENTS:
        return False, "hors IDF"
    if region_departements and first_dept not in region_departements:
        return False, "hors region"

    # Budget : ne JAMAIS exclure sur le montant (logique PME inversee).
    # Un petit budget est une cible ; un budget absent reste a verifier.
    # Le filtrage budget eventuel reste possible via --strict-budget (gros marches).
    if strict_budget:
        budget = extracted.get("budget_estime_eur")
        if not budget:
            return False, "budget absent"

    return True, match_reason


def build_source_url(record: dict[str, Any]) -> str:
    url = str(record.get("url_avis") or "").strip()
    if url:
        return url
    idweb = str(record.get("idweb") or "").strip()
    if not idweb:
        return ""
    return f"https://boamp-datadila.opendatasoft.com/explore/dataset/boamp/table/?q={idweb}"


def record_to_ao(record: dict[str, Any]) -> dict[str, Any]:
    extracted = extract_basic_fields(record)
    departement = normalize_department(record.get("code_departement"))
    departement_prestation = normalize_department(record.get("code_departement_prestation"))
    ao = {
        "source": "BOAMP",
        "id_ao": str(record.get("idweb") or record.get("id") or "").strip(),
        "objet": record.get("objet") or "",
        "acheteur": record.get("nomacheteur") or "",
        "departement": departement,
        "departement_prestation": departement_prestation,
        "region": "Ile-de-France"
        if (departement_prestation.split(",")[0] if departement_prestation else departement.split(",")[0] if departement else "")
        in IDF_DEPARTEMENTS
        else "",
        "date_publication": record.get("dateparution") or "",
        "date_limite": record.get("datelimitereponse") or "",
        "type_marche": ", ".join(record.get("type_marche") or []) if isinstance(record.get("type_marche"), list) else record.get("type_marche") or "",
        "procedure": record.get("procedure_libelle") or "",
        "nature_avis": record.get("nature_libelle") or "",
        "descripteur": ", ".join(record.get("descripteur_libelle") or [])
        if isinstance(record.get("descripteur_libelle"), list)
        else record.get("descripteur_libelle") or "",
        "criteres": record.get("criteres") or "",
        "url_avis": build_source_url(record),
        **extract_dce_links(record.get("donnees")),
        **extracted,
    }
    texte_cat = " ".join(str(ao.get(k) or "") for k in ("objet", "criteres", "texte_extraction"))
    ao["categorie"] = classify_categorie(texte_cat)
    ao["secteur"] = detect_secteur(ao.get("acheteur"), ao.get("objet"))
    duree_mois = extract_duree_mois(texte_cat)
    budget_annuel, annualise = annualize_budget(ao.get("budget_estime_eur"), duree_mois)
    ao["budget_annuel_eur"] = budget_annuel if budget_annuel is not None else ""
    ao["budget_annualise"] = "oui" if annualise else "non"

    score, priority, reasons = compute_ao_score(ao)
    ao["score_chruth"] = score
    ao["priorite"] = priority
    ao["raisons_scoring"] = reasons
    ao["resume_commercial"] = commercial_summary(ao)
    ao["proposition_message"] = email_template(ao)
    ao["script_appel"] = call_script(ao)
    return ao


def collect_boamp(
    max_pages: int = AO_MAX_PAGES,
    page_limit: int = AO_API_PAGE_LIMIT,
    max_ao: int = AO_MAX_EXPORT_ROWS,
    strict_budget: bool = False,
    idf_only: bool = AO_IDF_ONLY,
    lookback_days: int = AO_LOOKBACK_DAYS,
    region_departements: list[str] | None = None,
) -> dict[str, Any]:
    fetched_records: list[dict[str, Any]] = []
    kept_records: list[dict[str, Any]] = []
    skipped_reasons: dict[str, int] = {}
    kept_reasons: dict[str, int] = {}

    where = build_where_clause(
        AO_KEYWORDS_CORE + AO_KEYWORDS_SECONDARY + AO_KEYWORDS_RH, lookback_days)

    for page in range(max_pages):
        offset = page * page_limit
        if offset + page_limit > AO_API_OFFSET_CAP:
            break
        rows = fetch_page(limit=page_limit, offset=offset, where=where)
        if not rows:
            break
        fetched_records.extend(rows)
        for record in rows:
            ao = record_to_ao(record)
            keep, reason = is_relevant(record, ao, strict_budget=strict_budget, idf_only=idf_only,
                                       region_departements=region_departements)
            if keep:
                kept_records.append(ao)
                kept_reasons[reason] = kept_reasons.get(reason, 0) + 1
                if len(kept_records) >= max_ao:
                    break
            else:
                skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1
        if len(kept_records) >= max_ao:
            break

    AO_RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = AO_RAW_DIR / f"boamp_collect_{stamp}.json"
    raw_path.write_text(json.dumps(fetched_records, ensure_ascii=False, indent=2), encoding="utf-8")

    inserted = upsert_records(kept_records)
    log_update(
        source="BOAMP",
        fetched=len(fetched_records),
        kept=len(kept_records),
        inserted=inserted,
        details=json.dumps(
            {
                "raw_path": str(raw_path),
                "skipped_reasons": skipped_reasons,
                "kept_reasons": kept_reasons,
                "where": where,
                "strict_budget": strict_budget,
                "idf_only": idf_only,
            },
            ensure_ascii=False,
        ),
    )

    return {
        "fetched": len(fetched_records),
        "kept": len(kept_records),
        "inserted_or_updated": inserted,
        "raw_path": raw_path,
        "skipped_reasons": skipped_reasons,
        "kept_reasons": kept_reasons,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collecte BOAMP pour la veille AO CHRUTH.")
    parser.add_argument("--max-pages", type=int, default=AO_MAX_PAGES)
    parser.add_argument("--page-limit", type=int, default=AO_API_PAGE_LIMIT)
    parser.add_argument("--max-ao", type=int, default=AO_MAX_EXPORT_ROWS)
    parser.add_argument("--lookback-days", type=int, default=AO_LOOKBACK_DAYS)
    parser.add_argument("--strict-budget", action="store_true", help="Garde seulement les AO avec budget explicite >= 100k.")
    parser.add_argument("--idf-only", dest="idf_only", action="store_true", default=AO_IDF_ONLY,
                        help="Garde seulement les AO en Ile-de-France (defaut).")
    parser.add_argument("--no-idf", dest="idf_only", action="store_false",
                        help="Desactive le filtre IDF (collecte France entiere).")
    parser.add_argument("--regions", default="",
                        help="Garde seulement les AO d'une ou plusieurs regions, ex: --regions \"Île-de-France,Bretagne\".")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    region_departements = None
    if args.regions.strip():
        noms = [r.strip() for r in args.regions.split(",") if r.strip()]
        region_departements = departements_des_regions(noms)
        print(f"Filtre region : {', '.join(noms)} -> {len(region_departements)} departements")
    result = collect_boamp(
        max_pages=args.max_pages,
        page_limit=args.page_limit,
        max_ao=args.max_ao,
        strict_budget=args.strict_budget,
        idf_only=args.idf_only,
        lookback_days=args.lookback_days,
        region_departements=region_departements,
    )
    print("Collecte BOAMP CHRUTH terminee")
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
