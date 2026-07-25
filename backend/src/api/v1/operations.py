"""Operations API routes."""

from fastapi import APIRouter, Depends

from src.api.response import success_response
from src.api.dependencies import get_authenticated_user, AuthenticatedUser

router = APIRouter(prefix="/operations", tags=["Operations"])


@router.get("/metrics")
async def get_metrics(
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    return success_response(data={"metrics": {}}, message="Metrics retrieved")


@router.get("/history")
async def get_execution_history(
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    return success_response(data={"history": []}, message="History retrieved")
