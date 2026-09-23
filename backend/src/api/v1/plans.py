"""Campaign Plan API routes — spec 016.

POST   /campaigns/{id}/plan/draft         Run the panel, store v1.
GET    /campaigns/{id}/plan               Current plan document.
GET    /campaigns/{id}/plan/versions      Version history.
GET    /campaigns/{id}/plan/versions/{v}  Specific version.
GET    /campaigns/{id}/plan/messages      Refinement thread.
POST   /campaigns/{id}/plan/messages      Submit a critique / refine.
POST   /campaigns/{id}/plan/approve       Approve; unlocks generation.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.api.response import success_response
from src.modules.planning.models.campaign_plan import ResearchStatus
from src.modules.planning.repositories.plan_repository import PlanNotFoundError
from src.modules.planning.services.plan_refinement_service import (
    PlanDraftError,
    PlanRefinementService,
)
from src.services.campaign_context_service import (
    CampaignContextResolver,
    check_plan_freshness,
)

router = APIRouter(prefix="/campaigns", tags=["Campaign Plans"])


# ── Request bodies ────────────────────────────────────────────────────────────


class DraftPlanRequest(BaseModel):
    """Inputs required to draft a plan for a campaign."""

    user_goal: str = ""
    company_name: str = ""
    brand_tone: str = ""
    brand_guidelines: str = ""
    event_name: str = ""
    event_date: str = ""
    venue: str = ""
    registration_link: str = ""
    platforms: list[str] = []
    guests: list[str] = []
    language: str = "en"
    research_tier: str = "Quick"  # Quick, Standard, Deep


class RefinePlanRequest(BaseModel):
    """A single marketer critique submitted to the refinement loop."""

    content: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_service() -> PlanRefinementService:
    return PlanRefinementService()


def _not_found(campaign_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No plan found for campaign {campaign_id}",
    )


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("/{campaign_id}/plan/draft", status_code=status.HTTP_201_CREATED)
async def draft_plan(
    campaign_id: UUID,
    body: DraftPlanRequest,
    svc: PlanRefinementService = Depends(_get_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Run the specialist panel and store the plan as version 1.

    This is an async operation — runs web research first then panel calls LLM
    5 times concurrently.
    """
    inputs = await CampaignContextResolver().resolve(campaign_id, user.id)
    brief = inputs.to_brief(body.user_goal)

    try:
        plan = await svc.draft_plan(
            campaign_id=campaign_id,
            created_by=UUID(user.id),
            brief=brief,
            language=body.language,
            tier=body.research_tier,
        )
    except PlanDraftError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return success_response(data=plan.to_document(), message="Plan drafted successfully.")
    doc = plan.to_document()
    doc["research_status"] = plan.research_status.value
    doc["research_status_reason"] = plan.research_status_reason

    msg = "Plan drafted successfully."
    if plan.research_status == ResearchStatus.DEGRADED:
        msg = "Plan drafted, but live research was degraded or unavailable."
    elif plan.research_status == ResearchStatus.NO_EVIDENCE:
        msg = "Plan drafted, but web search returned no usable evidence."
    elif plan.research_status == ResearchStatus.AVAILABLE:
        msg = "Plan drafted successfully with live research evidence."

    return success_response(data=doc, message=msg)


