"""Le cockpit web ecrit au meme endroit que les autres surfaces.

Il n'herite pas de la tache 8 : il ne passe ni par `outils/sync_destinataires.py`
ni par `outils/set_*.py`. `sync_destinataires_secrets` ecrit alertes_secrets.json
(c'est `chruth_email.save_recipients` qui ecrit destinataires.txt, en amont) et
`definir_notifications` appelait `ao_config.set_notifications` en direct. Sans ce
branchement, un reglage change depuis le cockpit web resterait invisible des
autres surfaces — exactement la divergence qu'on supprime.
"""
import json

import ao_config
import cockpit_chruth
import reglages


def test_les_destinataires_du_cockpit_web_vont_dans_les_reglages(monkeypatch, tmp_path):
    ecrits = []
    monkeypatch.setattr(reglages, "ecrire", lambda m: ecrits.append(m) or m)
    monkeypatch.setattr(ao_config, "ALERTE_SECRETS_FILE", tmp_path / "secrets.json")

    cockpit_chruth.sync_destinataires_secrets(["a@x.fr", "b@x.fr"])
    assert ecrits[-1] == {"destinataires": ["a@x.fr", "b@x.fr"]}


def test_une_panne_de_reglages_ne_casse_pas_le_cockpit(monkeypatch, tmp_path):
    secrets = tmp_path / "secrets.json"

    def en_panne(_):
        raise RuntimeError("reseau")

    monkeypatch.setattr(reglages, "ecrire", en_panne)
    monkeypatch.setattr(ao_config, "ALERTE_SECRETS_FILE", secrets)

    cockpit_chruth.sync_destinataires_secrets(["a@x.fr"])  # ne doit pas lever
    assert json.loads(secrets.read_text(encoding="utf-8"))["destinataire"] == "a@x.fr"


def test_la_bascule_des_notifications_passe_par_les_reglages(monkeypatch):
    ecrits = []
    monkeypatch.setattr(reglages, "ecrire", lambda m: ecrits.append(m) or m)
    monkeypatch.setattr(reglages, "lire", lambda: {})
    monkeypatch.setattr(cockpit_chruth, "config_email", lambda: {})

    cockpit_chruth.definir_notifications({"actif": False})
    assert {"notifications": False} in ecrits


def test_le_cockpit_web_n_ecrit_pas_les_secrets_du_depot(monkeypatch):
    """Garde-fou : alertes_secrets.json porte le mot de passe SMTP du poste."""
    monkeypatch.setattr(reglages, "ecrire", lambda m: m)
    monkeypatch.setattr(reglages, "lire", lambda: {})
    monkeypatch.setattr(cockpit_chruth, "config_email", lambda: {})
    avant = ao_config.ALERTE_SECRETS_FILE.exists()

    cockpit_chruth.definir_notifications({"actif": True})
    assert ao_config.ALERTE_SECRETS_FILE.exists() is avant
