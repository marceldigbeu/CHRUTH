"""Le tri laisse passer les marches de personnel, pas la fonction RH."""
from ao_pertinence import PERTINENT, REJETE, trier_listes


def test_la_mise_a_disposition_de_personnel_est_pertinente():
    v = trier_listes("Mise a disposition de personnel d'entretien pour les ecoles")
    assert v.verdict == PERTINENT
    assert v.etage == "listes"


def test_les_agents_d_accueil_sont_pertinents():
    assert trier_listes("Prestations d'agents d'accueil pour l'hotel de ville").verdict == PERTINENT


def test_la_paie_reste_rejetee():
    """Le perimetre s'etend au personnel FOURNI, pas a la fonction RH."""
    assert trier_listes("Prestations de gestion de la paie et d'administration du personnel").verdict == REJETE


def test_la_sante_au_travail_reste_rejetee():
    assert trier_listes("Prestations de sante au travail et de medecine preventive").verdict == REJETE


def test_la_formation_reste_rejetee():
    assert trier_listes("Accord cadre de missions de formation des agents").verdict == REJETE


def test_un_intitule_d_accueil_sans_marqueur_reste_ambigu():
    assert trier_listes("Marche d'accueil telephonique de la mairie") is None
