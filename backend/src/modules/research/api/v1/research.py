"""Independent FastAPI REST endpoint for Autonomous Research Engine.

POST /api/v1/research — Standalone research endpoint.
Input: CampaignBrief JSON payload + optional tier parameter.
Output: ResearchBrief JSON + EvidenceGraph + RedTeamReport + ConversationTraces + Metrics.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.api.response import success_response
from src.modules.research.research_service import ResearchEngineService

router = APIRouter(prefix="/research", tags=["Autonomous Research Engine"])


class ResearchRequest(BaseModel):
    """Input payload for independent research execution."""

    user_goal: str
    company_name: str = ""
    tier: str = "Deep"  # Quick, Standard, Deep
    campaign_id: UUID | None = None


def _get_research_service() -> ResearchEngineService:
    return ResearchEngineService()


@router.post("", status_code=status.HTTP_200_OK)
async def execute_research(
    body: ResearchRequest,
    svc: ResearchEngineService = Depends(_get_research_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Execute complete autonomous research engine standalone."""
    if not body.user_goal.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="user_goal parameter cannot be empty",
        )

    try:
        results = await svc.draft_research(
            user_goal=body.user_goal,
            company_name=body.company_name,
            tier=body.tier,
            campaign_id=body.campaign_id,
        )
        return success_response(data=results, message="Autonomous research completed.")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research engine failure: {str(e)}",
        ) from e
