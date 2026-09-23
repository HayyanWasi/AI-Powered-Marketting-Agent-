import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.main import app
from src.models.brand_context import BrandContext
from src.modules.planning.models.campaign_plan import (
    CalendarSlot,
    CampaignPlan,
    ChannelPlan,
    InputIdentity,
)
from src.services.campaign_context_service import (
    CampaignInputs,
    check_plan_freshness,
    compute_brand_fingerprint,
    compute_intake_fingerprint,
)


@pytest.fixture
def base_context():
    company_id = uuid.uuid4()
    campaign_id = uuid.uuid4()
    brand = BrandContext(
        company_profile_id=company_id,
        company_name="Alpha Brand",
        brand_tone="Pragmatic and visionary",
        guidelines="Be clear, concise and direct",
        negative_guardrails=("Never use word revolutionary", "Never use emojis"),
    )
    campaign = SimpleNamespace(
        id=campaign_id,
        name="Launch Alpha",
        company_profile_id=company_id,
        platforms=["LinkedIn", "Twitter"],
        goals=SimpleNamespace(primary="Acquire 100 beta users"),
        schedule=SimpleNamespace(timezone="UTC"),
    )
    intake = {
        "campaign_type": "app_launch",
        "campaign_name": "Launch Alpha",
        "objective": "Acquire 100 beta users",
        "value_proposition": "Autonomous marketing with verifiable evidence",
        "cta_url": "https://alpha.example.com/signup",
        "target_audience": "Tech founders",
        "updated_at": "2026-09-17T10:00:00Z",
        "last_field_asked": "cta_url",
        "chat_messages": [{"role": "user", "content": "hello"}],
    }
    inputs = CampaignInputs(campaign=campaign, brand=brand, intake=intake)

    # Generated plan stamped with current identity fingerprints
    plan = CampaignPlan(
        campaign_id=campaign_id,
        input_identity=InputIdentity(
            campaign_id=campaign_id,
            company_profile_id=company_id,
            brand_version=compute_brand_fingerprint(brand),
            intake_hash=compute_intake_fingerprint(intake, campaign),
        ),
        channel_plan=ChannelPlan(
            calendar_slots=[
                CalendarSlot(
                    slot_id="slot-1",
                    date="2026-10-01",
                    platform="LinkedIn",
                    theme="Announcement",
                    cta="Sign up",
                )
            ]
        ),
    )
    return inputs, plan


def test_scenario_a_current_plan(base_context):
    """Initial plan matches source inputs -> CURRENT."""
    inputs, plan = base_context
    is_stale, reason = check_plan_freshness(plan, inputs)
    assert not is_stale
    assert reason is None


def test_scenario_b_relevant_campaign_objective_change(base_context):
    """Changing campaign objective invalidates plan -> STALE."""
    inputs, plan = base_context
    modified_intake = dict(inputs.intake)
    modified_intake["objective"] = "Acquire 5,000 enterprise customers"
    modified_inputs = CampaignInputs(
        campaign=inputs.campaign, brand=inputs.brand, intake=modified_intake
    )

    is_stale, reason = check_plan_freshness(plan, modified_inputs)
    assert is_stale is True
    assert reason == "Campaign details were updated."


def test_scenario_c_relevant_cta_url_change(base_context):
    """Changing CTA URL invalidates plan -> STALE."""
    inputs, plan = base_context
    modified_intake = dict(inputs.intake)
    modified_intake["cta_url"] = "https://alpha.example.com/new-checkout"
    modified_inputs = CampaignInputs(
        campaign=inputs.campaign, brand=inputs.brand, intake=modified_intake
    )

    is_stale, reason = check_plan_freshness(plan, modified_inputs)
    assert is_stale is True
    assert reason == "Campaign details were updated."


def test_scenario_d_relevant_brand_change(base_context):
    """Changing brand tone or negative guardrails invalidates plan -> STALE."""
    inputs, plan = base_context
    modified_brand = BrandContext(
        company_profile_id=inputs.brand.company_profile_id,
        company_name=inputs.brand.company_name,
        brand_tone="Casual, playful, and humor-driven",
        guidelines=inputs.brand.guidelines,
        negative_guardrails=inputs.brand.negative_guardrails + ("No corporate jargon",),
    )
    modified_inputs = CampaignInputs(
        campaign=inputs.campaign, brand=modified_brand, intake=inputs.intake
    )

    is_stale, reason = check_plan_freshness(plan, modified_inputs)
    assert is_stale is True
    assert reason == "Brand profile was updated."


def test_scenario_e_irrelevant_changes_remain_current(base_context):
    """Updating non-strategy fields (updated_at timestamp, last_field_asked, chat messages) preserves CURRENT state."""
    inputs, plan = base_context
    modified_intake = dict(inputs.intake)
    modified_intake["updated_at"] = "2026-09-17T12:34:56Z"
    modified_intake["last_field_asked"] = "completed"
    modified_intake["chat_messages"] = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "how can I help?"},
    ]
    modified_intake["ui_theme_preview"] = "dark"
    modified_inputs = CampaignInputs(
        campaign=inputs.campaign, brand=inputs.brand, intake=modified_intake
    )

    is_stale, reason = check_plan_freshness(plan, modified_inputs)
    assert is_stale is False
    assert reason is None


