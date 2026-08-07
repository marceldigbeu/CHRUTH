"""Tests du depot de l'espace membres : chiffrement, local, github.

Ces tests repondent a trois criteres d'acceptation : l'isolation entre deux
utilisateurs (deux fichiers, aucun melange), la persistance apres relecture
sur disque, et le refus d'ecriture quand la cle ou le jeton manquent.
"""
from __future__ import annotations

import base64
import json
import pytest

import espace_depot
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def depot_isolé(tmp_path, monkeypatch):
    """Depot local propre, cle forcee videe, source locale."""
    espace_depot._reinitialiser_cle()
    monkeypatch.setenv("CHRUTH_ESPACE_SOURCE", "local")
    monkeypatch.setenv("CHRUTH_ESPACE_DIR", str(tmp_path / "membres"))
    yield tmp_path
    espace_depot._reinitialiser_cle()


def _payload(nom="Alice"):
    return {"version": 1, "profil": {"nom": nom}, "preferences": {}, "aos": {},
            "messages": [], "journal": [], "actif": True}


def test_source_locale_par_defaut(monkeypatch):
    monkeypatch.delenv("CHRUTH_ESPACE_SOURCE", raising=False)
    assert espace_depot.source() == "local"


def test_ecrit_et_relit_un_membre(tmp_path):
    espace_depot.ecrire_membre("alice@chruth.fr", _payload("Alice"))
    relu = espace_depot.lire_membre("alice@chruth.fr")
    assert relu["profil"]["nom"] == "Alice"


def test_fichier_sur_disque_chiffre(tmp_path):
    espace_depot.ecrire_membre("alice@chruth.fr", _payload("Alice"))
    fichier = next((tmp_path / "membres").glob("*.enc"))
    brut = fichier.read_bytes()
    assert b"Alice" not in brut
    assert b"profil" not in brut


def test_cle_locale_generee_a_la_premiere_ecriture(tmp_path):
    assert not espace_depot.cle_disponible()
    espace_depot.ecrire_membre("alice@chruth.fr", _payload())
    assert espace_depot.cle_disponible()
    assert (tmp_path / "cle_locale.key").exists()


def test_cle_depuis_environnement(tmp_path, monkeypatch):
    cle = Fernet.generate_key().decode()
    monkeypatch.setenv("CHRUTH_ESPACE_CLE", cle)
    espace_depot.ecrire_membre("alice@chruth.fr", _payload())
    assert not (tmp_path / "cle_locale.key").exists()


def test_cle_depuis_definir_cle():
    cle = Fernet.generate_key().decode()
    espace_depot.definir_cle(cle)
    assert espace_depot.cle_disponible()
    espace_depot._reinitialiser_cle()
    assert not espace_depot.cle_disponible()


def test_deux_membres_deux_fichiers_isoles(tmp_path):
    espace_depot.ecrire_membre("alice@chruth.fr", _payload("Alice"))
    espace_depot.ecrire_membre("bob@chruth.fr", _payload("Bob"))
    assert espace_depot.lire_membre("alice@chruth.fr")["profil"]["nom"] == "Alice"
    assert espace_depot.lire_membre("bob@chruth.fr")["profil"]["nom"] == "Bob"


def test_lire_un_membre_inconnu_retourne_vide():
    assert espace_depot.lire_membre("personne@chruth.fr") == {}


def test_lister_les_membres(tmp_path):
    espace_depot.ecrire_membre("bob@chruth.fr", _payload())
    espace_depot.ecrire_membre("alice@chruth.fr", _payload())
    assert espace_depot.lister_membres() == ["alice@chruth.fr", "bob@chruth.fr"]


def test_supprimer_un_membre(tmp_path):
    espace_depot.ecrire_membre("alice@chruth.fr", _payload())
    espace_depot.supprimer_membre("alice@chruth.fr")
    assert espace_depot.lister_membres() == []


def test_lecture_avec_mauvaise_cle_erreur(tmp_path, monkeypatch):
    espace_depot.ecrire_membre("alice@chruth.fr", _payload())
    espace_depot._reinitialiser_cle()
    (tmp_path / "cle_locale.key").unlink()
    monkeypatch.setenv("CHRUTH_ESPACE_CLE", Fernet.generate_key().decode())
    with pytest.raises(RuntimeError):
        espace_depot.lire_membre("alice@chruth.fr")


# --- Source github (API simulee) -------------------------------------------

class Reponse:
    def __init__(self, status, corps=None):
        self.status_code = status
        self._corps = corps or {}

    def json(self):
        return self._corps


