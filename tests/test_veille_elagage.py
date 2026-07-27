from datetime import date, datetime, timedelta, timezone

import veille_etat
from ao_pertinence import Verdict


def _ajouter(etat, id_ao, verdict="REJETE", date_limite="", vu_le=None):
    veille_etat.ajouter(etat, {"id_ao": id_ao, "objet": id_ao, "date_limite": date_limite},
                        Verdict(verdict, "listes", "m", terme="t"))
    if vu_le is not None:
        etat["aos"][id_ao]["vu_le"] = vu_le


def test_elaguer_supprime_un_rejete_expire_non_corrige():
    etat = veille_etat._vide()
    _ajouter(etat, "OLD", "REJETE", date_limite="2020-01-01")
    n = veille_etat.elaguer(etat, aujourd_hui=date(2026, 7, 27))
    assert n == 1 and "OLD" not in etat["aos"]


def test_elaguer_garde_un_pertinent_meme_expire():
    etat = veille_etat._vide()
    _ajouter(etat, "P", "PERTINENT", date_limite="2020-01-01")
    veille_etat.elaguer(etat, aujourd_hui=date(2026, 7, 27))
    assert "P" in etat["aos"]


def test_elaguer_garde_un_rejete_corrige_meme_expire():
    etat = veille_etat._vide()
    _ajouter(etat, "C", "REJETE", date_limite="2020-01-01")
    veille_etat.corriger(etat, "C", "PERTINENT")
    veille_etat.elaguer(etat, aujourd_hui=date(2026, 7, 27))
    assert "C" in etat["aos"]


def test_elaguer_garde_un_rejete_non_expire():
    etat = veille_etat._vide()
    _ajouter(etat, "FUTUR", "REJETE", date_limite="2099-01-01")
    veille_etat.elaguer(etat, aujourd_hui=date(2026, 7, 27))
    assert "FUTUR" in etat["aos"]


def test_elaguer_sans_date_limite_utilise_l_age_vu_le():
    etat = veille_etat._vide()
    vieux = (datetime.now(timezone.utc) - timedelta(days=veille_etat.PURGE_JOURS + 5)).isoformat()
    recent = datetime.now(timezone.utc).isoformat()
    _ajouter(etat, "VIEUX", "REJETE", date_limite="", vu_le=vieux)
    _ajouter(etat, "RECENT", "REJETE", date_limite="", vu_le=recent)
    veille_etat.elaguer(etat)
    assert "VIEUX" not in etat["aos"]
    assert "RECENT" in etat["aos"]
