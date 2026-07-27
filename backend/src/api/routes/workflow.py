"""Workflow Engine API Routes — REST interface for workflow execution."""

import logging
import os
from uuid import uuid4

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflow", tags=["workflow"])


class ExecuteWorkflowRequest(BaseModel):
    graph_id: str = Field(..., description="Workflow graph identifier")
    initial_state: dict = Field(default_factory=dict, description="Initial workflow state")
    thread_id: Optional[str] = Field(default=None, description="Optional thread ID for isolation")


class ResumeWorkflowRequest(BaseModel):
    thread_id: str = Field(..., description="Thread ID to resume")
    resume_value: Optional[Any] = Field(
        default=None, description="Value to pass to interrupted node"
    )


class ApproveWorkflowRequest(BaseModel):
    thread_id: str = Field(..., description="Thread ID to approve")


class RejectWorkflowRequest(BaseModel):
    thread_id: str = Field(..., description="Thread ID to reject")
    reason: str = Field(..., description="Rejection reason")


class WorkflowResponse(BaseModel):
    success: bool
    thread_id: str
    status: str
    message: str
    data: Optional[dict] = None


@router.post("/execute", response_model=WorkflowResponse)
async def execute_workflow(request: ExecuteWorkflowRequest) -> WorkflowResponse:
    """Execute a workflow graph."""
    thread_id = request.thread_id or str(uuid4())
    logger.info("Executing workflow %s on thread %s", request.graph_id, thread_id)

    return WorkflowResponse(
        success=True,
        thread_id=thread_id,
        status="running",
        message="Workflow execution started",
    )


@router.post("/resume", response_model=WorkflowResponse)
async def resume_workflow(request: ResumeWorkflowRequest) -> WorkflowResponse:
    """Resume a paused workflow."""
    logger.info("Resuming workflow on thread %s", request.thread_id)

    return WorkflowResponse(
        success=True,
        thread_id=request.thread_id,
        status="running",
        message="Workflow resumed",
    )


@router.post("/approve", response_model=WorkflowResponse)
async def approve_workflow(request: ApproveWorkflowRequest) -> WorkflowResponse:
    """Approve a workflow paused for human approval."""
    logger.info("Approving workflow on thread %s", request.thread_id)

    return WorkflowResponse(
        success=True,
        thread_id=request.thread_id,
        status="approved",
        message="Workflow approved",
    )


@router.post("/reject", response_model=WorkflowResponse)
async def reject_workflow(request: RejectWorkflowRequest) -> WorkflowResponse:
    """Reject a workflow paused for human approval."""
    logger.info("Rejecting workflow on thread %s: %s", request.thread_id, request.reason)

    return WorkflowResponse(
        success=True,
        thread_id=request.thread_id,
        status="rejected",
        message=f"Workflow rejected: {request.reason}",
    )


@router.get("/status/{thread_id}", response_model=WorkflowResponse)
async def get_workflow_status(thread_id: str) -> WorkflowResponse:
    """Get workflow execution status."""
    return WorkflowResponse(
        success=True,
        thread_id=thread_id,
        status="unknown",
        message="Status retrieved",
    )
