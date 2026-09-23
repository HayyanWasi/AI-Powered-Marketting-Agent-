from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.models.brand_context import BrandContext
from src.models.campaign import Campaign
from src.models.llm import LLMResponse, TokenUsage
from src.modules.planning.agents import panel
from src.modules.planning.models.brief import PlanBrief
from src.services.campaign_context_service import CampaignInputs


SENTINELS = {
    "campaign_type": "app_launch",
    "campaign_name": "Prompt Sentinel App",
    "objective": "Acquire early registered users",
    "value_proposition": "Book verified beauty services in three taps",
    "cta_url": "https://sentinel.invalid/download",
}

RESPONSES = {
    "plan_audience_research": {"objective": "Acquire users", "smart_goals": [], "personas": []},
    "plan_positioning": {
        "positioning_statement": "Verified services in three taps.",
        "messaging_pillars": ["Trust"],
    },
    "plan_channel": {"platforms": [], "phases": [], "calendar_slots": []},
    "plan_measurement": {"kpis": []},
    "plan_competitive": {"landscape": [], "differentiation_angle": "Verified supply."},
}


class CapturingLLM:
    def __init__(self):
        self.requests = []

    def is_local_ollama(self) -> bool:
        return False

    def has_ollama_provider(self) -> bool:
        return False

    def generate(self, request):
        self.requests.append(request)
        return LLMResponse(
            text=json.dumps(RESPONSES[request.prompt_name]),
            token_usage=TokenUsage(),
            provider="test",
            model="test",
        )


def make_brand() -> BrandContext:
    return BrandContext(
        company_profile_id=uuid4(),
        company_name="Audit Sentinel Brand",
        brand_tone="Direct, concise",
    )


def make_persisted_brief(**intake_overrides) -> PlanBrief:
    intake = {**SENTINELS, **intake_overrides}
    campaign = Campaign(company_profile_id=uuid4(), platforms=["LinkedIn", "Instagram"])
    return CampaignInputs(campaign=campaign, brand=make_brand(), intake=intake).to_brief()


def test_persisted_intake_hydrates_plan_brief_and_template_variables():
    brief = make_persisted_brief()

    for field, value in SENTINELS.items():
        assert getattr(brief, field) == value
        assert brief.to_template_vars()[field] == value
    assert brief.company_name == "Audit Sentinel Brand"
    assert brief.brand_tone == "Direct, concise"


@pytest.mark.asyncio
async def test_all_five_specialists_receive_canonical_campaign_context():
    brief = make_persisted_brief()
    llm = CapturingLLM()

    with (
        patch.object(panel, "_parallel_research", new=AsyncMock(return_value="evidence")),
        patch.object(
            panel,
            "_parallel_competitor_research",
            new=AsyncMock(return_value="competitor evidence"),
        ),
    ):
        for specialist in panel.SPECIALISTS.values():
            await specialist(brief, llm=llm)

    assert len(llm.requests) == 5
    assert {request.prompt_name for request in llm.requests} == {
        "plan_audience_research",
        "plan_positioning",
        "plan_channel",
        "plan_measurement",
        "plan_competitive",
    }
    for request in llm.requests:
        for value in (*SENTINELS.values(), "Audit Sentinel Brand", "Direct, concise"):
            assert value in request.user_prompt
        assert "{event_name}" not in request.user_prompt


def test_app_launch_prompt_keeps_missing_event_fields_unspecified():
    prompt = panel.render_template("plan_positioning", make_persisted_brief().to_template_vars())

    assert "Event date: (not specified)" in prompt
    assert "Venue: (not specified)" in prompt
    assert "Curriculum: (not specified)" in prompt
    assert "Registration link: (not specified)" in prompt
    assert "Speakers/Guests:\n(none)" in prompt
    assert "capacity" not in prompt.lower()


def test_existing_event_fields_remain_in_shared_prompt():
    brief = make_persisted_brief(
        campaign_type="webinar",
        campaign_name="Event Sentinel",
        event_date="2026-11-05",
        venue="Sentinel Hall",
        curriculum_breakdown="Three verified modules",
        registration_link="https://sentinel.invalid/register",
        has_guest=True,
        guest_name="Guest Sentinel",
        guest_title="Founder",
    )

    # Event details are role-specific after compaction: the specialists that can
    # legitimately feature a speaker/venue/date (positioning, channel) receive
    # the event block; measurement/audience/competitive do not.
    vars_ = brief.to_template_vars()
    for template_name in ("plan_positioning", "plan_channel"):
        prompt = panel.render_template(template_name, vars_)
        for value in (
            "webinar",
            "Event Sentinel",
            "2026-11-05",
            "Sentinel Hall",
            "Three verified modules",
            "https://sentinel.invalid/register",
            "Guest Sentinel",
            "Founder",
        ):
            assert value in prompt, f"{value!r} missing from {template_name}"

    # Campaign-type/name identity still reaches measurement via the core brief,
    # even though event-only fields (venue/curriculum) no longer do.
    measurement_prompt = panel.render_template("plan_measurement", vars_)
    assert "webinar" in measurement_prompt
    assert "Event Sentinel" in measurement_prompt
    assert "Sentinel Hall" not in measurement_prompt
