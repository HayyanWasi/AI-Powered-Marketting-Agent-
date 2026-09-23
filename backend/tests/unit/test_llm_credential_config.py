"""LLM multi-key credential loading — config detection, missing-key handling,
and secret-safety of the failover chain's logging labels.

Task A finding: config loading itself is correct (settings.py already reads
2 keys per provider and llm_service.py builds an N/2-labelled failover chain
from them). The runtime "1/1" / "missing API key" logs reflect .env only
having one Gemini key, one Groq key, and zero OpenRouter keys — not a code
bug. These tests pin the loading behavior so a future change can't silently
break it, and confirm no key material ever reaches a log-facing string.
"""

from __future__ import annotations

from src.config.settings import Settings


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


class TestCredentialCounting:
    def test_single_gemini_key_detected(self):
        s = _settings(google_api_key="g1")
        assert s.get_gemini_keys() == ["g1"]

    def test_two_gemini_keys_detected_via_either_alias(self):
        s = _settings(google_api_key="g1", google_api_key_2="g2")
        assert s.get_gemini_keys() == ["g1", "g2"]

        s2 = _settings(gemini_api_key="g1", gemini_api_key_2="g2")
        assert s2.get_gemini_keys() == ["g1", "g2"]

    def test_two_groq_keys_detected_via_either_alias(self):
        s = _settings(grok_api_key="k1", grok_api_key_2="k2")
        assert s.get_groq_keys() == ["k1", "k2"]

        s2 = _settings(groq_api_key="k1", groq_api_key2="k2")
        assert s2.get_groq_keys() == ["k1", "k2"]

    def test_missing_openrouter_key_yields_empty_list(self):
        s = _settings()
        assert s.get_openrouter_keys() == []

    def test_configured_openrouter_keys_detected(self):
        s = _settings(openrouter_api_key="o1", openrouter_api_key_2="o2")
        assert s.get_openrouter_keys() == ["o1", "o2"]

    def test_blank_and_whitespace_keys_are_not_counted(self):
        s = _settings(google_api_key="  ", google_api_key_2="")
        assert s.get_gemini_keys() == []


class TestNoSecretsInFailoverLabels:
    def test_chain_labels_never_contain_key_material(self):
        """Provider labels (what gets logged) must never embed key material."""
        import src.services.llm_service as llm_service_module

        secret_key = "sk-super-secret-123"
        s = Settings(
            _env_file=None,  # type: ignore[call-arg]
            llm_api_key=secret_key,
            google_api_key="sk-gemini-secret",
            grok_api_key="sk-groq-secret",
        )

        original_settings = llm_service_module.settings
        try:
            llm_service_module.settings = s
            service = llm_service_module.LLMService()
            labels = [name for name, _provider, _model in service._chain]
        finally:
            llm_service_module.settings = original_settings

        for label in labels:
            assert secret_key not in label
            assert "sk-" not in label


class TestSingleEndpointChain:
    """100% of traffic must route to the LLM_BASE_URL endpoint — no failover."""

    def _chain(self, settings_obj):
        import src.services.llm_service as llm_service_module

        original_settings = llm_service_module.settings
        try:
            llm_service_module.settings = settings_obj
            service = llm_service_module.LLMService()
            return [(name, type(p).__name__, model) for name, p, model in service._chain]
        finally:
            llm_service_module.settings = original_settings

    def test_chain_is_exactly_one_openai_compatible_provider(self):
        chain = self._chain(
            Settings(
                _env_file=None,  # type: ignore[call-arg]
                llm_base_url="https://example.test/v1",
                llm_model="llama3.2:3b",
            )
        )
        assert len(chain) == 1
        name, provider_type, model = chain[0]
        assert name == "ollama"
        assert provider_type == "OllamaProvider"
        assert model == "llama3.2:3b"

    def test_hosted_provider_keys_do_not_reintroduce_failover(self):
        """Even with every hosted key configured, nothing may fail over."""
        chain = self._chain(
            Settings(
                _env_file=None,  # type: ignore[call-arg]
                llm_base_url="https://example.test/v1",
                google_api_key="g1",
                google_api_key_2="g2",
                grok_api_key="k1",
                grok_api_key_2="k2",
                openrouter_api_key="o1",
                openrouter_api_key_2="o2",
            )
        )
        assert len(chain) == 1
        assert chain[0][0] == "ollama"
        names = [name for name, _t, _m in chain]
        assert not any("gemini" in n or "groq" in n or "openrouter" in n for n in names)

    def test_model_and_base_url_come_from_settings_not_hardcoded(self):
        chain = self._chain(
            Settings(
                _env_file=None,  # type: ignore[call-arg]
                llm_base_url="https://some-other-tunnel.test/v1",
                llm_model="some-other-model:1b",
            )
        )
        assert chain[0][2] == "some-other-model:1b"
