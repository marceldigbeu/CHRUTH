from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ao_config import AO_DB_PATH


AO_COLUMNS = [
    "source",
    "id_ao",
    "objet",
    "acheteur",
    "siret_acheteur",
    "siren_acheteur",
    "nom_contact",
    "prenom_contact",
    "email",
    "telephone",
    "adresse",
    "code_postal",
    "ville",
    "departement",
    "departement_prestation",
    "region",
    "date_publication",
    "date_limite",
    "budget_estime_eur",
    "budget_statut",
    "budget_annuel_eur",
    "budget_annualise",
    "categorie",
    "secteur",
    "alerte_envoyee",
    "type_marche",
    "procedure",
    "nature_avis",
    "descripteur",
    "criteres",
    "url_avis",
    "url_dce",
    "url_profil_acheteur",
    "mots_cles_detectes",
    "nb_infos_disponibles",
    "niveau_confiance",
    "statut_extraction",
    "score_chruth",
    "priorite",
    "raisons_scoring",
    "resume_commercial",
    "proposition_message",
    "script_appel",
    "dce_statut",
    "dce_budget",
    "dce_email",
    "dce_tel",
    "dce_contact",
    "dce_resume",
    "dce_texte_extrait",
    "dce_fichier",
    "statut_contact",
    "responsable",
    "date_contact",
    "date_relance",
    "reponse",
    "rdv_obtenu",
    "commentaire_humain",
    "texte_extraction",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Path = AO_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = AO_DB_PATH) -> None:
    with connect(db_path) as conn:
        columns_sql = ",\n".join(f"{column} TEXT" for column in AO_COLUMNS if column != "id_ao")
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS ao_records (
                id_ao TEXT PRIMARY KEY,
                {columns_sql},
                first_seen TEXT,
                last_seen TEXT,
                update_count INTEGER DEFAULT 1
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ao_update_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TEXT,
                source TEXT,
                fetched INTEGER,
                kept INTEGER,
                inserted_or_updated INTEGER,
                details TEXT
            );
            """
        )
        existing = {row[1] for row in conn.execute("PRAGMA table_info(ao_records)")}
        for column in AO_COLUMNS:
            if column != "id_ao" and column not in existing:
                conn.execute(f"ALTER TABLE ao_records ADD COLUMN {column} TEXT")
        conn.commit()


def to_db_value(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)


def upsert_records(records: list[dict[str, Any]], db_path: Path = AO_DB_PATH) -> int:
    if not records:
        return 0
    init_db(db_path)
    now = utc_now()
    count = 0
    insert_columns = ["id_ao"] + [column for column in AO_COLUMNS if column != "id_ao"]
    placeholders = ",".join("?" for _ in insert_columns)
    # Colonnes a NE PAS ecraser lors d'une recollecte (etat applicatif, pas donnee BOAMP).
    # alerte_envoyee notamment : la recollecte 2x/jour renverrait le meme AO dans la
    # fenetre de lookback ; sans cette exclusion le drapeau anti-doublon serait remis a ""
    # a chaque run et l'AO realerté en boucle.
    preserve_on_conflict = {"alerte_envoyee"}
    update_columns = [c for c in insert_columns if c != "id_ao" and c not in preserve_on_conflict]
    update_sql = ", ".join(f"{column}=excluded.{column}" for column in update_columns)

    sql = f"""
        INSERT INTO ao_records ({", ".join(insert_columns)}, first_seen, last_seen, update_count)
        VALUES ({placeholders}, ?, ?, 1)
        ON CONFLICT(id_ao) DO UPDATE SET
            {update_sql},
            last_seen=excluded.last_seen,
            update_count=ao_records.update_count + 1;
    """

    with connect(db_path) as conn:
        for record in records:
            values = [to_db_value(record.get(column)) for column in insert_columns]
            conn.execute(sql, [*values, now, now])
            count += 1
        conn.commit()
    return count


def log_update(source: str, fetched: int, kept: int, inserted: int, details: str = "", db_path: Path = AO_DB_PATH) -> None:
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO ao_update_log (run_at, source, fetched, kept, inserted_or_updated, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (utc_now(), source, fetched, kept, inserted, details),
        )
        conn.commit()


def fetch_records(db_path: Path = AO_DB_PATH) -> pd.DataFrame:
    init_db(db_path)
    with connect(db_path) as conn:
        df = pd.read_sql_query("SELECT * FROM ao_records ORDER BY date_publication DESC, score_chruth DESC", conn)
    return df


def fetch_logs(db_path: Path = AO_DB_PATH) -> pd.DataFrame:
    init_db(db_path)
    with connect(db_path) as conn:
        return pd.read_sql_query("SELECT * FROM ao_update_log ORDER BY id DESC", conn)


if __name__ == "__main__":
    init_db()
    print(f"Base AO initialisee : {AO_DB_PATH}")
