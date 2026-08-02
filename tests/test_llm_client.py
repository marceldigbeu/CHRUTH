import pytest

import llm_client


def test_provider_defaut_ollama(monkeypatch):
    monkeypatch.delenv("CHRUTH_LLM_PROVIDER", raising=False)
    assert llm_client._provider() == "ollama"


def test_provider_via_env(monkeypatch):
    monkeypatch.setenv("CHRUTH_LLM_PROVIDER", "Anthropic")
    assert llm_client._provider() == "anthropic"


def test_disponible_cloud_selon_cle(monkeypatch):
    monkeypatch.setenv("CHRUTH_LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm_client.llm_disponible() is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    assert llm_client.llm_disponible() is False
    monkeypatch.setenv("CHRUTH_LLM_MODEL", "modele-test")
    assert llm_client.llm_disponible() is True


def test_generer_provider_inconnu(monkeypatch):
    monkeypatch.setenv("CHRUTH_LLM_PROVIDER", "inconnu")
    with pytest.raises(ValueError):
        llm_client.generer("salut")


def test_generer_ollama_passe_temperature(monkeypatch):
    captured = {}

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "ok"}

    def _fake_post(url, json=None, timeout=None, **kw):
        captured["json"] = json
        return _Resp()

    monkeypatch.setenv("CHRUTH_LLM_PROVIDER", "ollama")
    monkeypatch.setattr(llm_client.requests, "post", _fake_post)
    out = llm_client.generer("p", "s", temperature=0.2)
    assert out == "ok"
    assert captured["json"]["options"]["temperature"] == 0.2
