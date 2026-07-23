"""La recherche Maximilien est floue : une garde locale rattrape le bruit.

Mesure du 2026-07-23 : les mots-cles de personnel font passer la collecte de 14 a
96 consultations, pour UN seul vrai marche de mise a disposition. Le portail matche
sur les mots isoles (« mise », « service », « personnel ») et ramene assurances,
traiteurs et photocopieurs. Sans cette garde, ce bruit atteint l'arbitrage IA, ou
la regle « doute = PERTINENT » le transforme en alertes chez le client.
"""
import ao_maximilien_scrape as mx


def test_un_marche_de_nettoyage_passe_la_garde():
    assert mx.concerne_chruth("NETTOYAGE DES VITRERIES DANS LES BATIMENTS COMMUNAUX")


def test_une_mise_a_disposition_de_personnel_passe_la_garde():
    """La raison d'etre des mots-cles ajoutes : cet AO doit survivre."""
    assert mx.concerne_chruth("Service de mise a disposition de personnel")


def test_un_marche_d_assurance_est_ecarte():
    assert not mx.concerne_chruth("MARCHE PUBLIC DE SERVICES D'ASSURANCE POUR LE CHI")


def test_un_marche_de_traiteur_est_ecarte():
    assert not mx.concerne_chruth("PRESTATIONS DE TRAITEUR POUR DIVERSES RECEPTIONS")


def test_la_collecte_ne_retient_que_les_ao_du_perimetre(monkeypatch):
    """La garde doit etre branchee dans la collecte, pas seulement disponible."""
    brut = [
        {"cid": "1", "objet": "Prestations de nettoyage des locaux"},
        {"cid": "2", "objet": "Marche de prestations de services d'assurance"},
    ]
    monkeypatch.setattr(mx, "_session", lambda: None)
    monkeypatch.setattr(mx, "_pages_resultats", lambda s, kw: [""])
    monkeypatch.setattr(mx, "_parse_resultats", lambda html: brut)
    monkeypatch.setattr(mx, "_to_ao", lambda b: {
        "id_ao": b["cid"], "objet": b["objet"], "departement": "93",
        "priorite": "TIEDE", "score_chruth": 40, "acheteur": "Ville",
    })

    retenus = mx.collecter_brut(keywords=["nettoyage"])

    assert [a["objet"] for a in retenus] == ["Prestations de nettoyage des locaux"]
