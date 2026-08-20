"""Operations API routes."""

from fastapi import APIRouter, Depends

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
    user: AuthenticatedUser = Depends(get_authenticated_user),
    operations: PlatformOperationsService = Depends(get_operations_service),
):
    history = await operations.get_execution_history()
    return success_response(data=history, message="History retrieved")
