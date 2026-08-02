import collect_api_entreprises as cae


class _FakeResp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p


def _payload():
    return {"results": [{
        "siren": "217500016", "nom_complet": "COMMUNE DE PARIS", "nature_juridique": "7210",
        "siege": {"siret": "21750001600019", "adresse": "PLACE DE L'HOTEL DE VILLE 75004 PARIS",
                  "code_postal": "75004", "libelle_commune": "PARIS", "departement": "75",
                  "tranche_effectif_salarie": "42", "est_siege": True},
        "matching_etablissements": []}]}


def test_fetch_by_siret_renvoie_une_fiche(monkeypatch):
    monkeypatch.setattr(cae.SESSION, "get", lambda *a, **k: _FakeResp(_payload()))
    fiche = cae.fetch_by_siret("21750001600019")
    assert fiche is not None
    assert fiche["code_postal"] == "75004"
    assert fiche["nature_juridique"] == "7210"
    assert fiche["libelle_commune"] == "PARIS"


def test_fetch_by_siret_reseau_ko_renvoie_none(monkeypatch):
    import requests
    def boom(*a, **k): raise requests.exceptions.ConnectionError("offline")
    monkeypatch.setattr(cae.SESSION, "get", boom)
    assert cae.fetch_by_siret("21750001600019") is None


def test_fetch_by_siret_invalide_renvoie_none():
    assert cae.fetch_by_siret("abc") is None
    assert cae.fetch_by_siret("") is None
