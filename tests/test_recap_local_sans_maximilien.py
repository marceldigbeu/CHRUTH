"""Le recap local ne doit plus notifier Maximilien : le cloud s'en charge."""
import ao_alertes
from ao_db import init_db, upsert_records


def test_le_recap_local_ignore_les_ao_maximilien(tmp_path):
    """Le cloud s'en charge : les inclure ici notifierait deux fois."""
    db = tmp_path / "ao.sqlite"
    init_db(db)
    upsert_records([
        {"id_ao": "MX-1", "source": "MAXIMILIEN", "objet": "Nettoyage des ecoles",
         "priorite": "CHAUD", "score_chruth": "65", "alerte_envoyee": ""},
        {"id_ao": "26-1", "source": "BOAMP", "objet": "Nettoyage des bureaux",
         "priorite": "CHAUD", "score_chruth": "65", "alerte_envoyee": ""},
    ], db_path=db)
    ao_alertes.calculer_verdicts_manquants(db_path=db)

    ids = [r["id_ao"] for r in ao_alertes.nouveaux_ao_a_alerter(db_path=db)]
    assert ids == ["26-1"]
