import pytest
from pydantic import ValidationError
from src.config.settings import Settings


def test_settings_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("GOOGLE_API_KEY", "test_key")
    monkeypatch.setenv("SUPABASE_URL", "test_url")
    monkeypatch.setenv("SUPABASE_KEY", "test_key")
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.openai_api_key == "test_key"
    assert settings.supabase_url == "test_url"
    assert settings.log_level == "INFO"


def test_settings_default_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("GOOGLE_API_KEY", "test_key")
    monkeypatch.setenv("SUPABASE_URL", "test_url")
    monkeypatch.setenv("SUPABASE_KEY", "test_key")
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.log_level == "INFO"
    assert settings.session_timeout_hours == 24
    assert settings.ddgs_timeout_seconds == 15
    assert settings.ddgs_rate_limit_seconds == 5


def test_settings_missing_required_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]
