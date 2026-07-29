"""Le pilotage doit montrer ce qui est rempli, et rien d'autre.

La page affichait quatre nombres dont « AO en Ile-de-France », egal au total
puisque la collecte est filtree sur l'Ile-de-France : un indicateur qui ne peut
pas varier n'informe de rien. Ces tests couvrent ce qui la remplace.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pandas as pd

import pilotage

AUJOURD_HUI = date(2026, 7, 29)


def _dans(jours: int) -> str:
    return (AUJOURD_HUI + timedelta(days=jours)).isoformat()


def _base(lignes=None) -> pd.DataFrame:
    return pd.DataFrame(lignes if lignes is not None else [
        {"date_limite": _dans(3), "date_publication": "2026-07-20", "verdict_tri": "PERTINENT",
         "departement": "92", "budget_statut": "A_VERIFIER_BUDGET", "email": "a@b.fr",
         "telephone": "", "statut_extraction": "OK"},
        {"date_limite": _dans(12), "date_publication": "2026-07-21", "verdict_tri": "",
         "departement": "75", "budget_statut": "OK", "email": "", "telephone": "",
         "statut_extraction": "OK"},
        {"date_limite": _dans(25), "date_publication": "2026-07-27", "verdict_tri": "REJETE",
         "departement": "92", "budget_statut": "OK", "email": "c@d.fr",
         "telephone": "0102030405", "statut_extraction": "DCE_A_TELECHARGER"},
        {"date_limite": _dans(-5), "date_publication": "2026-06-01", "verdict_tri": "",
         "departement": "93", "budget_statut": "OK", "email": "e@f.fr", "telephone": "",
         "statut_extraction": "OK"},
    ])


# --- Echeances --------------------------------------------------------------

def test_les_paliers_d_echeance_sont_cumulatifs():
    e = pilotage.echeances(_base(), AUJOURD_HUI)
    assert e["sous_7j"] == 1
    assert e["sous_15j"] == 2, "la quinzaine contient la semaine"
    assert e["sous_30j"] == 3


def test_les_ao_expires_sont_comptes_a_part():
    e = pilotage.echeances(_base(), AUJOURD_HUI)
    assert e["expirees"] == 1
    assert e["ouvertes"] == 3


def test_une_date_illisible_ne_fausse_aucun_palier():
    df = _base([{"date_limite": "a preciser"}, {"date_limite": ""}, {"date_limite": None}])
    e = pilotage.echeances(df, AUJOURD_HUI)
    assert e["sous_7j"] == 0 and e["expirees"] == 0 and e["ouvertes"] == 0


def test_une_base_vide_ne_casse_pas_les_echeances():
    for vide in (pd.DataFrame(), None):
        assert pilotage.echeances(vide, AUJOURD_HUI)["sous_7j"] == 0


# --- Attente de tri ---------------------------------------------------------

def test_les_ao_jamais_juges_sont_comptes():
    """C'est du travail en attente : le chiffre doit appeler une action."""
    assert pilotage.attente_de_tri(_base()) == 2


def test_l_attente_de_tri_ignore_les_espaces():
    assert pilotage.attente_de_tri(pd.DataFrame([{"verdict_tri": "   "}])) == 1


# --- Flux hebdomadaire ------------------------------------------------------

def test_le_flux_est_rendu_dans_l_ordre_du_temps():
    flux = pilotage.flux_hebdomadaire(_base())
    assert list(flux["semaine"]) == sorted(flux["semaine"]), \
        "un graphique se lit de gauche a droite dans le sens du temps"


def test_le_flux_se_limite_aux_dernieres_semaines():
    lignes = [{"date_publication": f"2026-{m:02d}-01"} for m in range(1, 13)]
    assert len(pilotage.flux_hebdomadaire(pd.DataFrame(lignes), semaines=4)) == 4


def test_le_flux_sans_date_ne_casse_rien():
    assert pilotage.flux_hebdomadaire(pd.DataFrame([{"date_publication": ""}])).empty


# --- Entonnoir de collecte --------------------------------------------------

def _logs():
    return pd.DataFrame([
        {"run_at": "2026-07-29T14:44:26+00:00", "source": "MAXIMILIEN", "fetched": 15,
         "kept": 15, "inserted_or_updated": 0, "details": "5 mots-cles"},
        {"run_at": "2026-07-29T14:43:49+00:00", "source": "BOAMP", "fetched": 1609,
         "kept": 43, "inserted_or_updated": 43,
         "details": json.dumps({"skipped_reasons": {"aucun mot-cle CHRUTH": 934,
                                                    "avis non actif": 448,
                                                    "hors IDF": 130,
                                                    "exclusion dure": 54}})},
    ])


