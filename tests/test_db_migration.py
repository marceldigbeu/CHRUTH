import sqlite3

from ao_db import AO_COLUMNS, init_db

NEW_COLS = ["url_profil_acheteur", "dce_statut", "dce_budget", "dce_email",
            "dce_tel", "dce_contact", "dce_resume", "dce_texte_extrait", "dce_fichier"]


def test_new_columns_in_list():
    for c in NEW_COLS:
        assert c in AO_COLUMNS


def test_migration_adds_columns_to_old_db(tmp_path):
    db = tmp_path / "old.sqlite"
    # base "ancienne" sans les colonnes dce_*
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE ao_records (id_ao TEXT PRIMARY KEY, objet TEXT, first_seen TEXT, last_seen TEXT, update_count INTEGER DEFAULT 1)")
    con.execute("INSERT INTO ao_records (id_ao, objet) VALUES ('X1', 'nettoyage')")
    con.commit(); con.close()

    init_db(db)  # doit ajouter les colonnes manquantes sans perte

    con = sqlite3.connect(db)
    cols = {row[1] for row in con.execute("PRAGMA table_info(ao_records)")}
    rows = con.execute("SELECT id_ao, objet FROM ao_records").fetchall()
    con.close()
    for c in NEW_COLS:
        assert c in cols
    assert rows == [("X1", "nettoyage")]  # ligne preservee


def test_nouvelles_colonnes_presentes(tmp_path):
    from ao_db import init_db, connect
    db = tmp_path / "ao_test.sqlite"
    init_db(db)
    with connect(db) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(ao_records)")}
    assert {"categorie", "secteur", "budget_annuel_eur", "budget_annualise"} <= cols


def test_colonne_alerte_envoyee(tmp_path):
    from ao_db import init_db, connect
    db = tmp_path / "ao_alerte.sqlite"
    init_db(db)
    with connect(db) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(ao_records)")}
    assert "alerte_envoyee" in cols
