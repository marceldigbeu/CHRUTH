import llm_client

_CLES = ("ANTHROPIC_API_KEY", "MISTRAL_API_KEY", "GROQ_API_KEY")


def _clean(monkeypatch):
    for k in _CLES:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("CHRUTH_LLM_PROVIDER", raising=False)


def test_cloud_provider_none_sans_cle(monkeypatch):
    _clean(monkeypatch)
    assert llm_client.cloud_provider() is None
    assert llm_client.cloud_disponible() is False


def test_cloud_provider_detecte_une_seule_cle(monkeypatch):
    _clean(monkeypatch)
    monkeypatch.setenv("MISTRAL_API_KEY", "x")
    assert llm_client.cloud_provider() == "mistral"
    assert llm_client.cloud_disponible() is True


def test_cloud_provider_ordre_priorite(monkeypatch):
    _clean(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "y")
    assert llm_client.cloud_provider() == "anthropic"


def test_cloud_provider_respecte_choix_explicite(monkeypatch):
    _clean(monkeypatch)
    monkeypatch.setenv("CHRUTH_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "y")
    assert llm_client.cloud_provider() == "groq"


def test_moteur_auto_cloud_sinon_ollama_sinon_none(monkeypatch):
    _clean(monkeypatch)
    monkeypatch.setattr(llm_client, "llm_disponible", lambda p=None: p == "ollama")
    assert llm_client.moteur_auto() == "ollama"       # pas de cloud, ollama up
    monkeypatch.setattr(llm_client, "llm_disponible", lambda p=None: False)
    assert llm_client.moteur_auto() is None            # rien
    monkeypatch.setenv("ANTHROPIC_API_KEY", "z")
    assert llm_client.moteur_auto() == "anthropic"     # cloud prioritaire
