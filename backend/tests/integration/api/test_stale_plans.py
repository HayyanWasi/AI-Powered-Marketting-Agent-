from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.main import app
from src.models.brand_context import BrandContext
from src.models.campaign import Campaign, Goals
from src.modules.planning.models.campaign_plan import (
    CalendarSlot,
    CampaignPlan,
    ChannelPlan,
    InputIdentity,
)
from src.modules.planning.services.plan_refinement_service import PlanRefinementService
from src.services.campaign_context_service import CampaignInputs, check_plan_freshness

CAMPAIGN_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PROFILE_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_ID = "00000000-0000-0000-0000-00000000000a"


def _inputs(
    *,
    objective: str = "Acquire registrations",
    cta_url: str = "https://sentinel.invalid/register",
    brand_tone: str = "Confident and practical",
    updated_at: str = "2026-09-17T10:00:00Z",
    ui_state: str = "strategy-panel-open",
    intake_overrides: dict | None = None,
) -> CampaignInputs:
    campaign = Campaign(
        id=CAMPAIGN_ID,
        company_profile_id=PROFILE_ID,
        name="Freshness Sentinel",
        goals=Goals(primary=objective),
        platforms=["LinkedIn"],
        updated_at=datetime.now(UTC),
    )
    brand = BrandContext(
        company_profile_id=PROFILE_ID,
        company_name="Sentinel Labs",
        profile_updated_at=updated_at,
        description="Reliable growth tools",
        target_audience="Product teams",
        brand_tone=brand_tone,
        guidelines="Use direct language.",
    )
    intake = {
        "campaign_type": "app_launch",
        "campaign_name": "Freshness Sentinel",
        "objective": objective,
        "value_proposition": "Fast, reliable onboarding",
        "cta_url": cta_url,
        "target_audience": "Product teams",
        "updated_at": updated_at,
        "chat_display_state": ui_state,
    }
    intake.update(intake_overrides or {})
    return CampaignInputs(campaign=campaign, brand=brand, intake=intake)


def _plan_for(inputs: CampaignInputs, *, version: int = 1) -> CampaignPlan:
    brief = inputs.to_brief()
    identity = InputIdentity(
        campaign_id=CAMPAIGN_ID,
        company_profile_id=PROFILE_ID,
        brand_version=brief.brand_version,
        intake_hash=brief.intake_hash,
        user_goal=brief.user_goal,
    )
    return CampaignPlan(
        campaign_id=CAMPAIGN_ID,
        version=version,
        source_brief=brief.model_dump(mode="json"),
        input_identity=identity,
        channel_plan=ChannelPlan(
            calendar_slots=(CalendarSlot(platform="LinkedIn", theme="Sentinel"),)
        ),
    )


def test_current_plan_matches_canonical_sentinel_inputs() -> None:
    inputs = _inputs()

    assert check_plan_freshness(_plan_for(inputs), inputs) == (False, None)


def test_relevant_objective_change_marks_plan_stale() -> None:
    original = _inputs()
    changed = _inputs(objective="Acquire app downloads")

    assert check_plan_freshness(_plan_for(original), changed)[0] is True


def test_cta_change_marks_plan_stale() -> None:
    original = _inputs()
    changed = _inputs(cta_url="https://sentinel.invalid/download")

    assert check_plan_freshness(_plan_for(original), changed)[0] is True


def test_brand_change_marks_plan_stale() -> None:
    original = _inputs()
    changed = _inputs(brand_tone="Warm and conversational")

    assert check_plan_freshness(_plan_for(original), changed)[0] is True


@pytest.mark.parametrize(
    ("field", "before", "after"),
    [
        ("campaign_type", "webinar", "physical_event"),
        ("campaign_name", "Freshness Sentinel", "Freshness Sentinel 2"),
        ("target_audience", "Product teams", "Growth teams"),
        ("registration_link", "https://sentinel.invalid/r1", "https://sentinel.invalid/r2"),
        ("outcome_deliverable", "Starter kit", "Implementation guide"),
        ("event_date", "2026-10-01", "2026-10-02"),
        ("venue", "Hall A", "Hall B"),
    ],
)
def test_other_canonical_plan_input_changes_mark_plan_stale(
    field: str, before: str, after: str
) -> None:
    original = _inputs(intake_overrides={field: before})
    changed = _inputs(intake_overrides={field: after})

    assert check_plan_freshness(_plan_for(original), changed)[0] is True