def _config_github(monkeypatch):
    monkeypatch.setenv("CHRUTH_ESPACE_SOURCE", "github")
    monkeypatch.setenv("CHRUTH_GITHUB_REPO", "org/chruth")
    monkeypatch.setenv("CHRUTH_GITHUB_TOKEN", "jeton-de-test")
    monkeypatch.setenv("CHRUTH_ESPACE_CLE", Fernet.generate_key().decode())
    espace_depot._reinitialiser_cle()


def _blob_github(payload) -> Reponse:
    chiffre = espace_depot.chiffrer(payload)
    return Reponse(200, {"content": base64.b64encode(chiffre).decode(),
                         "sha": "sha-1"})


def test_lecture_github(monkeypatch, tmp_path):
    _config_github(monkeypatch)

    def fake_get(url, headers=None, timeout=None):
        return _blob_github(_payload("Alice"))

    monkeypatch.setattr(espace_depot.requests, "get", fake_get)
    assert espace_depot.lire_membre("alice@chruth.fr")["profil"]["nom"] == "Alice"


def test_lecture_github_inexistante_retourne_vide(monkeypatch):
    _config_github(monkeypatch)

    def fake_get(url, headers=None, timeout=None):
        return Reponse(404)

    monkeypatch.setattr(espace_depot.requests, "get", fake_get)
    assert espace_depot.lire_membre("personne@chruth.fr") == {}


def test_ecriture_github_sans_jeton_refusee(monkeypatch):
    _config_github(monkeypatch)
    monkeypatch.delenv("CHRUTH_GITHUB_TOKEN")
    assert not espace_depot.ecriture_possible()
    with pytest.raises(PermissionError):
        espace_depot.ecrire_membre("alice@chruth.fr", _payload())


def test_ecriture_github_sans_cle_refusee(monkeypatch):
    _config_github(monkeypatch)
    monkeypatch.delenv("CHRUTH_ESPACE_CLE")
    assert not espace_depot.ecriture_possible()
    with pytest.raises(PermissionError):
        espace_depot.ecrire_membre("alice@chruth.fr", _payload())


def test_ecriture_github(monkeypatch):
    _config_github(monkeypatch)
    appele = []

    def fake_put(url, headers=None, json=None, timeout=None):
        appele.append(json)
        return Reponse(201, {"content": {"sha": "sha-2"}})

    def fake_get(url, headers=None, timeout=None):
        return Reponse(200, {"content": "", "sha": "sha-1"})

    monkeypatch.setattr(espace_depot.requests, "put", fake_put)
    monkeypatch.setattr(espace_depot.requests, "get", fake_get)
    espace_depot.ecrire_membre("alice@chruth.fr", _payload())
    assert len(appele) == 1
    assert appele[0]["sha"] == "sha-1"


def test_ecriture_github_conflit_reessaie(monkeypatch):
    _config_github(monkeypatch)
    puts = []

    def fake_put(url, headers=None, json=None, timeout=None):
        puts.append(json)
        if len(puts) == 1:
            return Reponse(409)
        return Reponse(201)

    def fake_get(url, headers=None, timeout=None):
        return Reponse(200, {"content": "", "sha": "sha-frais"})

    monkeypatch.setattr(espace_depot.requests, "put", fake_put)
    monkeypatch.setattr(espace_depot.requests, "get", fake_get)
    espace_depot.ecrire_membre("alice@chruth.fr", _payload())
    assert len(puts) == 2
    assert puts[1]["sha"] == "sha-frais"


def test_lister_et_supprimer_sur_github(monkeypatch):
    _config_github(monkeypatch)
    urls = []

    def fake_get(url, headers=None, timeout=None):
        urls.append(url)
        if url.split("?")[0].endswith("/espace_membres"):
            return Reponse(200, [
                {"name": espace_depot._nom_fichier("alice@chruth.fr")},
                {"name": espace_depot._nom_fichier("bob@chruth.fr")},
            ])
        return Reponse(200, {"content": "", "sha": "sha-x"})

    def fake_delete(url, headers=None, json=None, timeout=None):
        return Reponse(200)

    monkeypatch.setattr(espace_depot.requests, "get", fake_get)
    monkeypatch.setattr(espace_depot.requests, "delete", fake_delete)
    assert espace_depot.lister_membres() == ["alice@chruth.fr", "bob@chruth.fr"]
    espace_depot.supprimer_membre("alice@chruth.fr")