@router.get("/{campaign_id}/plan")
async def get_plan(
    campaign_id: UUID,
    svc: PlanRefinementService = Depends(_get_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Return the current plan document."""
    try:
        inputs = await CampaignContextResolver().resolve(campaign_id, user.id)
        plan = await svc.get_plan(campaign_id)
    except PlanNotFoundError:
        raise _not_found(campaign_id)

    doc = plan.to_document()
    is_stale, reason = check_plan_freshness(plan, inputs)
    doc["is_stale"] = is_stale
    doc["staleness_reason"] = reason
    doc["research_status"] = plan.research_status.value
    doc["research_status_reason"] = plan.research_status_reason

    return success_response(data=doc, message="Plan retrieved.")


@router.get("/{campaign_id}/plan/versions")
async def list_versions(
    campaign_id: UUID,
    svc: PlanRefinementService = Depends(_get_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Return all plan versions, newest first."""
    try:
        await CampaignContextResolver().resolve(campaign_id, user.id)
        versions = await svc.list_versions(campaign_id)
    except PlanNotFoundError:
        raise _not_found(campaign_id)
    return success_response(
        data=[
            {
                "version": v.version,
                "change_summary": v.change_summary,
                "sections_changed": list(v.sections_changed),
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
        message=f"{len(versions)} version(s) found.",
    )


@router.get("/{campaign_id}/plan/versions/{version}")
async def get_version(
    campaign_id: UUID,
    version: int,
    svc: PlanRefinementService = Depends(_get_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Return a specific version of the plan."""
    try:
        await CampaignContextResolver().resolve(campaign_id, user.id)
        plan_version = await svc.get_version(campaign_id, version)
    except PlanNotFoundError:
        raise _not_found(campaign_id)
    if plan_version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found for campaign {campaign_id}",
        )
    doc = dict(plan_version.document)
    if "research_status" not in doc:
        doc["research_status"] = ResearchStatus.NOT_REQUESTED.value
    return success_response(
        data=doc,
        message=f"Version {version} retrieved.",
    )


@router.get("/{campaign_id}/plan/messages")
async def get_messages(
    campaign_id: UUID,
    svc: PlanRefinementService = Depends(_get_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Return the full refinement conversation thread."""
    try:
        await CampaignContextResolver().resolve(campaign_id, user.id)
        messages = await svc.get_messages(campaign_id)
    except PlanNotFoundError:
        raise _not_found(campaign_id)
    return success_response(
        data=[
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "language": m.language,
                "sections_targeted": list(m.sections_targeted),
                "resulting_version": m.resulting_version,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
        message=f"{len(messages)} message(s) found.",
    )


@router.post("/{campaign_id}/plan/messages", status_code=status.HTTP_201_CREATED)
async def refine_plan(
    campaign_id: UUID,
    body: RefinePlanRequest,
    svc: PlanRefinementService = Depends(_get_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Submit a critique and trigger a refinement turn.

    Only the sections the critique targets are regenerated; everything
    else comes back byte-identical. The reply mirrors the marketer's
    language (Roman Urdu, Urdu, English, etc.).
    """
    if not body.content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Critique content cannot be empty.",
        )
    try:
        await CampaignContextResolver().resolve(campaign_id, user.id)
        plan_row = await svc._repo.get_plan_row(campaign_id)
        if not plan_row:
            raise PlanNotFoundError(f"No plan for campaign {campaign_id}")

        inputs = await CampaignContextResolver().resolve(campaign_id, user.id)
        brief = inputs.to_brief()
        revised_plan, reply = await svc.refine_plan(
            campaign_id=campaign_id,
            critique=body.content,
            user_id=UUID(user.id),
            brief=brief,
        )
    except PlanNotFoundError:
        raise _not_found(campaign_id)
    except PlanDraftError as exc:
        raise HTTPException(502, "Plan refinement failed. Please retry.") from exc

    return success_response(
        data={
            "plan": revised_plan.to_document(),
            "reply": reply,
            "version": revised_plan.version,
        },
        message="Plan refined.",
    )


@router.post("/{campaign_id}/plan/approve")
async def approve_plan(
    campaign_id: UUID,
    svc: PlanRefinementService = Depends(_get_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Approve the plan. After this, content generation is unblocked."""
    try:
        await CampaignContextResolver().resolve(campaign_id, user.id)
        approved_plan = await svc.approve_plan(
            campaign_id=campaign_id,
            approved_by=UUID(user.id),
        )
    except PlanNotFoundError:
        raise _not_found(campaign_id)

    return success_response(
        data={
            "plan_id": str(approved_plan.plan_id),
            "campaign_id": str(approved_plan.campaign_id),
            "version": approved_plan.version,
            "approved": approved_plan.approved,
            "status": approved_plan.status.value,
        },
        message="Plan approved. Content generation is now unlocked.",
    )
