"""Workflow Engine API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.api.response import success_response

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.post("")
async def execute_workflow(
    workflow_type: str,
    campaign_id: UUID,
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    return success_response(
        data={"workflow_id": str(campaign_id), "status": "started"}, message="Workflow started"
    )


@router.get("/{thread_id}")
async def get_workflow_status(
    thread_id: str,
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    return success_response(
        data={"thread_id": thread_id, "status": "running"}, message="Workflow status retrieved"
    )


@router.post("/{thread_id}/approve")
async def approve_step(
    thread_id: str,
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    return success_response(
        data={"thread_id": thread_id, "status": "approved"}, message="Step approved"
    )


@router.post("/{thread_id}/reject")
async def reject_step(
    thread_id: str,
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    return success_response(
        data={"thread_id": thread_id, "status": "rejected"}, message="Step rejected"
    )
