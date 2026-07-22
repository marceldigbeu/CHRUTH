from ao_scoring import compute_ao_score


def _base_row(**over):
    row = {
        "objet": "Nettoyage des locaux",
        "categorie": "Batiments",
        "departement_prestation": "75",
        "budget_annuel_eur": None,
        "budget_estime_eur": None,
        "procedure": "",
        "secteur": "Autre",
        "date_limite": "",  # absente => pas de bonus/malus delai
        "niveau_confiance": 80,
        "statut_extraction": "INFO_PARTIELLE",
    }
    row.update(over)
    return row


def _budget_points(budget):
    score, _, _ = compute_ao_score(_base_row(budget_annuel_eur=budget))
    return score


def test_budget_strictement_decroissant():
    s_small = _budget_points(40_000)
    s_mid = _budget_points(90_000)
    s_high = _budget_points(150_000)
    s_big = _budget_points(300_000)
    s_huge = _budget_points(600_000)
    assert s_small > s_mid > s_high > s_big > s_huge


def test_bonus_mapa():
    sans = compute_ao_score(_base_row(procedure="Appel d'offres ouvert"))[0]
    avec = compute_ao_score(_base_row(procedure="Procedure adaptee (MAPA)"))[0]
    assert avec > sans


def test_mapa_article_avec_ponctuation():
    # La citation legale standard "Article R.2123-1" doit declencher le bonus MAPA.
    sans = compute_ao_score(_base_row(procedure="Appel d'offres ouvert"))[0]
    avec = compute_ao_score(_base_row(procedure="Marche passe selon l'article R.2123-1 du CCP"))[0]
    assert avec > sans


def test_bonus_secteur():
    sans = compute_ao_score(_base_row(secteur="Autre"))[0]
    avec = compute_ao_score(_base_row(secteur="Ecole"))[0]
    assert avec > sans


def test_ao_expire_penalise():
    score, _, reasons = compute_ao_score(_base_row(date_limite="2000-01-01"))
    assert "expire" in reasons.lower()
