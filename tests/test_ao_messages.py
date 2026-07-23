import pandas as pd

import ao_messages as am


def _ao(**kw):
    base = {
        "id_ao": "A1", "objet": "Nettoyage des locaux scolaires", "acheteur": "Mairie de Test",
        "ville": "Paris", "date_limite": "2099-01-01", "budget_estime_eur": "50000",
        "budget_annuel_eur": "50000", "secteur": "Mairie", "categorie": "Batiments",
        "priorite": "CHAUD",
    }
    base.update(kw)
    return base


class _FakeClient:
    def __init__(self, dispo=True, reponse=""):
        self._d, self._r, self.appels = dispo, reponse, 0

    def llm_disponible(self):
        return self._d

    def generer(self, prompt, system="", **kw):
        self.appels += 1
        return self._r


def test_prompt_ao_injecte_le_contexte():
    _system, prompt = am.prompt_ao(_ao())
    assert "Nettoyage des locaux scolaires" in prompt
    assert "Mairie de Test" in prompt
    assert "2099-01-01" in prompt


def test_generer_message_ao_repli_sans_llm():
    client = _FakeClient(dispo=False)
    m = am.generer_message_ao(_ao(), client=client)
    assert m["source"] == "defaut"
    assert m["email"].strip() and m["script"].strip()
    assert client.appels == 0


def test_generer_message_ao_ia():
    rep = '{"email": "Bonjour Mairie de Test, au sujet de Nettoyage des locaux scolaires.", "script": "Appel a la Mairie de Test"}'
    client = _FakeClient(dispo=True, reponse=rep)
    m = am.generer_message_ao(_ao(), client=client)
    assert m["source"] == "ia"
    assert "Mairie de Test" in m["email"]


def test_generer_pour_ao_df_colonnes_et_filtre(tmp_path):
    client = _FakeClient(dispo=False)
    df = pd.DataFrame([_ao(id_ao="A1", priorite="CHAUD"), _ao(id_ao="A2", priorite="FROID")])
    out = am.generer_pour_ao_df(df, cache_path=tmp_path / "c.json", client=client)
    assert "brouillon_email_ia" in out.columns and "brouillon_script_ia" in out.columns
    a1 = out[out["id_ao"] == "A1"].iloc[0]
    a2 = out[out["id_ao"] == "A2"].iloc[0]
    assert a1["brouillon_email_ia"].strip()   # CHAUD -> rempli
    assert a2["brouillon_email_ia"] == ""      # FROID -> vide


def test_generer_pour_ao_df_cache(tmp_path):
    rep = '{"email": "Bonjour Mairie de Test", "script": "Appel Mairie de Test"}'
    client = _FakeClient(dispo=True, reponse=rep)
    df = pd.DataFrame([_ao(id_ao="A1", priorite="CHAUD")])
    cache = tmp_path / "c.json"
    am.generer_pour_ao_df(df, cache_path=cache, client=client)
    assert client.appels == 1
    am.generer_pour_ao_df(df, cache_path=cache, client=client)  # 2e fois = cache
    assert client.appels == 1


def test_ecrire_brouillon_md(tmp_path):
    rec = _ao(id_ao="AO/42:x", objet="Nettoyage college")
    msg = {"email": "Bonjour Mairie", "script": "Allo, CHRUTH", "source": "ia"}
    p = am.ecrire_brouillon_md(rec, msg, dossier=tmp_path)
    assert p.exists()
    txt = p.read_text(encoding="utf-8")
    assert "## Email" in txt and "Bonjour Mairie" in txt
    assert "## Script d'appel" in txt and "Allo, CHRUTH" in txt
    assert p.name == "AO_AO_42_x.md"   # id assaini


class _FakeAutoClient:
    def __init__(self, moteur, reponse):
        self._m, self._r, self.kw = moteur, reponse, {}

    def moteur_auto(self):
        return self._m

    def generer(self, prompt, system="", **kw):
        self.kw = kw
        return self._r


def test_generer_message_ao_forwarde_provider_et_timeout_cloud():
    c = _FakeAutoClient("anthropic", '{"email":"E","script":"S"}')
    m = am.generer_message_ao(_ao(), client=c)
    assert m["source"] == "ia"
    assert c.kw.get("provider") == "anthropic"
    assert c.kw.get("timeout") == 60


def test_generer_message_ao_timeout_ollama_plus_long():
    c = _FakeAutoClient("ollama", '{"email":"E","script":"S"}')
    am.generer_message_ao(_ao(), client=c)
    assert c.kw.get("provider") == "ollama"
    assert c.kw.get("timeout") == 300


def test_generer_message_ao_moteur_none_repli():
    c = _FakeAutoClient(None, '{"email":"E","script":"S"}')
    m = am.generer_message_ao(_ao(), client=c)
    assert m["source"] == "defaut"
