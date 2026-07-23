"""La collecte doit ramener les marches de personnel, sinon le tri ne verra rien."""
import ao_collect_boamp as collect
import ao_maximilien_scrape as mx
from ao_config import AO_KEYWORDS_RH


def _record(objet: str) -> dict:
    # `nature_libelle` porte « appel » : sans ca l'avis est juge inactif et ecarte
    # AVANT le filtre mot-cle — le test passerait pour la mauvaise raison.
    return {"objet": objet, "nature_libelle": "avis d'appel public a la concurrence",
            "famille": "SERVICES", "code_departement": "93", "dateparution": "2026-07-20"}


def test_la_requete_boamp_interroge_les_termes_de_personnel():
    where = collect.build_where_clause(
        ["nettoyage"] + AO_KEYWORDS_RH, lookback_days=14)
    assert "mise a disposition de personnel" in where


def test_un_ao_de_personnel_est_retenu_avec_son_motif():
    record = _record("Mise a disposition de personnel d'entretien pour les ecoles")
    garde, motif = collect.is_relevant(record, {}, strict_budget=False, idf_only=False)
    assert garde is True
    assert motif == "ok personnel"


def test_un_ao_hors_perimetre_reste_ecarte():
    record = _record("Fourniture de mobilier urbain")
    garde, _ = collect.is_relevant(record, {}, strict_budget=False, idf_only=False)
    assert garde is False


def test_maximilien_cherche_aussi_le_personnel():
    assert any("personnel" in kw.lower() for kw in mx.KEYWORDS)
