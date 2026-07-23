"""Le marquage des verdicts doit etre incremental.

Le tri d'un gros arriere-plan appelle le LLM une fois par AO ambigu (30 s et plus
sur un modele local). Tout garder dans une seule transaction, c'est perdre le
travail a la premiere interruption et verrouiller la base pendant tout ce temps
face a la tache planifiee.
"""
import pytest

import ao_alertes
import ao_pertinence
from ao_db import connect, init_db, upsert_records


def _ao(id_ao: str, objet: str) -> dict:
    return {"id_ao": id_ao, "source": "BOAMP", "objet": objet, "priorite": "CHAUD",
            "score_chruth": "65", "alerte_envoyee": ""}


def test_les_verdicts_deja_calcules_survivent_a_une_interruption(tmp_path, monkeypatch):
    db = tmp_path / "ao.sqlite"
    init_db(db)
    upsert_records([_ao("26-1", "Nettoyage des locaux"),
                    _ao("26-2", "Nettoyage des vitres")], db_path=db)

    vrai_trier = ao_pertinence.trier
    appels = {"n": 0}

    def trier_puis_planter(*a, **kw):
        appels["n"] += 1
        if appels["n"] > 1:
            raise KeyboardInterrupt("interruption au 2e AO")
        return vrai_trier(*a, **kw)

    monkeypatch.setattr(ao_pertinence, "trier", trier_puis_planter)
    with pytest.raises(KeyboardInterrupt):
        ao_alertes.calculer_verdicts_manquants(db_path=db)

    with connect(db) as conn:
        verdicts = dict(conn.execute(
            "SELECT id_ao, COALESCE(verdict_tri, '') FROM ao_records").fetchall())
    assert verdicts["26-1"] != ""      # deja calcule : conserve
    assert verdicts["26-2"] == ""      # jamais atteint : sera repris au run suivant
