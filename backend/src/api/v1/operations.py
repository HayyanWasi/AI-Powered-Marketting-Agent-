"""Operations API routes."""

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import AuthenticatedUser, get_authenticated_user, get_operations_service
from src.api.response import success_response
from src.modules.operations.interfaces.operations import PlatformOperationsService

router = APIRouter(prefix="/operations", tags=["Operations"])


@router.get("/metrics")
async def get_metrics(
    user: AuthenticatedUser = Depends(get_authenticated_user),
    operations: PlatformOperationsService = Depends(get_operations_service),
):
    metrics = await operations.get_metrics()
    return success_response(data=metrics, message="Metrics retrieved")


@router.get("/history")
async def get_execution_history(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    workflow_id: str | None = Query(default=None),
    user: AuthenticatedUser = Depends(get_authenticated_user),
    operations: PlatformOperationsService = Depends(get_operations_service),
):
    """Retrieve execution history strictly scoped to the authenticated user."""
    actual_limit = limit if isinstance(limit, int) else 100
    actual_offset = offset if isinstance(offset, int) else 0
    actual_status = status if isinstance(status, str) else None
    actual_workflow_id = workflow_id if isinstance(workflow_id, str) else None

    history = await operations.get_execution_history(
        user_id=str(user.id),
        workflow_id=actual_workflow_id,
        status=actual_status,
        limit=actual_limit,
        offset=actual_offset,
    )
    return success_response(data=history, message="History retrieved")
