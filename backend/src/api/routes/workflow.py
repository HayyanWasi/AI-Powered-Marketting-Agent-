"""Workflow Engine API Routes — REST interface for workflow execution."""

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflow", tags=["workflow"])

# In-memory workflow state (for MVP)
_workflow_state: dict[str, dict] = {}


class ExecuteWorkflowRequest(BaseModel):
    graph_id: str = Field(..., description="Workflow graph identifier")
    initial_state: dict = Field(default_factory=dict, description="Initial workflow state")
    thread_id: str | None = Field(default=None, description="Optional thread ID for isolation")


class ResumeWorkflowRequest(BaseModel):
    thread_id: str = Field(..., description="Thread ID to resume")
    resume_value: Any | None = Field(
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
    data: dict | None = None


async def _execute_campaign_generation(thread_id: str, initial_state: dict) -> dict:
    """Execute campaign generation via the real LangGraph-backed pipeline.

    Delegates entirely to campaign_generation_service.run_campaign_generation
    (ContextBuilder -> Orchestrator/LangGraph -> persistence). No fallback
    content is ever substituted for a failed pipeline run.
    """
    from src.services.campaign_generation_service import (
        CampaignGenerationError,
        run_campaign_generation,
    )

    try:
        result = await run_campaign_generation(initial_state)
        _workflow_state[thread_id] = {
            "status": "completed",
            "campaign_id": result["campaign_id"],
            "completed_at": datetime.now().isoformat(),
        }
        return result

    except CampaignGenerationError as e:
        logger.error("Campaign generation pipeline failed: %s", e)
        _workflow_state[thread_id] = {
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now().isoformat(),
        }
        raise
    except Exception as e:
        logger.exception("Campaign generation failed: %s", e)
        _workflow_state[thread_id] = {
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now().isoformat(),
        }
        raise


@router.post("/execute", response_model=WorkflowResponse)
async def execute_workflow(request: ExecuteWorkflowRequest) -> WorkflowResponse:
    """Execute a workflow graph."""
    thread_id = request.thread_id or str(uuid4())
    logger.info("Executing workflow %s on thread %s", request.graph_id, thread_id)

    # Store initial state
    _workflow_state[thread_id] = {
        "status": "running",
        "graph_id": request.graph_id,
        "initial_state": request.initial_state,
        "started_at": datetime.now().isoformat(),
    }

    # Execute the actual generation
    try:
        if request.graph_id == "campaign_generation":
            result = await _execute_campaign_generation(thread_id, request.initial_state)
            return WorkflowResponse(
                success=True,
                thread_id=thread_id,
                status="completed",
                message="Campaign generation completed",
                data=result,
            )
        else:
            return WorkflowResponse(
                success=True,
                thread_id=thread_id,
                status="running",
                message="Workflow execution started",
            )
    except Exception as e:
        return WorkflowResponse(
            success=False,
            thread_id=thread_id,
            status="failed",
            message=f"Workflow failed: {str(e)}",
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
    state = _workflow_state.get(thread_id)

    if state:
        return WorkflowResponse(
            success=True,
            thread_id=thread_id,
            status=state.get("status", "unknown"),
            message=f"Workflow {state.get('status', 'unknown')}",
            data=state,
        )

    return WorkflowResponse(
        success=True,
        thread_id=thread_id,
        status="unknown",
        message="Status retrieved",
    )
