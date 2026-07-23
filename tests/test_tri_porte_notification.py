"""Le tri est une porte devant la notification : marquer, jamais supprimer."""
import ao_alertes
from ao_db import connect, init_db, upsert_records


def _ao(id_ao: str, objet: str, priorite: str = "CHAUD") -> dict:
    return {"id_ao": id_ao, "source": "BOAMP", "objet": objet, "priorite": priorite,
            "score_chruth": "65", "alerte_envoyee": ""}


def test_les_colonnes_de_tri_sont_creees(tmp_path):
    db = tmp_path / "ao.sqlite"
    init_db(db)
    with connect(db) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(ao_records)")}
    assert {"verdict_tri", "motif_tri"} <= cols


def test_le_chateau_de_sceaux_ne_part_plus_en_notification(tmp_path):
    db = tmp_path / "ao.sqlite"
    init_db(db)
    upsert_records([
        _ao("26-71675", "Decontamination, depoussierage et reconditionnement des reserves "
                        "documentaires du Chateau de Sceaux"),
        _ao("26-00001", "Nettoyage des locaux du MAC VAL"),
    ], db_path=db)

    ao_alertes.calculer_verdicts_manquants(db_path=db)
    ids = [r["id_ao"] for r in ao_alertes.nouveaux_ao_a_alerter(db_path=db)]

    assert "26-71675" not in ids
    assert "26-00001" in ids


def test_l_ao_rejete_reste_en_base_avec_son_motif(tmp_path):
    """On marque, on ne supprime jamais : le cockpit garde le filet large."""
    db = tmp_path / "ao.sqlite"
    init_db(db)
    upsert_records([_ao("26-71675", "Depoussierage des reserves documentaires")], db_path=db)
    ao_alertes.calculer_verdicts_manquants(db_path=db)

    with connect(db) as conn:
        row = dict(conn.execute(
            "SELECT verdict_tri, motif_tri FROM ao_records WHERE id_ao='26-71675'").fetchone())
    assert row["verdict_tri"] == "REJETE"
    assert "depoussierage" in row["motif_tri"]


def test_le_calcul_est_idempotent(tmp_path):
    db = tmp_path / "ao.sqlite"
    init_db(db)
    upsert_records([_ao("26-00001", "Nettoyage des locaux")], db_path=db)
    assert ao_alertes.calculer_verdicts_manquants(db_path=db) == 1
    assert ao_alertes.calculer_verdicts_manquants(db_path=db) == 0
