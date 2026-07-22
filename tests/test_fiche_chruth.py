import prospect_messages as pm


def test_fiche_absente_renvoie_vide(tmp_path):
    assert pm.fiche_chruth(tmp_path / "nope.md") == ""


def test_gabarit_vide_renvoie_vide(tmp_path):
    f = tmp_path / "fiche.md"
    f.write_text(
        "# Fiche CHRUTH (remplir)\n\n## Activite\n<!-- ex: nettoyage -->\n\n"
        "## Zone\n<!-- ex: IDF -->\n",
        encoding="utf-8",
    )
    assert pm.fiche_chruth(f) == ""


def test_fiche_remplie_garde_les_faits(tmp_path):
    f = tmp_path / "fiche.md"
    f.write_text(
        "## Activite\n<!-- ex -->\nNettoyage de bureaux en IDF\n\n"
        "## Points forts\nInterlocuteur unique\n",
        encoding="utf-8",
    )
    out = pm.fiche_chruth(f)
    assert "Nettoyage de bureaux en IDF" in out
    assert "Interlocuteur unique" in out
    assert "<!--" not in out
