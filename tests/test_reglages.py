"""Reglages partages : une seule verite, plusieurs fenetres."""
import json

import pytest

import reglages
import veille_depot


def _etat(reg: dict | None = None) -> dict:
    e = {"version": 1, "maj_le": "", "aos": {}, "guide_messages": ""}
    if reg is not None:
        e["reglages"] = reg
    return e


def test_sans_rien_les_defauts_s_appliquent(tmp_path, monkeypatch):
    monkeypatch.setattr(reglages, "CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(veille_depot, "lire", lambda: (_etat(), None))
    r = reglages.lire()
    assert r["notifications"] is True
    assert r["destinataires"] == []


def test_l_etat_partage_prime_sur_le_cache(tmp_path, monkeypatch):
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps({"destinataires": ["cache@x.fr"]}), encoding="utf-8")
    monkeypatch.setattr(reglages, "CACHE", cache)
    monkeypatch.setattr(veille_depot, "lire",
                        lambda: (_etat({"destinataires": ["partage@x.fr"]}), None))
    assert reglages.lire()["destinataires"] == ["partage@x.fr"]


def test_le_cache_prend_le_relais_si_github_est_injoignable(tmp_path, monkeypatch):
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps({"destinataires": ["cache@x.fr"]}), encoding="utf-8")
    monkeypatch.setattr(reglages, "CACHE", cache)

    def en_panne():
        raise RuntimeError("reseau indisponible")

    monkeypatch.setattr(veille_depot, "lire", en_panne)
    assert reglages.lire()["destinataires"] == ["cache@x.fr"]


def test_ecrire_conserve_la_saisie_meme_hors_ligne(tmp_path, monkeypatch):
    """Une panne reseau ne doit jamais faire perdre une saisie."""
    cache = tmp_path / "cache.json"
    monkeypatch.setattr(reglages, "CACHE", cache)
    monkeypatch.setattr(veille_depot, "lire", lambda: (_etat(), None))

    def ecriture_en_panne(etat, sha, message="x"):
        raise RuntimeError("reseau indisponible")

    monkeypatch.setattr(veille_depot, "ecrire", ecriture_en_panne)
    reglages.ecrire({"destinataires": ["a@x.fr"]})
    assert json.loads(cache.read_text(encoding="utf-8"))["destinataires"] == ["a@x.fr"]


def test_ecrire_pousse_dans_l_etat_partage(tmp_path, monkeypatch):
    monkeypatch.setattr(reglages, "CACHE", tmp_path / "cache.json")
    ecrits = []
    monkeypatch.setattr(veille_depot, "lire", lambda: (_etat(), "sha1"))
    monkeypatch.setattr(veille_depot, "ecrire",
                        lambda etat, sha, message="x": ecrits.append(etat) or "sha2")

    reglages.ecrire({"notifications": False})
    assert ecrits[0]["reglages"]["notifications"] is False


def test_l_ancienne_cle_guide_messages_est_reprise(tmp_path, monkeypatch):
    """Migration douce : l'etat en service porte encore guide_messages."""
    monkeypatch.setattr(reglages, "CACHE", tmp_path / "cache.json")
    etat = _etat()
    etat["guide_messages"] = "CHRUTH nettoie des bureaux."
    monkeypatch.setattr(veille_depot, "lire", lambda: (etat, None))
    assert reglages.lire()["fiche_chruth"] == "CHRUTH nettoie des bureaux."


def test_aucun_mot_de_passe_ne_peut_entrer_dans_les_reglages(tmp_path, monkeypatch):
    """Garde-fou de securite : l'etat est versionne, un secret n'y a pas sa place."""
    monkeypatch.setattr(reglages, "CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(veille_depot, "lire", lambda: (_etat(), None))
    monkeypatch.setattr(veille_depot, "ecrire", lambda etat, sha, message="x": "sha")

    with pytest.raises(ValueError):
        reglages.ecrire({"smtp_password": "secret"})
