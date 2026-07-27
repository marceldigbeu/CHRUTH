from ao_pertinence import PERTINENT, REJETE, trier_listes, trier
from ao_extract_fields import normalize_text


def test_trier_listes_expose_le_terme_declencheur():
    v = trier_listes("Nettoyage des locaux administratifs")
    assert v is not None
    assert v.verdict == PERTINENT
    assert v.terme, "le terme declencheur doit etre renseigne"
    # le terme trouve est bien present dans l'intitule normalise
    assert normalize_text(v.terme) in normalize_text("Nettoyage des locaux administratifs")


class _Espion:
    """Client LLM factice : compte les appels, renvoie une reponse fixe."""
    def __init__(self, reponse='{"verdict": "NON_PERTINENT", "motif": "hors metier"}'):
        self.reponse = reponse
        self.appels = 0

    def moteur_auto(self):
        return True

    def generer(self, *a, **k):
        self.appels += 1
        return self.reponse


def test_une_correction_contradictoire_escalade_vers_l_ia():
    base = trier_listes("Nettoyage des locaux administratifs")
    assert base is not None and base.verdict == PERTINENT
    corrections = [{"objet": "Autre marche", "verdict": REJETE, "terme": base.terme}]
    espion = _Espion()
    v = trier("Nettoyage des locaux administratifs", client=espion, corrections=corrections)
    assert espion.appels == 1, "l'IA doit etre consultee quand une correction contredit"
    assert v.etage == "ia"


def test_sans_contradiction_le_verdict_deterministe_est_garde():
    espion = _Espion()
    v = trier("Nettoyage des locaux administratifs", client=espion, corrections=[])
    assert espion.appels == 0, "aucun appel IA quand rien ne contredit l'etage 1"
    assert v.etage == "listes" and v.verdict == PERTINENT


def test_une_correction_de_meme_verdict_ne_declenche_pas():
    base = trier_listes("Nettoyage des locaux administratifs")
    corrections = [{"objet": "X", "verdict": base.verdict, "terme": base.terme}]
    espion = _Espion()
    v = trier("Nettoyage des locaux administratifs", client=espion, corrections=corrections)
    assert espion.appels == 0
    assert v.etage == "listes"
