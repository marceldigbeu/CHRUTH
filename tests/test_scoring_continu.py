"""Le score doit departager, pas seulement classer.

Avant cette refonte le score etait une somme de paliers : 17 valeurs distinctes
pour 141 AO, toutes multiples de 5, 21 marches a egalite sur 65. Trier ou filtrer
sur une telle echelle ne trie rien. Ces tests fixent ce qu'on attend d'un score
continu : une decimale, un ordre preserve, et deux marches voisins departages.
"""
from __future__ import annotations

from datetime import date, timedelta

from ao_scoring import compute_ao_score


def _row(**over):
    row = {
        "objet": "Nettoyage des locaux",
        "categorie": "Batiments",
        "departement_prestation": "75",
        "budget_annuel_eur": None,
        "budget_estime_eur": None,
        "procedure": "",
        "secteur": "Autre",
        "date_limite": "",
        "niveau_confiance": 80,
        "statut_extraction": "INFO_PARTIELLE",
    }
    row.update(over)
    return row


def _dans(jours: int) -> str:
    return (date.today() + timedelta(days=jours)).isoformat()


def test_le_score_est_un_nombre_a_une_decimale():
    score, _, _ = compute_ao_score(_row())
    assert isinstance(score, float)
    assert round(score, 1) == score, "une seule decimale : au-dela on affiche du bruit"


def test_le_score_reste_borne_entre_0_et_100():
    parfait = compute_ao_score(_row(
        objet="Nettoyage proprete entretien des locaux et vitrerie",
        secteur="Ecole", procedure="Procedure adaptee (MAPA)",
        budget_annuel_eur=10_000, date_limite=_dans(60),
        email="a@b.fr", telephone="0102030405", nom_contact="Dupont",
        url_dce="http://x"))[0]
    nul = compute_ao_score(_row(objet="Fourniture de mobilier de bureau ergonomique",
                                categorie="Mixte/Autre", date_limite="2000-01-01"))[0]
    assert 0.0 <= nul <= parfait <= 100.0


def test_deux_budgets_voisins_ne_donnent_pas_le_meme_score():
    """Le coeur du probleme : deux marches a 30 000 et 45 000 EUR tombaient dans
    la meme tranche et recevaient exactement 25 points."""
    a = compute_ao_score(_row(budget_annuel_eur=30_000))[0]
    b = compute_ao_score(_row(budget_annuel_eur=45_000))[0]
    assert a != b
    assert a > b, "plus le budget est proche de la cible PME, mieux c'est"


def test_deux_delais_voisins_ne_donnent_pas_le_meme_score():
    a = compute_ao_score(_row(date_limite=_dans(20)))[0]
    b = compute_ao_score(_row(date_limite=_dans(28)))[0]
    assert a != b
    assert b > a, "plus il reste de temps pour repondre, mieux c'est"


def test_le_budget_reste_strictement_decroissant():
    scores = [compute_ao_score(_row(budget_annuel_eur=b))[0]
              for b in (40_000, 90_000, 150_000, 300_000, 600_000)]
    assert scores == sorted(scores, reverse=True)
    assert len(set(scores)) == len(scores)


def test_le_delai_reste_croissant_avec_le_temps_restant():
    scores = [compute_ao_score(_row(date_limite=_dans(j)))[0] for j in (1, 7, 20, 40, 90)]
    assert scores == sorted(scores)


def test_un_ao_expire_reste_lourdement_penalise():
    expire = compute_ao_score(_row(date_limite="2000-01-01"))
    vivant = compute_ao_score(_row(date_limite=_dans(30)))[0]
    assert "expire" in expire[2].lower()
    assert expire[0] < vivant


def test_la_densite_de_mots_cles_departage():
    """Un intitule qui empile les termes metier est plus surement pour nous
    qu'un intitule qui en porte un seul."""
    maigre = compute_ao_score(_row(objet="Nettoyage des locaux"))[0]
    dense = compute_ao_score(_row(objet="Nettoyage, proprete et entretien des locaux, vitrerie"))[0]
    assert dense > maigre


def test_la_completude_du_dossier_departage():
    """A criteres metier egaux, un AO joignable vaut mieux qu'un AO muet."""
    muet = compute_ao_score(_row())[0]
    joignable = compute_ao_score(_row(email="contact@ville.fr", telephone="0102030405",
                                      nom_contact="Dupont", url_dce="http://x"))[0]
    assert joignable > muet


def test_le_score_departage_un_lot_d_ao_realistes():
    """Le test qui compte : sur un echantillon proche du reel, on veut des
    valeurs distinctes, la ou l'ancien bareme en produisait une poignee."""
    lot = [
        _row(objet="Nettoyage des batiments communaux", budget_annuel_eur=48_000,
             date_limite=_dans(22), secteur="Ecole"),
        _row(objet="Nettoyage des vitres", budget_annuel_eur=52_000, date_limite=_dans(19)),
        _row(objet="Entretien menager des gymnases", budget_annuel_eur=77_680,
             date_limite=_dans(31), secteur="Gymnase"),
        _row(objet="Proprete des locaux administratifs", budget_annuel_eur=61_000,
             date_limite=_dans(27)),
        _row(objet="Bionettoyage des locaux de sante", budget_annuel_eur=95_000,
             date_limite=_dans(14)),
    ]
    scores = [compute_ao_score(r)[0] for r in lot]
    assert len(set(scores)) == len(scores), f"AO a egalite : {scores}"


def test_les_raisons_citent_les_valeurs_continues():
    _, _, raisons = compute_ao_score(_row(budget_annuel_eur=61_000, date_limite=_dans(27)))
    assert "budget" in raisons.lower()
    assert "delai" in raisons.lower()
