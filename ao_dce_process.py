from __future__ import annotations

from pathlib import Path

import pandas as pd

from ao_config import BASE_DIR
from ao_db import AO_COLUMNS, fetch_records, upsert_records
from ao_dce import (
    extract_fields_from_text,
    extract_pdf_text,
    match_manual_pdf,
    try_download_direct,
)

DCE_AUTO_DIR = BASE_DIR / "dce_auto"
DCE_MANUEL_DIR = BASE_DIR / "dce_manuel"


def _blank(value) -> bool:
    return str(value or "").strip().lower() in {"", "nan", "none", "null"}


def needs_dce(row: dict) -> bool:
    return _blank(row.get("budget_estime_eur")) or _blank(row.get("email")) or _blank(row.get("telephone"))


def apply_extraction(row: dict, extracted: dict, statut: str, fichier: str) -> dict:
    out = dict(row)
    for key in ("dce_budget", "dce_email", "dce_tel", "dce_contact", "dce_resume", "dce_texte_extrait"):
        out[key] = extracted.get(key, "")
    out["dce_statut"] = statut
    out["dce_fichier"] = fichier
    # completion non destructive
    if _blank(out.get("budget_estime_eur")) and extracted.get("dce_budget"):
        out["budget_estime_eur"] = extracted["dce_budget"]
    if _blank(out.get("email")) and extracted.get("dce_email"):
        out["email"] = extracted["dce_email"]
    if _blank(out.get("telephone")) and extracted.get("dce_tel"):
        out["telephone"] = extracted["dce_tel"]
    if not _blank(extracted.get("dce_budget")) or not _blank(extracted.get("dce_email")):
        existing = str(out.get("preuve_source") or "")
        out["preuve_source"] = (existing + " | DCE").strip(" |") if "DCE" not in existing else existing
    return out


def process(db_records: pd.DataFrame | None = None) -> dict:
    DCE_AUTO_DIR.mkdir(parents=True, exist_ok=True)
    DCE_MANUEL_DIR.mkdir(parents=True, exist_ok=True)
    df = fetch_records() if db_records is None else db_records
    stats = {"auto": 0, "manuel": 0, "lien_seul": 0, "aucun_lien": 0, "completes": 0}
    updated: list[dict] = []

    for _, series in df.iterrows():
        row = series.to_dict()
        if not needs_dce(row):
            continue
        id_ao = str(row.get("id_ao") or "")
        url_dce = str(row.get("url_dce") or "")
        pdf_path = None
        statut = "AUCUN_LIEN" if _blank(url_dce) else "LIEN_SEUL"

        if not _blank(url_dce):
            pdf_path = try_download_direct(url_dce, DCE_AUTO_DIR, filename=f"{id_ao}.pdf")
            if pdf_path:
                statut = "AUTO_TELECHARGE"
        if pdf_path is None:
            manual = match_manual_pdf(id_ao, DCE_MANUEL_DIR)
            if manual:
                pdf_path = manual
                statut = "DEPOT_MANUEL_OK"

        if pdf_path is not None:
            text = extract_pdf_text(pdf_path)
            extracted = extract_fields_from_text(text)
            new_row = apply_extraction(row, extracted, statut=statut, fichier=pdf_path.name)
            if not _blank(new_row.get("budget_estime_eur")) or not _blank(new_row.get("email")):
                stats["completes"] += 1
            updated.append(new_row)
            stats["auto" if statut == "AUTO_TELECHARGE" else "manuel"] += 1
        else:
            row["dce_statut"] = statut
            updated.append(row)
            stats["aucun_lien" if statut == "AUCUN_LIEN" else "lien_seul"] += 1

    if updated:
        clean = [{k: r.get(k, "") for k in (["id_ao"] + [c for c in AO_COLUMNS if c != "id_ao"])} for r in updated]
        upsert_records(clean)
    return stats


def main() -> int:
    stats = process()
    print("Traitement DCE termine :", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
