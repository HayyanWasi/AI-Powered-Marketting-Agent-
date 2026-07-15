from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openai_api_key: str
    google_api_key: str
    supabase_url: str
    supabase_key: str
    pollinations_base_url: str = "https://image.pollinations.ai/prompt"
    pollinations_model: str = "kontext"
    pollinations_timeout_seconds: int = 30
    pollinations_max_retries: int = 3
    min_image_width: int = 1080
    min_image_height: int = 1080
    image_validation_timeout_seconds: int = 10
    log_level: str = "INFO"
    session_timeout_hours: int = 24
    ddgs_timeout_seconds: int = 15
    ddgs_rate_limit_seconds: int = 5


settings = Settings()  # type: ignore[call-arg]
