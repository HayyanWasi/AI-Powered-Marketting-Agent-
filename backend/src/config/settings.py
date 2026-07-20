"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application
    APP_NAME: str = "Campaign Management API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    log_level: str = "INFO"

    # LLM
    openai_api_key: str
    google_api_key: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: Optional[str] = None

    # Database (PostgreSQL via Supabase)
    DATABASE_URL: Optional[str] = None

    # Pollinations
    pollinations_base_url: str = "https://image.pollinations.ai/prompt"
    pollinations_model: str = "kontext"
    pollinations_timeout_seconds: int = 30
    pollinations_max_retries: int = 3

    # Image Validation
    min_image_width: int = 1080
    min_image_height: int = 1080
    image_validation_timeout_seconds: int = 10

    # DuckDuckGo Search
    ddgs_timeout_seconds: int = 15
    ddgs_rate_limit_seconds: int = 5

    # Session
    session_timeout_hours: int = 24

    # API
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["*"]

    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Optimistic locking
    ENABLE_VERSION_CHECK: bool = True


settings = Settings()