def test_l_entonnoir_prend_le_passage_qui_a_reellement_filtre():
    """Le passage Maximilien est plus recent mais ne rapporte que ses quinze
    consultations : il masquerait le tri de fond."""
    e = pilotage.entonnoir_collecte(_logs())
    assert e["source"] == "BOAMP"
    assert e["examines"] == 1609
    assert e["retenus"] == 43


def test_les_raisons_d_ecartement_sont_triees_par_volume():
    raisons = pilotage.entonnoir_collecte(_logs())["raisons"]
    assert [r["nombre"] for r in raisons] == sorted([r["nombre"] for r in raisons], reverse=True)
    assert raisons[0]["motif"] == "aucun mot-cle CHRUTH"


def test_un_journal_sans_details_json_ne_casse_rien():
    logs = pd.DataFrame([{"run_at": "2026-07-29T10:00:00+00:00", "source": "MAXIMILIEN",
                          "fetched": 15, "kept": 15, "inserted_or_updated": 2,
                          "details": "5 mots-cles"}])
    e = pilotage.entonnoir_collecte(logs)
    assert e["examines"] == 15
    assert e["raisons"] == []


def test_un_journal_vide_ne_casse_rien():
    for vide in (pd.DataFrame(), None):
        assert pilotage.entonnoir_collecte(vide)["examines"] == 0


def test_les_derniers_passages_sont_du_plus_recent_au_plus_ancien():
    passages = pilotage.derniers_passages(_logs())
    assert list(passages["source"]) == ["MAXIMILIEN", "BOAMP"]
    assert list(passages["examinés"]) == [15, 1609]


# --- Repartition ------------------------------------------------------------

def test_la_repartition_classe_du_plus_fourni_au_moins_fourni():
    r = pilotage.repartition(_base(), "departement")
    assert list(r["departement"])[0] == "92"
    assert list(r["appels d'offres"]) == sorted(list(r["appels d'offres"]), reverse=True)


def test_la_repartition_ignore_les_valeurs_vides():
    df = pd.DataFrame([{"secteur": "Mairie"}, {"secteur": ""}, {"secteur": None}])
    r = pilotage.repartition(df, "secteur")
    assert len(r) == 1


def test_une_colonne_absente_ne_casse_pas_la_repartition():
    assert pilotage.repartition(_base(), "colonne_inexistante").empty


# --- Qualite des donnees ----------------------------------------------------

def test_la_qualite_liste_des_taches_et_non_des_indicateurs():
    points = {p["point"]: p["nombre"] for p in pilotage.qualite_donnees(_base())}
    assert points["Budget à vérifier"] == 1
    assert points["Sans email ni téléphone"] == 1
    assert points["Dossier de consultation à récupérer"] == 1
    assert points["En attente de tri"] == 2


def test_un_point_a_zero_ne_s_affiche_pas():
    """Une ligne « 0 chose a faire » occupe l'ecran sans rien apprendre."""
    propre = pd.DataFrame([{"budget_statut": "OK", "email": "a@b.fr", "telephone": "01",
                            "statut_extraction": "OK", "verdict_tri": "PERTINENT"}])
    assert pilotage.qualite_donnees(propre) == []


def test_une_base_vide_ne_produit_aucune_tache():
    assert pilotage.qualite_donnees(pd.DataFrame()) == []


# --- Age de la base ---------------------------------------------------------

def test_l_age_de_la_base_est_dit_en_clair():
    maintenant = datetime(2026, 7, 29, 18, 0, tzinfo=timezone.utc)
    logs = pd.DataFrame([{"run_at": "2026-07-29T14:00:00+00:00"}])
    assert pilotage.age_de_la_base(logs, maintenant) == "il y a 4 h"


def test_l_age_bascule_en_jours_au_dela_de_24h():
    maintenant = datetime(2026, 7, 29, 18, 0, tzinfo=timezone.utc)
    logs = pd.DataFrame([{"run_at": "2026-07-26T14:00:00+00:00"}])
    assert pilotage.age_de_la_base(logs, maintenant) == "il y a 3 j"


def test_sans_journal_l_age_vaut_jamais():
    assert pilotage.age_de_la_base(pd.DataFrame()) == "jamais"
    assert pilotage.age_de_la_base(None) == "jamais"
