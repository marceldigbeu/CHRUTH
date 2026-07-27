"""Veille memoire : conservation des verdicts et de leurs termes declencheurs."""
import veille_etat
from ao_pertinence import Verdict


def test_ajouter_conserve_le_terme_du_tri():
    etat = veille_etat._vide()
    veille_etat.ajouter(etat, {"id_ao": "MX-1", "objet": "Nettoyage"},
                        Verdict("PERTINENT", "listes", "motif", terme="nettoyage"))
    assert etat["aos"]["MX-1"]["tri"]["terme"] == "nettoyage"


def _etat_avec_ao(id_ao="MX-1", objet="Nettoyage", terme="nettoyage"):
    etat = veille_etat._vide()
    veille_etat.ajouter(etat, {"id_ao": id_ao, "objet": objet},
                        Verdict("PERTINENT", "listes", "m", terme=terme))
    return etat


def test_corriger_ecrit_dans_la_memoire_avec_le_terme():
    etat = _etat_avec_ao()
    veille_etat.corriger(etat, "MX-1", "REJETE")
    memoire = etat["corrections_memoire"]
    assert len(memoire) == 1
    assert memoire[0]["objet"] == "Nettoyage"
    assert memoire[0]["verdict"] == "REJETE"
    assert memoire[0]["terme"] == "nettoyage"


def test_la_memoire_se_dedoublonne_par_objet():
    etat = _etat_avec_ao()
    veille_etat.corriger(etat, "MX-1", "REJETE")
    veille_etat.corriger(etat, "MX-1", "PERTINENT")  # meme objet -> remplace
    memoire = etat["corrections_memoire"]
    assert len(memoire) == 1
    assert memoire[0]["verdict"] == "PERTINENT"


def test_la_memoire_est_plafonnee():
    etat = veille_etat._vide()
    for i in range(veille_etat.MEMOIRE_MAX + 10):
        veille_etat.ajouter(etat, {"id_ao": f"A{i}", "objet": f"Objet {i}"},
                            Verdict("PERTINENT", "listes", "m", terme="t"))
        veille_etat.corriger(etat, f"A{i}", "REJETE")
    assert len(etat["corrections_memoire"]) == veille_etat.MEMOIRE_MAX
    # les plus recentes sont gardees
    assert etat["corrections_memoire"][-1]["objet"] == f"Objet {veille_etat.MEMOIRE_MAX + 9}"


def test_memoire_corrections_renvoie_les_plus_recentes_d_abord():
    etat = veille_etat._vide()
    for i in range(3):
        veille_etat.ajouter(etat, {"id_ao": f"A{i}", "objet": f"O{i}"},
                            Verdict("PERTINENT", "listes", "m", terme="t"))
        veille_etat.corriger(etat, f"A{i}", "REJETE")
    recentes = veille_etat.memoire_corrections(etat)
    assert [m["objet"] for m in recentes] == ["O2", "O1", "O0"]


def test_migration_reconstruit_la_memoire_depuis_les_ao_corriges():
    # etat "ancien" : des AO corriges, pas de cle corrections_memoire
    etat = _etat_avec_ao(objet="Vieux marche")
    veille_etat.corriger(etat, "MX-1", "REJETE")
    del etat["corrections_memoire"]
    reconstruit = veille_etat.charger_dict(etat)  # helper de migration en memoire
    assert any(m["objet"] == "Vieux marche" and m["verdict"] == "REJETE"
               for m in reconstruit["corrections_memoire"])


def test_migration_dedoublonne_les_objets_identiques():
    """Deux AOs partageant le meme objet : la migration ne garde que le dernier verdict."""
    etat = veille_etat._vide()
    # Ajoute deux AOs avec le meme objet mais des verdicts et dates differents
    for i, (idao, verdict) in enumerate([("A", "PERTINENT"), ("B", "REJETE")]):
        veille_etat.ajouter(etat, {"id_ao": idao, "objet": "Nettoyage des locaux"},
                            Verdict(verdict, "listes", "m", terme="nettoyage"))
        # Simule des corrections a des dates differentes : B est la plus recente
        etat["aos"][idao]["correction_humaine"] = {
            "verdict": verdict,
            "le": f"2026-07-2{i}T10:00:00+00:00",
            "par": "app"
        }
    # Simule un etat ancien : supprime la memoire
    del etat["corrections_memoire"]
    # La migration doit deduire la memoire
    reconstruit = veille_etat.charger_dict(etat)
    memoire = reconstruit["corrections_memoire"]
    # Verifie qu'il n'y a qu'UNE entree (dedoublonnee par objet)
    assert len(memoire) == 1, f"Expected 1 entry, got {len(memoire)}: {memoire}"
    # Et que c'est le verdict le plus recent (B = REJETE)
    assert memoire[0]["verdict"] == "REJETE", f"Expected REJETE, got {memoire[0]['verdict']}"
