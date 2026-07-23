"""Le rapprochement des mots-cles doit commencer sur un debut de mot.

Cas reel du 2026-07-23 : « TRAVAUX D'AMENAGEMENT INTERIEUR DU R+1 » a ete classe
PERTINENT au motif « mot-cle menage », trouve a l'interieur de a-menage-ment.
On garde en revanche les suffixes (pluriels, formes flechies) : « ASCENSEURS »
doit toujours declencher l'exclusion « ascenseur ».
"""
from ao_pertinence import PERTINENT, REJETE, trier_listes


def test_amenagement_ne_declenche_pas_le_mot_cle_menage():
    assert trier_listes("TRAVAUX D'AMENAGEMENT INTERIEUR DU R+1 ET COMBLE") is None


def test_menage_reste_un_mot_cle_quand_c_est_le_vrai_mot():
    v = trier_listes("Prestations de menage des locaux administratifs")
    assert v.verdict == PERTINENT


def test_les_pluriels_declenchent_toujours_les_exclusions():
    assert trier_listes("MAINTENANCE DES ASCENSEURS ET MONTE-CHARGES").verdict == REJETE
    assert trier_listes("Entretien du patrimoine arbore de la commune").verdict == REJETE


def test_les_mots_composes_restent_reconnus():
    assert trier_listes("Prestations de bio-nettoyage des chambres").verdict == PERTINENT


def test_limite_assumee_le_suffixe_reste_permissif():
    """Frontiere en tete seulement : « arbore » reconnait « arboree » et « arbores »,
    donc aussi « arborescence ». Accepte : c'est une exclusion, et une arborescence
    documentaire n'est de toute facon pas un marche de nettoyage. Reconnaitre les
    pluriels vaut plus que d'ecarter ce cas de figure."""
    assert trier_listes("Refonte de l'arborescence documentaire").verdict == REJETE
