import acheteurs_semaine as asem


def _ao(objet, ach, siret="", dept="75", prio="TIEDE", src="BOAMP"):
    return {"acheteur": ach, "siret": siret, "siren": "", "ville": "Paris", "departement": dept,
            "date_publication": "2026-07-24", "url": "u", "objet": objet, "priorite": prio, "source": src}


def test_deux_ao_du_meme_acheteur_fusionnent_par_siret():
    aos = [_ao("Nettoyage A", "Mairie X", siret="21750001600019", prio="TIEDE"),
           _ao("Nettoyage B", "Mairie X", siret="21750001600019", prio="CHAUD")]
    out = asem.extraire_acheteurs(aos)
    assert len(out) == 1
    assert out[0]["nb_ao_semaine"] == 2
    assert out[0]["priorite"] == "CHAUD"          # la plus chaude gagne
    assert len(out[0]["aos"]) == 2


def test_sans_siret_dedoublonne_par_nom_et_departement():
    aos = [_ao("N1", "Ville Y", dept="92"), _ao("N2", "ville  y", dept="92"), _ao("N3", "Ville Y", dept="93")]
    out = asem.extraire_acheteurs(aos)
    # "Ville Y"/"ville y" (92) fusionnent ; "Ville Y" (93) est distinct
    assert len(out) == 2
