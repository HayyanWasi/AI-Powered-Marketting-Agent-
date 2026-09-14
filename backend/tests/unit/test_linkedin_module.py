"""Unit tests for LinkedIn Module (ContentContext, Generators, Gateway, Worker)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.gateways.unipile_gateway import UnipileGateway
from src.modules.linkedin.generators.content_context import ContentContextBuilder
from src.modules.linkedin.generators.post_generator import LinkedInPostGenerator
from src.modules.linkedin.generators.sequence_generator import OutreachSequenceGenerator
from src.modules.linkedin.models import (
    AutoPilotConfig,
    PostStatus,
    WarmupState,
)
from src.modules.linkedin.worker.human_schedule import HumanSchedule
from src.modules.planning.models.campaign_plan import (
    CalendarSlot,
    CampaignPhase,
    CampaignPlan,
    ChannelPlan,
    CoreStrategy,
)
from src.modules.research.models.evidence import ConfidenceScore, EvidenceItem, SourceItem
from src.modules.research.models.research_brief import DimensionSummary, ResearchBrief


@pytest.fixture
def sample_research_brief():
    src = SourceItem(url="https://example.com/report", title="ETL Market Report")
    conf = ConfidenceScore(corroboration=4.0, freshness=4.0, relevance=4.0, credibility=4.0)
    item = EvidenceItem(
        dimension="competitor",
        claim="Competitor X charges $800/month for ETL",
        quote="Pricing starts at $800/month",
        source=src,
        confidence=conf,
    )
    return ResearchBrief(
        user_goal="Drive ETL signups",
        company_name="Acme Data",
        competitor=DimensionSummary(dimension="competitor", evidence_items=(item,)),
    )


@pytest.fixture
def sample_plan():
    slot = CalendarSlot(
        slot_id="slot-1",
        date="2026-08-20",
        theme="Cost of Manual Pipelines",
        messaging_pillar="Cloud ETL ROI",
        cta="Register Now",
        phase=CampaignPhase.LAUNCH,
    )
    return CampaignPlan(
        title="Acme Cloud Launch",
        core_strategy=CoreStrategy(
            unique_selling_proposition="Zero-config ETL in 5 minutes",
            tone_of_voice="Professional & Data-driven",
        ),
        channel_plan=ChannelPlan(calendar_slots=(slot,)),
    )


def test_content_context_builder(sample_plan, sample_research_brief):
    slot = sample_plan.channel_plan.calendar_slots[0]
    ctx = ContentContextBuilder.build_context(slot, sample_plan, sample_research_brief)

    assert ctx.slot_id == "slot-1"
    assert ctx.theme == "Cost of Manual Pipelines"
    assert ctx.messaging_pillar == "Cloud ETL ROI"
    assert ctx.usp == "Zero-config ETL in 5 minutes"
    assert len(ctx.researched_facts) == 1
    assert ctx.researched_facts[0].claim == "Competitor X charges $800/month for ETL"


@pytest.mark.asyncio
async def test_post_generator(sample_plan, sample_research_brief):
    mock_llm = MagicMock()
    mock_llm.generate_json = AsyncMock(
        return_value={
            "hook": "Tired of paying $800/mo for manual ETL?",
            "body": "Acme Data automates your pipelines in under 5 minutes.",
            "cta": "Click link in bio to register for our webinar.",
        }
    )

    generator = LinkedInPostGenerator(llm_router=mock_llm)
    posts = await generator.generate_all_posts(uuid4(), sample_plan, sample_research_brief)

    assert len(posts) == 1
    post = posts[0]
    assert post.hook == "Tired of paying $800/mo for manual ETL?"
    assert "Acme Data automates" in post.body
    assert post.status == PostStatus.SCHEDULED
    assert post.scheduled_at is not None
    assert len(post.evidence_ids) == 1


@pytest.mark.asyncio
async def test_sequence_generator(sample_plan, sample_research_brief):
    mock_llm = MagicMock()
    mock_llm.generate_json = AsyncMock(
        return_value={
            "step_invite_msg": "Hi Sarah, loved your work in pipeline architecture.",
            "step_value_msg": "Hi Sarah, here is our latest report on Cloud ETL ROI.",
            "step_followup_msg": "Hi Sarah, just following up on our guide.",
        }
    )

    generator = OutreachSequenceGenerator(llm_router=mock_llm)
    seq = await generator.generate_sequence(uuid4(), sample_plan, sample_research_brief)

    assert "Hi Sarah" in seq.step_invite_msg
    assert "Cloud ETL ROI" in seq.step_value_msg


@pytest.mark.asyncio
async def test_unipile_gateway_list_accounts():
    gateway = UnipileGateway(dsn="https://api1.unipile.com:13XXX", token="test_token")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": [{"id": "acc_123", "name": "LinkedIn User"}]}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        accounts = await gateway.list_accounts()
        assert len(accounts) == 1
        assert accounts[0]["id"] == "acc_123"


def test_human_schedule_planning():
    planner = HumanSchedule()
    config = AutoPilotConfig()
    warmup = WarmupState(account_id="acc_123")
    schedule = planner.plan_and_schedule_day(config, warmup)
    assert len(schedule.sessions) >= config.sessions_per_day_min
    assert schedule.work_start < schedule.work_end
