"""Application configuration using Pydantic Settings."""


from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # LLM (Multi-Account Pool)
    google_api_key: str
    grok_api_key: str = ""
    grok_api_key_2: str = ""
    grok_api_key_3: str = ""
    openrouter_api_key: str = ""
    openrouter_api_key_2: str = ""
    openrouter_api_key_3: str = ""
    openrouter_model: str = "google/gemma-4-26b-a4b-it:free"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str | None = None

    # Unipile (LinkedIn Gateway)
    unipile_dsn: str = "https://api1.unipile.com:13XXX"
    unipile_token: str = ""
    unipile_account_id: str = ""

    # Database (PostgreSQL via Supabase)
    DATABASE_URL: str | None = None

    # Cloudflare Workers AI (image generation — free tier)
    cloudflare_account_id: str = ""
    cloudflare_ai_token: str = ""
    cloudflare_ai_base_url: str = "https://api.cloudflare.com/client/v4/accounts"
    cloudflare_img2img_model: str = "@cf/runwayml/stable-diffusion-v1-5-img2img"
    cloudflare_text2img_model: str = "@cf/black-forest-labs/flux-1-schnell"
    cloudflare_image_timeout_seconds: int = 120
    cloudflare_max_retries: int = 3
    cloudflare_image_width: int = 1080
    cloudflare_image_height: int = 1080

    # Pollinations
    pollinations_base_url: str = "https://image.pollinations.ai/prompt"
    pollinations_model: str = ""
    pollinations_api_token: str | None = None
    pollinations_image_width: int = 1080
    pollinations_image_height: int = 1080
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

    # Observability (all optional — telemetry no-ops cleanly when unset)
    langsmith_api_key: str | None = None
    langsmith_project: str = "ai-marketing-agent"
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "ai-marketing-agent-operations"

    # API
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["*"]

    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Optimistic locking
    ENABLE_VERSION_CHECK: bool = True

    # When an LLM call fails, agents may fall back to hardcoded placeholder
    # copy. Off by default: a silent placeholder looks like a successful
    # generation to the caller and hides a broken pipeline.
    ALLOW_PLACEHOLDER_CONTENT: bool = False


settings = Settings()
