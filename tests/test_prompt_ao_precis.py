import ao_messages as am


def _ao(**kw):
    base = {"id_ao": "A1", "objet": "Nettoyage des locaux scolaires",
            "acheteur": "Mairie de Test", "ville": "Paris", "date_limite": "2099-01-01",
            "budget_estime_eur": "50000", "secteur": "Mairie", "categorie": "Batiments",
            "priorite": "CHAUD"}
    base.update(kw)
    return base


def test_fiche_injectee_dans_system():
    fiche = "## Activite\nNettoyage de bureaux\n## Zone\nIle-de-France"
    system, _prompt = am.prompt_ao(_ao(), fiche=fiche)
    assert "Nettoyage de bureaux" in system
    assert "N'invente AUCUN" in system


def test_sans_fiche_pas_de_bloc_fiche():
    system, _prompt = am.prompt_ao(_ao())
    assert "FICHE CHRUTH" not in system


def test_sections_demandees_dans_le_prompt():
    _system, prompt = am.prompt_ao(_ao())
    for mot in ("Objet", "Accroche", "Compréhension", "propose", "Demande", "Signature", "SCRIPT"):
        assert mot in prompt


def test_garde_qui_parle_a_qui():
    _system, prompt = am.prompt_ao(_ao())
    assert "CHRUTH" in prompt
    assert "acheteur" in prompt.lower()
