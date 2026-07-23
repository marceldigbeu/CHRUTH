"""Le pipeline local lit les reglages partages, sans jamais dependre du reseau."""
import ao_alertes
import reglages


def test_les_destinataires_viennent_des_reglages(monkeypatch):
    monkeypatch.setattr(reglages, "lire", lambda: {"destinataires": ["a@x.fr", "b@x.fr"]})
    assert ao_alertes.charger_destinataires() == ["a@x.fr", "b@x.fr"]


def test_le_fichier_local_prend_le_relais_si_les_reglages_sont_vides(monkeypatch, tmp_path):
    """Anti-regression : une installation existante ne doit pas perdre ses destinataires."""
    fichier = tmp_path / "destinataires.txt"
    fichier.write_text("# liste\nlegacy@x.fr\n", encoding="utf-8")
    monkeypatch.setattr(reglages, "lire", lambda: {"destinataires": []})
    monkeypatch.setattr(ao_alertes, "ALERTE_DESTINATAIRES_FILE", fichier)
    assert ao_alertes.charger_destinataires() == ["legacy@x.fr"]


def test_une_panne_de_reglages_ne_casse_pas_l_envoi(monkeypatch, tmp_path):
    fichier = tmp_path / "destinataires.txt"
    fichier.write_text("legacy@x.fr\n", encoding="utf-8")

    def en_panne():
        raise RuntimeError("reseau")

    monkeypatch.setattr(reglages, "lire", en_panne)
    monkeypatch.setattr(ao_alertes, "ALERTE_DESTINATAIRES_FILE", fichier)
    assert ao_alertes.charger_destinataires() == ["legacy@x.fr"]


def test_les_notifications_suivent_les_reglages(monkeypatch):
    monkeypatch.setattr(reglages, "lire", lambda: {"notifications": False})
    assert ao_alertes.notifications_ouvertes() is False


def test_hors_ligne_le_drapeau_local_reprend_la_main(monkeypatch):
    """Le bouton du cockpit doit rester efficace quand l'etat partage est injoignable."""
    def en_panne():
        raise RuntimeError("reseau")

    monkeypatch.setattr(reglages, "lire", en_panne)
    monkeypatch.setattr(ao_alertes, "notifications_actives", lambda: False)
    assert ao_alertes.notifications_ouvertes() is False
