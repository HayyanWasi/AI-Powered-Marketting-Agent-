"""FastAPI application factory.

Creates and configures the FastAPI application with:
- OpenAPI metadata, Swagger UI, and ReDoc
- Middleware (CORS, request ID, security headers, logging)
- Global exception handlers
- Versioned API route registration
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.exception_handlers import register_exception_handlers
from src.api.middleware import register_middleware
from src.api.v1.router import router as v1_router
from src.api.v2.router import router as v2_router

_API_PREFIX = "/api"

_APP: FastAPI | None = None


def _register_versioned_routers(app: FastAPI) -> None:
    """Register versioned API routers under /api/v1 and /api/v2.

    Unversioned requests to /api/ route to the latest stable version.
    Unknown version prefixes produce 404 via the exception handler.
    """
    v1_prefix = f"{_API_PREFIX}/v1"
    v2_prefix = f"{_API_PREFIX}/v2"

    app.include_router(v1_router, prefix=v1_prefix)
    app.include_router(v2_router, prefix=v2_prefix)

    latest_router = APIRouter(prefix=_API_PREFIX)
    latest_router.include_router(v1_router)
    app.include_router(latest_router)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application."""
    from src.api.dependencies import get_operations_service
    from src.modules.linkedin.worker.scheduler import (
        shutdown_linkedin_scheduler,
        start_linkedin_scheduler,
    )

    # Initialize observability telemetry buffers on startup
    operations = get_operations_service()
    await operations.initialize()

    # Validate configured LLM providers independently on startup
    from src.config.settings import settings

    _startup_logger = logging.getLogger("startup")
    _startup_logger.info("=== Validating LLM Provider Configuration ===")
    provider_status = settings.validate_providers()
    for p_name, p_info in provider_status.items():
        if p_info["eligible"]:
            _startup_logger.info(
                "Provider [%s]: ELIGIBLE (model=%s, keys_configured=%d)",
                p_name,
                p_info["model"],
                p_info["keys_configured"],
            )
        else:
            _startup_logger.warning(
                "Provider [%s]: UNAVAILABLE / SKIPPED (missing credentials or model)",
                p_name,
            )

    # Proactively warm the planning-only Ollama GPUs so the first CampaignPlan
    # does not pay cold-start latency. Best-effort: failures are logged inside
    # and never block startup; planning also re-ensures warmth per draft.
    try:
        from src.modules.planning import warmup

        warm_status = await warmup.ensure_planning_endpoints_warm()
        if warm_status:
            _startup_logger.info("Planning Ollama warm-up: %s", warm_status)
    except Exception as exc:  # noqa: BLE001 — warm-up must never break startup
        _startup_logger.warning("Planning Ollama warm-up skipped: %s", type(exc).__name__)

    # Start background scheduler for LinkedIn AutoPilot
    start_linkedin_scheduler()

    yield

    # Flush buffers and gracefully shutdown telemetry & scheduler on exit
    shutdown_linkedin_scheduler()
    await operations.shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Fully configured FastAPI instance ready to serve requests.
    """
    app = FastAPI(
        title="AI Marketing Agent API",
        description="REST API for the AI-powered marketing agent platform. "
        "Provides endpoints for campaign management, AI generation, "
        "workflow orchestration, and guest research.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "AI Marketing Agent Team",
        },
        lifespan=app_lifespan,
    )

    register_middleware(app)
    register_exception_handlers(app)
    _register_versioned_routers(app)

    # Mount static files for local video serving (fallback when Supabase is unavailable)
    static_videos_dir = Path(__file__).parent.parent.parent / "static" / "videos"
    static_videos_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_videos_dir.parent)), name="static")

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    @app.get("/")
    async def root():
        return {
            "message": "AI Social Campaign Manager API",
            "version": "1.0.0",
            "status": "running",
        }

    return app


def get_app() -> FastAPI:
    """Get or create the singleton FastAPI application instance."""
    global _APP
    if _APP is None:
        _APP = create_app()
    return _APP


app = get_app()
