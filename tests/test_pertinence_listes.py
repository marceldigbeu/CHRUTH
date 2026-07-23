"""Etage 1 du tri : listes deterministes. Cas reellement observes en production."""
from ao_pertinence import PERTINENT, REJETE, trier_listes


def test_rejette_decontamination_et_depoussierage():
    """Le cas qui a declenche la refonte : BOAMP 26-71675, score CHAUD 65, email envoye."""
    v = trier_listes(
        "Decontamination, depoussierage et reconditionnement des reserves documentaires "
        "n2 et 3 du Chateau de Sceaux",
        detail="prestations de nettoyage des reserves",
    )
    assert v.verdict == REJETE
    assert "decontamination" in v.motif


def test_rejette_les_ascenseurs():
    v = trier_listes("MAINTENANCE DES ASCENSEURS, MONTE-CHARGES ET ELEVATEURS DE PERSONNES")
    assert v.verdict == REJETE


def test_rejette_l_elagage():
    v = trier_listes("Elagage, essouchage, plantation et entretien ecologique des arbres")
    assert v.verdict == REJETE


def test_rejette_les_punaises_de_lit():
    v = trier_listes("Prestations de lutte contre les punaises de lit, et de deratisation")
    assert v.verdict == REJETE


def test_garde_le_mac_val():
    """AO coeur de metier, perdu par l'absence de pagination."""
    v = trier_listes("Nettoyage des locaux du MAC VAL - Musee d'art contemporain")
    assert v.verdict == PERTINENT
    assert v.etage == "listes"


def test_garde_le_nettoyage_de_batiments_communaux():
    assert trier_listes("nettoyage et entretien des batiments communaux").verdict == PERTINENT


def test_mot_cle_seulement_dans_le_detail_ne_tranche_pas():
    """La regle centrale : le detail seul n'autorise plus a notifier."""
    assert trier_listes("Reconditionnement de reserves documentaires",
                        detail="inclut une prestation de nettoyage") is None


def test_intitule_sans_signal_est_ambigu():
    assert trier_listes("Marche de services divers pour la commune") is None


def test_exclusion_prime_sur_mot_cle_coeur():
    """Un intitule qui contient les deux doit etre rejete : l'exclusion est plus specifique."""
    v = trier_listes("Nettoyage et depoussierage des gaines de ventilation")
    assert v.verdict == REJETE
