"""Acces a l'etat depuis l'app : fichier local ou API GitHub. Aucun reseau reel."""
import base64
import json

import pytest

import veille_depot as vd


class FausseReponse:
    def __init__(self, code: int, corps: dict | None = None):
        self.status_code = code
        self._corps = corps or {}

    def json(self):
        return self._corps


def _contenu(etat: dict, sha: str = "sha1") -> FausseReponse:
    brut = json.dumps(etat, ensure_ascii=False).encode("utf-8")
    return FausseReponse(200, {"content": base64.b64encode(brut).decode(), "sha": sha})


# --- Source locale ---------------------------------------------------------

def test_source_locale_lit_et_ecrit_le_fichier(tmp_path, monkeypatch):
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "local")
    monkeypatch.setenv("CHRUTH_VEILLE_ETAT", str(tmp_path / "veille.json"))

    etat, sha = vd.lire()
    assert etat["aos"] == {}
    assert sha is None

    etat["guide_messages"] = "CHRUTH nettoie des bureaux."
    vd.ecrire(etat, sha)
    assert vd.lire()[0]["guide_messages"] == "CHRUTH nettoie des bureaux."


def test_sans_configuration_la_source_est_locale(monkeypatch):
    monkeypatch.delenv("CHRUTH_VEILLE_SOURCE", raising=False)
    monkeypatch.delenv("CHRUTH_GITHUB_TOKEN", raising=False)
    assert vd.source() == "local"


# --- Source GitHub ---------------------------------------------------------

def _config_github(monkeypatch):
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "github")
    monkeypatch.setenv("CHRUTH_GITHUB_REPO", "organisation/CHRUTH")
    monkeypatch.setenv("CHRUTH_GITHUB_TOKEN", "jeton-de-test")


def test_lecture_github_decode_le_base64(monkeypatch):
    _config_github(monkeypatch)
    monkeypatch.setattr(vd.requests, "get",
                        lambda *a, **kw: _contenu({"version": 1, "aos": {"MX-1": {}}}))
    etat, sha = vd.lire()
    assert list(etat["aos"]) == ["MX-1"]
    assert sha == "sha1"


def test_un_etat_absent_sur_github_rend_une_structure_vide(monkeypatch):
    _config_github(monkeypatch)
    monkeypatch.setattr(vd.requests, "get", lambda *a, **kw: FausseReponse(404))
    etat, sha = vd.lire()
    assert etat["aos"] == {}
    assert sha is None


def test_ecriture_github_renvoie_le_nouveau_sha(monkeypatch):
    _config_github(monkeypatch)
    envois = []

    def faux_put(url, **kw):
        envois.append(kw.get("json"))
        return FausseReponse(200, {"content": {"sha": "sha2"}})

    monkeypatch.setattr(vd.requests, "put", faux_put)
    assert vd.ecrire({"version": 1, "aos": {}}, "sha1") == "sha2"
    assert envois[0]["sha"] == "sha1"
    assert base64.b64decode(envois[0]["content"])  # contenu bien encode


def test_un_conflit_declenche_exactement_un_reessai(monkeypatch):
    """Un run de veille concurrent peut avoir ecrit entre notre lecture et notre ecriture."""
    _config_github(monkeypatch)
    reponses = [FausseReponse(409), FausseReponse(200, {"content": {"sha": "sha3"}})]
    tentatives = []

    def faux_put(url, **kw):
        tentatives.append(kw.get("json", {}).get("sha"))
        return reponses.pop(0)

    monkeypatch.setattr(vd.requests, "put", faux_put)
    monkeypatch.setattr(vd.requests, "get", lambda *a, **kw: _contenu({"aos": {}}, sha="frais"))

    assert vd.ecrire({"version": 1, "aos": {}}, "sha-perime") == "sha3"
    assert tentatives == ["sha-perime", "frais"]  # relu avant de reessayer


def test_un_conflit_persistant_leve(monkeypatch):
    _config_github(monkeypatch)
    monkeypatch.setattr(vd.requests, "put", lambda url, **kw: FausseReponse(409))
    monkeypatch.setattr(vd.requests, "get", lambda *a, **kw: _contenu({"aos": {}}, sha="frais"))
    with pytest.raises(RuntimeError):
        vd.ecrire({"version": 1, "aos": {}}, "sha-perime")


def test_sans_jeton_l_ecriture_est_refusee_clairement(monkeypatch):
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "github")
    monkeypatch.setenv("CHRUTH_GITHUB_REPO", "organisation/CHRUTH")
    monkeypatch.delenv("CHRUTH_GITHUB_TOKEN", raising=False)
    assert vd.ecriture_possible() is False
    with pytest.raises(PermissionError):
        vd.ecrire({"version": 1, "aos": {}}, None)


def test_declencher_la_veille_appelle_le_workflow(monkeypatch):
    _config_github(monkeypatch)
    appels = []

    def faux_post(url, **kw):
        appels.append(url)
        return FausseReponse(204)

    monkeypatch.setattr(vd.requests, "post", faux_post)
    assert vd.declencher_veille() is True
    assert "veille-maximilien.yml/dispatches" in appels[0]
