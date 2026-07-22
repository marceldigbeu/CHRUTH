from ao_collect_boamp import is_relevant

ACTIVE = {"nature_libelle": "avis d'appel public a la concurrence"}


def _rec(objet, **extra):
    r = dict(ACTIVE)
    r["objet"] = objet
    r.update(extra)
    return r


def test_keeps_core_keyword():
    keep, reason = is_relevant(_rec("Marche de nettoyage des locaux"), {}, False, False)
    assert keep is True
    assert reason == "ok"


def test_keeps_secondary_only():
    keep, reason = is_relevant(_rec("Prestation d'entretien menager des bureaux"), {}, False, False)
    assert keep is True
    assert reason == "ok mot-cle secondaire"


def test_keeps_detailed_only():
    keep, reason = is_relevant(_rec("Marche de services generaux"), {"texte_extraction": "prestation de nettoyage"}, False, False)
    assert keep is True
    assert reason == "ok"


def test_still_excludes_metier():
    keep, reason = is_relevant(_rec("Desinfection et restauration collective"), {}, False, False)
    assert keep is False
    assert reason == "exclusion dure"


def test_exclusion_dure_graffiti_malgre_nettoyage():
    # Contient "nettoyage" mais c'est de l'enlevement de graffitis -> exclusion DURE.
    keep, reason = is_relevant(_rec("Enlevement de graffitis, affiches sauvages et nettoyage du mobilier"), {}, False, False)
    assert keep is False
    assert reason == "exclusion dure"


def test_exclusion_dure_voirie():
    # "nettoyage" (mot-cle) present mais c'est de la voirie -> l'exclusion dure prime.
    keep, reason = is_relevant(_rec("Prestations de nettoyage de la voirie communale"), {}, False, False)
    assert keep is False
    assert reason == "exclusion dure"


def test_exclusion_dure_cvc_et_fourniture():
    assert is_relevant(_rec("Maintenance des installations de CVC et traitement d'air"), {}, False, False)[0] is False
    assert is_relevant(_rec("Fourniture de produits d'entretien et d'equipements de nettoyage"), {}, False, False)[0] is False


def test_exclusion_dure_fourniture_hygiene():
    # Marche de fourniture (le prestataire fournit les produits) -> ecarte meme avec "nettoyage".
    keep, reason = is_relevant(_rec("Accord-cadre pour la fourniture de produits d'hygiene et de nettoyage"), {}, False, False)
    assert keep is False
    assert reason == "exclusion dure"


def test_nettoyage_locaux_reste_garde():
    # Sanity : un vrai AO de nettoyage de locaux n'est PAS exclu par les regles dures.
    keep, reason = is_relevant(_rec("Nettoyage des locaux de la mairie"), {}, False, False)
    assert keep is True
    assert reason == "ok"


def test_core_keyword_survit_a_exclusion():
    # "menage" est un mot-cle FORT (core) : meme avec un terme d'exclusion SOUPLE present,
    # on garde (l'exclusion souple ne droppe que sans mot-cle nettoyage fort).
    keep, reason = is_relevant(_rec("Menage des locaux, produits d'incontinence inclus"), {}, False, False)
    assert keep is True
    assert reason == "ok"


def test_rejects_no_keyword():
    keep, reason = is_relevant(_rec("Fourniture de vehicules utilitaires"), {}, False, False)
    assert keep is False
    assert reason == "aucun mot-cle CHRUTH"


def test_rejects_inactive():
    rec = {"objet": "Nettoyage des locaux", "nature_libelle": "resultat de marche"}
    keep, reason = is_relevant(rec, {}, False, False)
    assert keep is False
    assert reason == "avis non actif ou attribution"


def test_petit_budget_non_exclu():
    # Budget bien en dessous de 100k : avec la logique inversee, on GARDE.
    record = {
        "objet": "Nettoyage des locaux de l'ecole",
        "nature_libelle": "Appel d'offres",
        "datelimitereponse": "2099-01-01",
        "code_departement_prestation": "75",
    }
    extracted = {"budget_estime_eur": 30_000, "texte_extraction": "nettoyage des locaux"}
    keep, reason = is_relevant(record, extracted, strict_budget=False, idf_only=True)
    assert keep is True


def test_hors_idf_exclu_par_defaut():
    record = {
        "objet": "Nettoyage des locaux",
        "nature_libelle": "Appel d'offres",
        "datelimitereponse": "2099-01-01",
        "code_departement_prestation": "13",  # Marseille, hors IDF
    }
    extracted = {"budget_estime_eur": 30_000, "texte_extraction": "nettoyage des locaux"}
    keep, reason = is_relevant(record, extracted, strict_budget=False, idf_only=True)
    assert keep is False
    assert reason == "hors IDF"
