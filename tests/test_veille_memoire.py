"""Veille memoire : conservation des verdicts et de leurs termes declencheurs."""
import veille_etat
from ao_pertinence import Verdict


def test_ajouter_conserve_le_terme_du_tri():
    etat = veille_etat._vide()
    veille_etat.ajouter(etat, {"id_ao": "MX-1", "objet": "Nettoyage"},
                        Verdict("PERTINENT", "listes", "motif", terme="nettoyage"))
    assert etat["aos"]["MX-1"]["tri"]["terme"] == "nettoyage"
