import ao_alertes
from ao_config import (_drapeau_collecte, _drapeau_notifications, set_collecte,
                       set_notifications)
from ao_export_excel import vba_module_text

# Ces trois tests portent sur le drapeau local. Ils visent `_drapeau_notifications`
# et non `notifications_actives` : depuis que les reglages partages font autorite,
# la fonction publique ne consulte le drapeau que lorsqu'ils sont injoignables.
# Le comportement de la fonction publique est couvert par
# tests/test_notifications_source_unique.py.


def test_defaut_actif_si_fichier_absent(tmp_path):
    assert _drapeau_notifications(tmp_path / "absent.flag") is True


def test_set_off_puis_on(tmp_path):
    flag = tmp_path / "alertes_actives.flag"
    set_notifications(False, flag)
    assert _drapeau_notifications(flag) is False
    set_notifications(True, flag)
    assert _drapeau_notifications(flag) is True


def test_off_insensible_casse_et_espaces(tmp_path):
    flag = tmp_path / "f.flag"
    flag.write_text("  off\n", encoding="utf-8")
    assert _drapeau_notifications(flag) is False


def test_collecte_defaut_actif_si_fichier_absent(tmp_path):
    assert _drapeau_collecte(tmp_path / "absent.flag") is True


def test_collecte_set_off_puis_on(tmp_path):
    flag = tmp_path / "collecte_active.flag"
    set_collecte(False, flag)
    assert _drapeau_collecte(flag) is False
    set_collecte(True, flag)
    assert _drapeau_collecte(flag) is True


def test_main_off_n_envoie_aucun_email(monkeypatch):
    # main() interroge notifications_ouvertes() : les reglages partages priment
    # sur le drapeau local, qui n'en est plus qu'un repli hors ligne. Patcher le
    # drapeau ne suffit donc plus, et rendrait le test dependant des fichiers locaux.
    monkeypatch.setattr(ao_alertes, "notifications_ouvertes", lambda: False)

    def _ne_doit_pas_etre_appele(*a, **k):
        raise AssertionError("envoyer_alertes ne doit pas etre appele quand OFF")

    monkeypatch.setattr(ao_alertes, "envoyer_alertes", _ne_doit_pas_etre_appele)
    assert ao_alertes.main() == 0


def test_main_on_appelle_envoyer(monkeypatch):
    monkeypatch.setattr(ao_alertes, "notifications_ouvertes", lambda: True)
    appels = {"n": 0}

    def _faux_envoi(*a, **k):
        appels["n"] += 1
        return 0

    monkeypatch.setattr(ao_alertes, "envoyer_alertes", _faux_envoi)
    assert ao_alertes.main() == 0
    assert appels["n"] == 1


def test_vba_contient_bouton_notifications():
    src = vba_module_text()
    assert "Basculer_Notifications" in src
    assert "set_notifications.py" in src
    assert 'Sheets("Parametres")' in src


def test_vba_contient_bouton_collecte():
    src = vba_module_text()
    assert "Basculer_Collecte_Donnees" in src
    assert "set_collecte.py" in src
    assert 'Range("B3")' in src