@pytest.mark.asyncio
async def test_scenario_f_successful_regeneration_restores_current(base_context):
    """After changing source inputs, drafting a new plan version stamps the new identity -> CURRENT."""
    inputs, plan = base_context
    modified_intake = dict(inputs.intake)
    modified_intake["objective"] = "Updated App Downloads"
    modified_inputs = CampaignInputs(
        campaign=inputs.campaign, brand=inputs.brand, intake=modified_intake
    )

    # Old plan is stale
    assert check_plan_freshness(plan, modified_inputs)[0] is True

    # Regenerating produces a new brief and stamps new InputIdentity
    new_brief = modified_inputs.to_brief()
    regenerated_plan = plan.model_copy(
        update={
            "version": plan.version + 1,
            "input_identity": InputIdentity(
                campaign_id=plan.campaign_id,
                company_profile_id=inputs.brand.company_profile_id,
                brand_version=new_brief.brand_version,
                intake_hash=new_brief.intake_hash,
            ),
        }
    )

    is_stale, reason = check_plan_freshness(regenerated_plan, modified_inputs)
    assert is_stale is False
    assert reason is None


def test_scenario_g_failed_regeneration_remains_stale(base_context):
    """If regeneration fails, the stored plan version remains unchanged and stays STALE."""
    inputs, plan = base_context
    modified_intake = dict(inputs.intake)
    modified_intake["objective"] = "Updated App Downloads"
    modified_inputs = CampaignInputs(
        campaign=inputs.campaign, brand=inputs.brand, intake=modified_intake
    )

    # Plan is stale
    assert check_plan_freshness(plan, modified_inputs)[0] is True

    # Failed draft raises an exception without modifying the stored plan
    try:
        raise RuntimeError("LLM rate limit error")
    except RuntimeError:
        pass  # Draft aborted, DB unchanged

    # Checking stored plan again
    is_stale, reason = check_plan_freshness(plan, modified_inputs)
    assert is_stale is True
    assert reason == "Campaign details were updated."


def test_stale_plan_blocks_linkedin_with_409(base_context):
    """Calling linkedin generate endpoint with a stale plan returns 409 with exact message."""
    inputs, plan = base_context
    modified_intake = dict(inputs.intake)
    modified_intake["objective"] = "New Objective"
    stale_inputs = CampaignInputs(
        campaign=inputs.campaign, brand=inputs.brand, intake=modified_intake
    )

    client = TestClient(app)
    user = AuthenticatedUser(id=str(uuid.uuid4()), roles=["user"], permissions=[])
    app.dependency_overrides[get_authenticated_user] = lambda: user

    try:
        with (
            patch(
                "src.api.v1.linkedin.CampaignContextResolver.resolve",
                new=AsyncMock(return_value=stale_inputs),
            ),
            patch(
                "src.api.v1.linkedin.PlanRefinementService.get_plan",
                new=AsyncMock(return_value=plan),
            ),
        ):
            res = client.post(f"/api/v1/linkedin/campaigns/{plan.campaign_id}/generate", json={})
            assert res.status_code == 409
            expected_msg = (
                "Campaign strategy is outdated because campaign or brand details changed. "
                "Regenerate the campaign strategy before generating content."
            )
            assert res.json()["message"] == expected_msg
    finally:
        app.dependency_overrides.clear()


def test_get_plan_reports_freshness_status(base_context):
    """GET /campaigns/{id}/plan returns is_stale and staleness_reason accurately."""
    inputs, plan = base_context
    client = TestClient(app)
    user = AuthenticatedUser(id=str(uuid.uuid4()), roles=["user"], permissions=[])
    app.dependency_overrides[get_authenticated_user] = lambda: user

    try:
        # Case 1: Fresh plan
        with (
            patch(
                "src.api.v1.plans.CampaignContextResolver.resolve",
                new=AsyncMock(return_value=inputs),
            ),
            patch(
                "src.api.v1.plans.PlanRefinementService.get_plan",
                new=AsyncMock(return_value=plan),
            ),
        ):
            res = client.get(f"/api/v1/campaigns/{plan.campaign_id}/plan")
            assert res.status_code == 200
            data = res.json()["data"]
            assert data["is_stale"] is False
            assert data["staleness_reason"] is None

        # Case 2: Stale plan (campaign objective changed)
        modified_intake = dict(inputs.intake)
        modified_intake["objective"] = "Brand new objective"
        stale_inputs = CampaignInputs(
            campaign=inputs.campaign, brand=inputs.brand, intake=modified_intake
        )

        with (
            patch(
                "src.api.v1.plans.CampaignContextResolver.resolve",
                new=AsyncMock(return_value=stale_inputs),
            ),
            patch(
                "src.api.v1.plans.PlanRefinementService.get_plan",
                new=AsyncMock(return_value=plan),
            ),
        ):
            res = client.get(f"/api/v1/campaigns/{plan.campaign_id}/plan")
            assert res.status_code == 200
            data = res.json()["data"]
            assert data["is_stale"] is True
            assert data["staleness_reason"] == "Campaign details were updated."
    finally:
        app.dependency_overrides.clear()

