"""Health check endpoints for the API layer."""

from fastapi import APIRouter

from src.api.response import success_response

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health():
    """Basic health check — API is running."""
    return success_response(data={"status": "healthy"}, message="Service is healthy")


@router.get("/ready")
async def ready():
    """Readiness check — API can accept traffic."""
    return success_response(data={"status": "ready"}, message="Service is ready")


@router.get("/live")
async def live():
    """Liveness check — process is alive."""
    return success_response(data={"status": "alive"}, message="Service is alive")
