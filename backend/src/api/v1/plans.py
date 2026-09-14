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
from src.modules.planning.models.brief import PlanBrief
from src.modules.planning.repositories.plan_repository import PlanNotFoundError
from src.modules.planning.services.plan_refinement_service import (
    PlanDraftError,
    PlanRefinementService,
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
    guests_list = list(body.guests)
    user_goal = body.user_goal
    event_name = body.event_name

    # Hydrate from saved intake checklist & campaign record in DB
    category = ""
    target_audience = ""
    curriculum_breakdown = ""
    outcome_deliverable = ""
    ticket_price = "Free"
    event_date = body.event_date
    venue = body.venue
    registration_link = body.registration_link

    try:
        from src.repositories.base import BaseRepository

        repo = BaseRepository("intake_checklists")
        res = (
            repo.client.table("intake_checklists")
            .select("*")
            .eq("campaign_id", str(campaign_id))
            .execute()
        )
        if res.data:
            cdata = res.data[0]
            if not event_name and cdata.get("event_name"):
                event_name = cdata.get("event_name")
            if not event_date and cdata.get("event_date"):
                event_date = cdata.get("event_date")
            if not venue and cdata.get("venue"):
                venue = cdata.get("venue")
            if not registration_link and cdata.get("registration_link"):
                registration_link = cdata.get("registration_link")

            category = cdata.get("category") or ""
            target_audience = cdata.get("target_audience") or ""
            curriculum_breakdown = cdata.get("curriculum_breakdown") or ""
            outcome_deliverable = cdata.get("outcome_deliverable") or ""
            ticket_price = cdata.get("is_free_or_paid") or "Free"

            if cdata.get("has_guest") is True:
                g_name = cdata.get("guest_name")
                g_title = cdata.get("guest_title")
                if g_name and not any(g_name.lower() in g.lower() for g in guests_list):
                    g_str = f"{g_name} ({g_title})" if g_title else g_name
                    guests_list.append(g_str)
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(
            "Could not hydrate intake checklist details in draft_plan: %s", e
        )

    brief = PlanBrief(
        user_goal=user_goal,
        company_name=body.company_name,
        brand_tone=body.brand_tone,
        brand_guidelines=body.brand_guidelines,
        event_name=event_name,
        category=category,
        target_audience=target_audience,
        curriculum_breakdown=curriculum_breakdown,
        outcome_deliverable=outcome_deliverable,
        ticket_price=ticket_price,
        event_date=event_date,
        venue=venue,
        registration_link=registration_link,
        platforms=tuple(body.platforms),
        guests=tuple(guests_list),
    )

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


@router.get("/{campaign_id}/plan")
async def get_plan(
    campaign_id: UUID,
    svc: PlanRefinementService = Depends(_get_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Return the current plan document."""
    try:
        plan = await svc.get_plan(campaign_id)
    except PlanNotFoundError:
        raise _not_found(campaign_id)
    return success_response(data=plan.to_document(), message="Plan retrieved.")


@router.get("/{campaign_id}/plan/versions")
async def list_versions(
    campaign_id: UUID,
    svc: PlanRefinementService = Depends(_get_service),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Return all plan versions, newest first."""
    try:
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
        plan_version = await svc.get_version(campaign_id, version)
    except PlanNotFoundError:
        raise _not_found(campaign_id)
    if plan_version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found for campaign {campaign_id}",
        )
    return success_response(
        data=plan_version.document,
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
        plan_row = await svc._repo.get_plan_row(campaign_id)
        if not plan_row:
            raise PlanNotFoundError(f"No plan for campaign {campaign_id}")

        # Re-build the brief from the latest plan's stored data so we don't
        # require the caller to resend all fields on every message.
        latest_plan = await svc.get_plan(campaign_id)
        brief = PlanBrief(
            user_goal="",
            company_name="",
            event_name=latest_plan.title,
            platforms=tuple(p.platform for p in latest_plan.channel_plan.platforms),
        )
        revised_plan, reply = await svc.refine_plan(
            campaign_id=campaign_id,
            critique=body.content,
            user_id=UUID(user.id),
            brief=brief,
        )
    except PlanNotFoundError:
        raise _not_found(campaign_id)

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
