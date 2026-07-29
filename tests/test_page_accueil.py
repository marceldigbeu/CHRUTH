"""La page d'accueil doit dire quoi faire, pas seulement souhaiter la bienvenue."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from accueil import couleur_urgence, jours_restants, prochaines_echeances

AUJOURD_HUI = date(2026, 7, 28)


def _dans(jours: int) -> str:
    return (AUJOURD_HUI + timedelta(days=jours)).isoformat()


def _base(**over) -> pd.DataFrame:
    lignes = over.pop("lignes", None) or [
        {"objet": "Nettoyage A", "priorite": "CHAUD", "date_limite": _dans(30),
         "verdict_tri": "PERTINENT"},
        {"objet": "Nettoyage B", "priorite": "CHAUD", "date_limite": _dans(3),
         "verdict_tri": "PERTINENT"},
        {"objet": "Nettoyage C", "priorite": "TIEDE", "date_limite": _dans(12),
         "verdict_tri": ""},
    ]
    return pd.DataFrame(lignes)


def test_jours_restants_lit_une_date_iso():
    assert jours_restants(_dans(10), AUJOURD_HUI) == 10
    assert jours_restants(_dans(-3), AUJOURD_HUI) == -3


def test_jours_restants_tolere_une_date_absente_ou_cassee():
    assert jours_restants("", AUJOURD_HUI) is None
    assert jours_restants(None, AUJOURD_HUI) is None
    assert jours_restants("bientot", AUJOURD_HUI) is None


def test_les_echeances_sortent_de_la_plus_urgente_a_la_moins_urgente():
    urgents = prochaines_echeances(_base(), aujourd_hui=AUJOURD_HUI)
    assert list(urgents["objet"]) == ["Nettoyage B", "Nettoyage C", "Nettoyage A"]


def test_un_ao_expire_ne_figure_pas_dans_les_echeances():
    df = _base(lignes=[
        {"objet": "Expire", "priorite": "CHAUD", "date_limite": _dans(-1), "verdict_tri": ""},
        {"objet": "Vivant", "priorite": "CHAUD", "date_limite": _dans(5), "verdict_tri": ""},
    ])
    urgents = prochaines_echeances(df, aujourd_hui=AUJOURD_HUI)
    assert list(urgents["objet"]) == ["Vivant"]


def test_un_ao_rejete_par_le_tri_ne_figure_pas():
    df = _base(lignes=[
        {"objet": "Hors sujet", "priorite": "CHAUD", "date_limite": _dans(2),
         "verdict_tri": "REJETE"},
        {"objet": "Nettoyage", "priorite": "CHAUD", "date_limite": _dans(9),
         "verdict_tri": "PERTINENT"},
    ])
    urgents = prochaines_echeances(df, aujourd_hui=AUJOURD_HUI)
    assert list(urgents["objet"]) == ["Nettoyage"]


def test_les_ao_froids_ne_remontent_pas_en_accueil():
    df = _base(lignes=[
        {"objet": "Froid", "priorite": "FROID", "date_limite": _dans(1), "verdict_tri": ""},
        {"objet": "Chaud", "priorite": "CHAUD", "date_limite": _dans(20), "verdict_tri": ""},
    ])
    urgents = prochaines_echeances(df, aujourd_hui=AUJOURD_HUI)
    assert list(urgents["objet"]) == ["Chaud"]


def test_la_liste_est_plafonnee():
    lignes = [{"objet": f"AO {i}", "priorite": "CHAUD", "date_limite": _dans(i),
               "verdict_tri": ""} for i in range(1, 12)]
    urgents = prochaines_echeances(_base(lignes=lignes), limite=5, aujourd_hui=AUJOURD_HUI)
    assert len(urgents) == 5
    assert list(urgents["objet"]) == [f"AO {i}" for i in range(1, 6)]


def test_une_base_vide_ne_casse_pas_la_page():
    assert prochaines_echeances(pd.DataFrame(), aujourd_hui=AUJOURD_HUI).empty
    assert prochaines_echeances(None, aujourd_hui=AUJOURD_HUI).empty


def test_une_base_sans_echeance_lisible_ne_casse_pas_la_page():
    df = _base(lignes=[{"objet": "Sans date", "priorite": "CHAUD", "date_limite": "",
                        "verdict_tri": ""}])
    assert prochaines_echeances(df, aujourd_hui=AUJOURD_HUI).empty


def test_la_couleur_signale_l_urgence():
    assert couleur_urgence(2) == "red"
    assert couleur_urgence(7) == "red"
    assert couleur_urgence(12) == "orange"
    assert couleur_urgence(40) == "green"


def test_la_colonne_de_tri_survit_a_itertuples():
    """Une colonne prefixee d'un tiret bas est renommee silencieusement par
    pandas : la page lirait alors un champ inexistant."""
    from accueil import COLONNE_JOURS
    urgents = prochaines_echeances(_base(), aujourd_hui=AUJOURD_HUI)
    assert not COLONNE_JOURS.startswith("_")
    assert COLONNE_JOURS in urgents.columns
    assert all(hasattr(t, COLONNE_JOURS) for t in urgents.itertuples())


def test_la_date_limite_s_affiche_en_francais():
    from accueil import date_lisible
    assert date_lisible("2026-07-28") == "28/07/2026"


def test_un_horodatage_iso_complet_est_reduit_a_la_date():
    """La base stocke parfois « 2026-07-28T14:00:00+00:00 » : brut, il noie la ligne."""
    from accueil import date_lisible
    assert date_lisible("2026-07-28T14:00:00+00:00") == "28/07/2026"


def test_une_date_absente_ou_cassee_ne_casse_pas_l_affichage():
    from accueil import date_lisible
    assert date_lisible("") == ""
    assert date_lisible(None) == ""
    assert date_lisible("a preciser") == "a preciser"


# --- Bloc « Retenus par le tri » --------------------------------------------

def _veille():
    return {
        "MX-1": {"objet": "Nettoyage A", "date_publication": "2026-07-20",
                 "tri": {"verdict": "PERTINENT", "motif": "mot-cle nettoyage"}},
        "MX-2": {"objet": "Nettoyage B", "date_publication": "2026-07-27",
                 "tri": {"verdict": "PERTINENT", "motif": "mot-cle proprete"}},
        "MX-3": {"objet": "Formation", "date_publication": "2026-07-28",
                 "tri": {"verdict": "REJETE", "motif": "hors perimetre"}},
    }


def test_seuls_les_ao_retenus_par_le_tri_sont_montres():
    from accueil import retenus_par_le_tri
    retenus = retenus_par_le_tri(_veille())
    assert [i for i, _ in retenus] == ["MX-2", "MX-1"]


def test_les_plus_recemment_publies_arrivent_en_tete():
    from accueil import retenus_par_le_tri
    retenus = retenus_par_le_tri(_veille())
    assert retenus[0][1]["date_publication"] == "2026-07-27"


def test_une_correction_humaine_prime_sur_le_tri():
    """Un verdict corrige a la main fait autorite : le bloc doit le refleter,
    sans quoi corriger dans la veille ne changerait rien a l'accueil."""
    from accueil import retenus_par_le_tri
    aos = _veille()
    aos["MX-3"]["correction_humaine"] = {"verdict": "PERTINENT", "le": "2026-07-28"}
    retenus = retenus_par_le_tri(aos)
    assert "MX-3" in [i for i, _ in retenus]


def test_une_correction_peut_aussi_retirer_un_ao():
    from accueil import retenus_par_le_tri
    aos = _veille()
    aos["MX-1"]["correction_humaine"] = {"verdict": "REJETE", "le": "2026-07-28"}
    assert "MX-1" not in [i for i, _ in retenus_par_le_tri(aos)]


def test_le_bloc_est_plafonne():
    from accueil import retenus_par_le_tri
    aos = {f"MX-{i}": {"objet": f"AO {i}", "date_publication": f"2026-07-{i:02d}",
                       "tri": {"verdict": "PERTINENT", "motif": "x"}} for i in range(1, 15)}
    assert len(retenus_par_le_tri(aos, limite=5)) == 5


def test_une_veille_vide_ne_casse_pas_l_accueil():
    from accueil import retenus_par_le_tri
    assert retenus_par_le_tri({}) == []
    assert retenus_par_le_tri(None) == []
