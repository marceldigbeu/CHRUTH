"""Interrupteur des notifications de la veille cloud.

Couper les emails ne doit jamais faire PERDRE un AO : pendant la pause les avis
continuent d'entrer dans l'etat (l'app doit les montrer), mais sans email. A la
reactivation, ceux qui n'ont jamais ete notifies partent enfin.
"""
import veille_etat as ve
from ao_pertinence import PERTINENT, REJETE, Verdict

import ao_maximilien_veille as mv


def _ao(id_ao="MX-1", objet="Nettoyage des locaux"):
    return {"id_ao": id_ao, "objet": objet, "acheteur": "Mairie", "ville": "STAINS",
            "departement": "93", "date_publication": "2026-07-20",
            "date_limite": "2026-09-28", "procedure": "MAPA", "score": "65",
            "priorite": "CHAUD", "url": "https://x/1"}


def test_les_notifications_sont_actives_par_defaut(tmp_path):
    assert ve.notifications_actives(ve.charger(tmp_path / "veille.json")) is True


def test_l_interrupteur_fait_un_aller_retour_disque(tmp_path):
    p = tmp_path / "veille.json"
    etat = ve.charger(p)
    ve.definir_notifications(etat, False)
    ve.enregistrer(etat, p)
    assert ve.notifications_actives(ve.charger(p)) is False


def test_en_pause_l_ao_entre_dans_l_etat_mais_sans_email(tmp_path, monkeypatch):
    chemin = tmp_path / "veille.json"
    etat = ve.charger(chemin)
    ve.definir_notifications(etat, False)
    ve.enregistrer(etat, chemin)

    monkeypatch.setattr(mv, "collecter", lambda: [_ao()])
    envoyes = []
    monkeypatch.setattr(mv, "_envoyer", lambda s, h, t: envoyes.append(s))

    assert mv.veiller(etat_path=chemin) == 0
    assert envoyes == []

    releve = ve.charger(chemin)
    assert "MX-1" in releve["aos"]           # visible dans l'app
    assert releve["aos"]["MX-1"]["notifie_le"] is None


def test_a_la_reactivation_le_retard_est_rattrape(tmp_path, monkeypatch):
    """Le coeur de l'affaire : un AO paru pendant la pause ne doit pas etre perdu."""
    chemin = tmp_path / "veille.json"
    etat = ve.charger(chemin)
    ve.definir_notifications(etat, False)
    ve.enregistrer(etat, chemin)

    monkeypatch.setattr(mv, "collecter", lambda: [_ao()])
    envoyes = []
    monkeypatch.setattr(mv, "_envoyer", lambda s, h, t: envoyes.append(s))
    mv.veiller(etat_path=chemin)
    assert envoyes == []

    etat = ve.charger(chemin)
    ve.definir_notifications(etat, True)
    ve.enregistrer(etat, chemin)

    monkeypatch.setattr(mv, "collecter", list)  # plus rien de neuf a collecter
    assert mv.veiller(etat_path=chemin) == 1
    assert len(envoyes) == 1
    assert ve.charger(chemin)["aos"]["MX-1"]["notifie_le"]


def test_un_ao_rejete_ne_part_jamais_meme_apres_reactivation(tmp_path, monkeypatch):
    chemin = tmp_path / "veille.json"
    monkeypatch.setattr(mv, "collecter", lambda: [_ao(objet="Elagage des arbres")])
    envoyes = []
    monkeypatch.setattr(mv, "_envoyer", lambda s, h, t: envoyes.append(s))

    mv.veiller(etat_path=chemin)
    mv.veiller(etat_path=chemin)
    assert envoyes == []
    assert ve.charger(chemin)["aos"]["MX-1"]["tri"]["verdict"] == REJETE


def test_une_correction_humaine_debloque_la_notification(tmp_path, monkeypatch):
    """Marquer « pertinent » dans l'app doit valoir feu vert pour l'email."""
    chemin = tmp_path / "veille.json"
    monkeypatch.setattr(mv, "collecter", lambda: [_ao(objet="Elagage des arbres")])
    envoyes = []
    monkeypatch.setattr(mv, "_envoyer", lambda s, h, t: envoyes.append(s))
    mv.veiller(etat_path=chemin)
    assert envoyes == []

    etat = ve.charger(chemin)
    ve.corriger(etat, "MX-1", PERTINENT)
    ve.enregistrer(etat, chemin)

    monkeypatch.setattr(mv, "collecter", list)
    assert mv.veiller(etat_path=chemin) == 1


def test_la_variable_d_environnement_coupe_tout_meme_si_l_etat_est_actif(tmp_path, monkeypatch):
    """CHRUTH_NOTIFICATIONS=OFF reste le coupe-circuit cote GitHub."""
    chemin = tmp_path / "veille.json"
    monkeypatch.setenv("CHRUTH_NOTIFICATIONS", "OFF")
    monkeypatch.setattr(mv, "collecter", lambda: [_ao()])
    envoyes = []
    monkeypatch.setattr(mv, "_envoyer", lambda s, h, t: envoyes.append(s))

    assert mv.veiller(etat_path=chemin) == 0
    assert envoyes == []
    assert "MX-1" in ve.charger(chemin)["aos"]
