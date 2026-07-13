from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    openai_api_key: str
    google_api_key: str
    supabase_url: str
    supabase_key: str
    log_level: str = "INFO"
    session_timeout_hours: int = 24
    ddgs_timeout_seconds: int = 15
    ddgs_rate_limit_seconds: int = 5


settings = Settings()  # type: ignore[call-arg]
