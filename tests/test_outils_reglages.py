"""Les boutons du tableur ecrivent au meme endroit que l'app."""
from pathlib import Path

import ao_config
import reglages
from outils import set_collecte, set_notifications


def test_le_bouton_notifications_ecrit_dans_les_reglages(monkeypatch):
    ecrits = []
    monkeypatch.setattr(reglages, "ecrire", lambda m: ecrits.append(m) or m)
    monkeypatch.setattr(reglages, "lire", lambda: {"notifications": True})
    set_notifications.appliquer(False)
    assert ecrits == [{"notifications": False}]


def test_le_bouton_collecte_ecrit_dans_les_reglages(monkeypatch):
    ecrits = []
    monkeypatch.setattr(reglages, "ecrire", lambda m: ecrits.append(m) or m)
    monkeypatch.setattr(reglages, "lire", lambda: {"collecte": True})
    set_collecte.appliquer(False)
    assert ecrits == [{"collecte": False}]


def test_les_boutons_n_ecrivent_pas_les_drapeaux_du_depot(monkeypatch):
    """Lancer la suite ne doit pas couper les notifications du poste.

    `appliquer` pose aussi le drapeau local. Les chemins de drapeau doivent donc
    etre redirigeables : sinon un test eteint pour de bon la veille du fondateur.
    """
    monkeypatch.setattr(reglages, "ecrire", lambda m: m)
    monkeypatch.setattr(reglages, "lire", lambda: {})
    set_notifications.appliquer(False)
    set_collecte.appliquer(False)
    assert not Path(ao_config.BASE_DIR / "alertes_actives.flag").exists()
    assert not Path(ao_config.BASE_DIR / "collecte_active.flag").exists()


def test_les_mots_cles_rh_se_coupent_depuis_les_reglages(monkeypatch):
    import ao_pertinence
    monkeypatch.setattr(reglages, "lire", lambda: {"mots_cles_rh_actifs": False})
    assert ao_pertinence.trier_listes("Mise a disposition de personnel d'entretien") is None


def test_les_mots_cles_rh_actifs_par_defaut(monkeypatch):
    import ao_pertinence
    from ao_pertinence import PERTINENT
    monkeypatch.setattr(reglages, "lire", lambda: {})
    v = ao_pertinence.trier_listes("Mise a disposition de personnel d'entretien")
    assert v.verdict == PERTINENT
