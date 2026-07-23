import prospect_messages as pm


class _FakeClient:
    def __init__(self, dispo=False, reponse=""):
        self._dispo, self._reponse, self.appels = dispo, reponse, 0

    def llm_disponible(self):
        return self._dispo

    def generer(self, prompt, system="", **kw):
        self.appels += 1
        return self._reponse


def test_template_par_defaut_variante_b_differe_de_a():
    a = pm.template_par_defaut("PRIV_BUREAU", "CHAUDE", "A")
    b = pm.template_par_defaut("PRIV_BUREAU", "CHAUDE", "B")
    assert a["email"] != b["email"]
    # les deux restent personnalisables
    for t in (a, b):
        assert "{denomination}" in (t["email"] + " " + t["script"])
        assert any(ph in t["email"] for ph in ("{denomination}", "{ville}", "{effectif}"))


def test_template_par_defaut_a_est_retrocompatible():
    # appel a 2 arguments (ancien style) => variante A
    deux_args = pm.template_par_defaut("PRIV_BUREAU", "CHAUDE")
    explicite_a = pm.template_par_defaut("PRIV_BUREAU", "CHAUDE", "A")
    assert deux_args == explicite_a


def test_generer_variantes_produit_a_et_b(tmp_path):
    client = _FakeClient(dispo=False)  # repli deterministe
    res = pm.generer_variantes(
        [("PRIV_BUREAU", "CHAUDE")], cache_path=tmp_path / "v.json", client=client)
    assert pm.cle_var("PRIV_BUREAU", "CHAUDE", "A") in res
    assert pm.cle_var("PRIV_BUREAU", "CHAUDE", "B") in res
    a = res["PRIV_BUREAU|CHAUDE|A"]
    b = res["PRIV_BUREAU|CHAUDE|B"]
    assert a["variante"] == "A" and b["variante"] == "B"
    assert a["source"] == "defaut" and a["email"] != b["email"]


def test_generer_variantes_cache_evite_double_appel_ia(tmp_path):
    rep = '{"email": "Bonjour {denomination} a {ville}", "script": "Appel {denomination}"}'
    client = _FakeClient(dispo=True, reponse=rep)
    cache = tmp_path / "v.json"
    pm.generer_variantes([("PRIV_BUREAU", "CHAUDE")], cache_path=cache, client=client)
    appels_1 = client.appels
    assert appels_1 == 2  # une generation IA par variante A et B
    pm.generer_variantes([("PRIV_BUREAU", "CHAUDE")], cache_path=cache, client=client)
    assert client.appels == appels_1  # rien de neuf : tout vient du cache
