"""Application configuration using Pydantic Settings."""

from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE, env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application
    APP_NAME: str = "Campaign Management API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def _validate_debug(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes", "on", "debug", "dev")
        return bool(v)

    log_level: str = "INFO"

    # Active LLM endpoint — an OpenAI-compatible server (Ollama behind a tunnel).
    # All LLM traffic routes here; the hosted providers below are left configured
    # but unwired. The base URL ends at /v1 because the OpenAI SDK appends
    # /chat/completions itself. Override per-session via .env when the tunnel
    # restarts — nothing in application logic should hardcode these.
    llm_base_url: str = "https://alphabetical-gui-tahoe-vpn.trycloudflare.com/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "llama3.2:3b"

    # Runtime LLM routing mode. "remote" (the default) routes every LLM workload
    # to the hosted provider chain (Groq -> OpenRouter -> Gemini, all keys) and
    # skips every Ollama contact, including the planning warm-up — the backend
    # then needs no Ollama tunnel to operate. Set LLM_MODE=ollama (or "local"/
    # "hybrid") to restore the legacy Ollama-primary behaviour for rollback.
    llm_mode: str = "remote"

    # Planning-only Ollama endpoints (two independent qwen3:8b GPUs). Used ONLY
    # by the campaign-planning lanes; intake, video, and other features keep the
    # global llm_base_url above. Empty means "not configured" — that lane then
    # runs on the remote provider chain alone. Base URL ends at /v1.
    planning_ollama_a_base_url: str = ""
    planning_ollama_a_model: str = "qwen3:8b"
    planning_ollama_b_base_url: str = ""
    planning_ollama_b_model: str = "qwen3:8b"

    # LLM (Multi-Account Pool & Provider-Specific Configuration)
    # Retained for configuration/testing only — not part of the active chain.
    # 1. Primary: Google Gemini
    gemini_api_key: str = ""
    gemini_api_key2: str = ""
    gemini_api_key_2: str = ""
    google_api_key: str = ""
    google_api_key_2: str = ""
    google_api_key_3: str = ""
    gemini_model: str = "gemini-3.6-flash"

    # 2. Failover Tier 2: OpenRouter
    openrouter_api_key: str = ""
    openrouter_api_key2: str = ""
    openrouter_api_key_2: str = ""
    openrouter_api_key_3: str = ""
    openrouter_model: str = "openai/gpt-oss-120b"

    # 3. Failover Tier 3: Groq
    groq_api_key: str = ""
    groq_api_key2: str = ""
    groq_api_key_2: str = ""
    grok_api_key: str = ""
    grok_api_key_2: str = ""
    grok_api_key_3: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    def get_gemini_keys(self) -> list[str]:
        keys = [
            self.gemini_api_key,
            self.gemini_api_key2,
            self.gemini_api_key_2,
            self.google_api_key,
            self.google_api_key_2,
            self.google_api_key_3,
        ]
        return [k.strip() for k in keys if k and k.strip()]

    def get_openrouter_keys(self) -> list[str]:
        keys = [
            self.openrouter_api_key,
            self.openrouter_api_key2,
            self.openrouter_api_key_2,
            self.openrouter_api_key_3,
        ]
        return [k.strip() for k in keys if k and k.strip()]

    def get_groq_keys(self) -> list[str]:
        keys = [
            self.groq_api_key,
            self.groq_api_key2,
            self.groq_api_key_2,
            self.grok_api_key,
            self.grok_api_key_2,
            self.grok_api_key_3,
        ]
        return [k.strip() for k in keys if k and k.strip()]

    def validate_providers(self) -> dict[str, dict[str, Any]]:
        """Validate each configured LLM provider independently."""
        gemini_keys = self.get_gemini_keys()
        openrouter_keys = self.get_openrouter_keys()
        groq_keys = self.get_groq_keys()

        return {
            "gemini": {
                "eligible": bool(gemini_keys and self.gemini_model),
                "model": self.gemini_model,
                "keys_configured": len(gemini_keys),
            },
            "openrouter": {
                "eligible": bool(openrouter_keys and self.openrouter_model),
                "model": self.openrouter_model,
                "keys_configured": len(openrouter_keys),
            },
            "groq": {
                "eligible": bool(groq_keys and self.groq_model),
                "model": self.groq_model,
                "keys_configured": len(groq_keys),
            },
        }

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_KEY: str | None = None

    # Unipile (LinkedIn Gateway)
    unipile_dsn: str = "https://api1.unipile.com:13XXX"
    unipile_token: str = ""
    unipile_account_id: str = ""

    # Hosted Auth (in-app LinkedIn connection). Public base URLs used only to
    # build the Unipile Hosted Auth redirect + notify URLs — no secrets.
    # app_public_base_url must be reachable by Unipile for the notify callback.
    app_public_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:3000"
    unipile_hosted_auth_expiry_minutes: int = 15
    linkedin_auto_engagement_enabled: bool = True
    linkedin_daily_invite_limit: int = 25
    linkedin_daily_like_limit: int = 40
    linkedin_daily_comment_limit: int = 15
    linkedin_timezone: str = "Asia/Karachi"
    # A post stuck in 'publishing' longer than this is treated as a crashed
    # claim and parked in 'needs_review' (fail-closed; never auto-republished).
    linkedin_publish_stale_minutes: int = 15

    # Mock mode (safe development — no real LinkedIn API calls)
    use_mock_unipile: bool = False

    # Database (PostgreSQL via Supabase)
    DATABASE_URL: str | None = None

    # Cloudflare Workers AI (image generation — free tier)
    cloudflare_account_id: str = ""
    cloudflare_ai_token: str = ""
    cloudflare_gateway_id: str = ""
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

    # Exa Research
    exa_api_key: str = ""

    # Video Generation
    imagemagick_binary: str = "/usr/bin/convert"
    video_max_concurrent_renders: int = 1
    video_render_timeout_seconds: int = 300

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

    # Authentication & Security
    REQUIRE_AUTH: bool = True
    SUPABASE_JWT_SECRET: str | None = None

    # When an LLM call fails, agents may fall back to hardcoded placeholder
    # copy. Off by default: a silent placeholder looks like a successful
    # generation to the caller and hides a broken pipeline.
    ALLOW_PLACEHOLDER_CONTENT: bool = False


settings = Settings()
