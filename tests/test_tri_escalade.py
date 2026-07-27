from ao_pertinence import PERTINENT, REJETE, trier_listes
from ao_extract_fields import normalize_text


def test_trier_listes_expose_le_terme_declencheur():
    v = trier_listes("Nettoyage des locaux administratifs")
    assert v is not None
    assert v.verdict == PERTINENT
    assert v.terme, "le terme declencheur doit etre renseigne"
    # le terme trouve est bien present dans l'intitule normalise
    assert normalize_text(v.terme) in normalize_text("Nettoyage des locaux administratifs")