def test_irrelevant_timestamp_and_ui_state_changes_remain_current() -> None:
    original = _inputs(updated_at="2026-09-17T10:00:00Z", ui_state="plan-open")
    changed = _inputs(updated_at="2026-09-18T11:30:00Z", ui_state="artifacts-open")

    assert check_plan_freshness(_plan_for(original), changed) == (False, None)


def test_legacy_timestamp_identity_is_stale() -> None:
    inputs = _inputs()
    plan = _plan_for(inputs).model_copy(
        update={
            "input_identity": InputIdentity(
                campaign_id=CAMPAIGN_ID,
                company_profile_id=PROFILE_ID,
                brand_version=inputs.brand.profile_updated_at,
                intake_hash=inputs.intake["updated_at"],
            )
        }
    )

    assert check_plan_freshness(plan, inputs)[0] is True


@pytest.fixture
def user_client():
    app.dependency_overrides[get_authenticated_user] = lambda: AuthenticatedUser(
        id=USER_ID, roles=["user"], permissions=[]
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_stale_plan_blocks_linkedin_before_generation(user_client: TestClient) -> None:
    old_inputs = _inputs()
    changed_inputs = _inputs(objective="Acquire app downloads")
    old_plan = _plan_for(old_inputs)

    with (
        patch("src.api.v1.linkedin.CampaignContextResolver") as resolver,
        patch("src.api.v1.linkedin.PlanRefinementService") as plan_service,
        patch("src.api.v1.linkedin.LinkedInPostGenerator") as post_generator,
    ):
        resolver.return_value.resolve = AsyncMock(return_value=changed_inputs)
        plan_service.return_value.get_plan = AsyncMock(return_value=old_plan)

        response = user_client.post(
            f"/api/v1/linkedin/campaigns/{CAMPAIGN_ID}/generate",
            json={},
        )

    assert response.status_code == 409
    assert "regenerate" in response.json()["message"].lower()
    post_generator.assert_not_called()


@pytest.mark.asyncio
async def test_successful_regeneration_persists_current_fingerprint() -> None:
    changed_inputs = _inputs(objective="Acquire app downloads")
    brief = changed_inputs.to_brief()
    repository = MagicMock()
    repository.get_or_create_plan_row = AsyncMock(return_value={"id": str(PROFILE_ID)})
    repository.get_latest_version = AsyncMock(return_value=None)
    repository.add_version = AsyncMock()
    graph = MagicMock()
    graph.ainvoke = AsyncMock(return_value={"plan": CampaignPlan()})

    with patch(
        "src.modules.planning.services.plan_refinement_service.plan_graph.compile_graph",
        return_value=graph,
    ):
        regenerated = await PlanRefinementService(repository).draft_plan(
            campaign_id=CAMPAIGN_ID,
            created_by=UUID(USER_ID),
            brief=brief,
        )

    repository.add_version.assert_awaited_once()
    assert check_plan_freshness(regenerated, changed_inputs) == (False, None)


@pytest.mark.asyncio
async def test_failed_regeneration_leaves_old_plan_stale() -> None:
    original = _inputs()
    changed = _inputs(objective="Acquire app downloads")
    old_plan = _plan_for(original)
    repository = MagicMock()
    repository.get_or_create_plan_row = AsyncMock(return_value={"id": str(PROFILE_ID)})
    repository.get_latest_version = AsyncMock(return_value=MagicMock(version=1))
    repository.add_version = AsyncMock(side_effect=RuntimeError("persistence failed"))
    graph = MagicMock()
    graph.ainvoke = AsyncMock(return_value={"plan": CampaignPlan()})

    with (
        patch(
            "src.modules.planning.services.plan_refinement_service.plan_graph.compile_graph",
            return_value=graph,
        ),
        pytest.raises(RuntimeError, match="persistence failed"),
    ):
        await PlanRefinementService(repository).draft_plan(
            campaign_id=CAMPAIGN_ID,
            created_by=UUID(USER_ID),
            brief=changed.to_brief(),
        )

    assert check_plan_freshness(old_plan, changed)[0] is True
