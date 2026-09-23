from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.main import app
from src.models.brand_context import BrandContext
from src.modules.planning.agents.panel import audience_research, competitive
from src.modules.planning.models.brief import PlanBrief
from src.modules.planning.models.campaign_plan import (
    CalendarSlot,
    CampaignPlan,
    ChannelPlan,
    Competitive,
    CoreStrategy,
    Measurement,
    PlanStatus,
    ResearchStatus,
)
from src.modules.planning.services.plan_refinement_service import PlanRefinementService

SAMPLE_BRAND = BrandContext(
    company_profile_id=uuid4(),
    company_name="Apex Marketing AI",
    brand_tone="Analytical, authoritative, concise",
    negative_guardrails=("Never use buzzwords",),
)


def _sample_brief(research_context: dict | None = None) -> PlanBrief:
    return PlanBrief(
        campaign_id=str(uuid4()),
        company_profile_id=str(SAMPLE_BRAND.company_profile_id),
        brand=SAMPLE_BRAND,
        company_name="Apex Marketing AI",
        campaign_type="app_launch",
        campaign_name="Apex Launch",
        objective="Drive 10,000 active trial signups",
        value_proposition="Autonomous AI campaign workflows",
        cta_url="https://apex.ai/launch",
        category="marketing_automation",
        target_audience="B2B Growth Leaders",
        research_context=research_context,
    )


def _sample_plan(
    campaign_id: UUID,
    research_status: ResearchStatus = ResearchStatus.NOT_REQUESTED,
    research_reason: str = "",
) -> CampaignPlan:
    return CampaignPlan(
        campaign_id=campaign_id,
        version=1,
        title="Apex Strategic Launch Plan",
        status=PlanStatus.DRAFT,
        research_status=research_status,
        research_status_reason=research_reason,
        core_strategy=CoreStrategy(
            positioning_statement="The leading workflow agent.",
            unique_selling_proposition="Zero-manual prompts.",
        ),
        # A complete, valid plan always has a non-empty calendar — draft_plan
        # now refuses to persist a plan with an empty channel calendar, since
        # that reflects an upstream specialist failure rather than a real draft.
        channel_plan=ChannelPlan(calendar_slots=(CalendarSlot(),)),
        measurement=Measurement(),
        competitive=Competitive(),
    )


# ── Test A: Successful Research ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_successful_research_marked_available_and_persisted():
    """A: Research returns usable evidence -> status is available, evidence reaches plan."""
    campaign_id = uuid4()
    user_id = uuid4()
    brief = _sample_brief()

    usable_research_result = {
        "session_id": str(uuid4()),
        "tier": "Standard",
        "research_brief": {
            "market": {
                "key_findings": ["B2B marketing automation grew 28% YoY in 2026."],
                "evidence_items": [{"claim": "Market growth", "confidence": {"overall": 4.5}}],
            },
            "competitor": {
                "key_findings": ["Legacy tools lack native LLM orchestration."],
                "evidence_items": [],
            },
        },
        "evidence_graph": {"nodes": {"node1": {}}, "edges": []},
    }

    mock_research_svc = MagicMock()
    mock_research_svc.draft_research = AsyncMock(return_value=usable_research_result)

    drafted_plan = _sample_plan(campaign_id, ResearchStatus.AVAILABLE, "Live research completed with usable evidence.")
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={"plan": drafted_plan, "failures": []})

    mock_repo = MagicMock()
    mock_repo.get_or_create_plan_row = AsyncMock(return_value={"id": str(uuid4())})
    mock_repo.get_latest_version = AsyncMock(return_value=None)
    mock_repo.add_version = AsyncMock()

    service = PlanRefinementService(repository=mock_repo)

    with (
        patch("src.modules.planning.services.plan_refinement_service.ResearchEngineService", return_value=mock_research_svc),
        patch("src.modules.planning.services.plan_refinement_service.plan_graph.compile_graph", return_value=mock_graph),
        patch("src.modules.planning.services.plan_refinement_service.normalize_calendar_slots", side_effect=lambda slots, sp: slots),
    ):
        result_plan = await service.draft_plan(
            campaign_id=campaign_id,
            created_by=user_id,
            brief=brief,
            tier="Standard",
        )

    assert result_plan.research_status == ResearchStatus.AVAILABLE
    assert "usable evidence" in result_plan.research_status_reason.lower()

    # Check persistence received truthful metadata
    mock_repo.add_version.assert_awaited_once()
    persisted_plan = mock_repo.add_version.call_args[0][1]
    assert persisted_plan.research_status == ResearchStatus.AVAILABLE


# ── Test B: Research Exception ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_research_exception_marks_status_degraded():
    """B: Research throws an exception -> planning continues, status marked degraded without fake evidence."""
    campaign_id = uuid4()
    user_id = uuid4()
    brief = _sample_brief()

    mock_research_svc = MagicMock()
    mock_research_svc.draft_research = AsyncMock(side_effect=RuntimeError("Search provider API timeout"))

    drafted_plan = _sample_plan(campaign_id)
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={"plan": drafted_plan, "failures": []})

    mock_repo = MagicMock()
    mock_repo.get_or_create_plan_row = AsyncMock(return_value={"id": str(uuid4())})
    mock_repo.get_latest_version = AsyncMock(return_value=None)
    mock_repo.add_version = AsyncMock()

    service = PlanRefinementService(repository=mock_repo)

    with (
        patch("src.modules.planning.services.plan_refinement_service.ResearchEngineService", return_value=mock_research_svc),
        patch("src.modules.planning.services.plan_refinement_service.plan_graph.compile_graph", return_value=mock_graph),
        patch("src.modules.planning.services.plan_refinement_service.normalize_calendar_slots", side_effect=lambda slots, sp: slots),
    ):
        result_plan = await service.draft_plan(
            campaign_id=campaign_id,
            created_by=user_id,
            brief=brief,
            tier="Standard",
        )

    assert result_plan.research_status == ResearchStatus.DEGRADED
    assert "Search provider API timeout" in result_plan.research_status_reason

    # Verify no fake research evidence was fabricated in template vars
    persisted_plan = mock_repo.add_version.call_args[0][1]
    assert persisted_plan.research_status == ResearchStatus.DEGRADED
    source_brief = PlanBrief.model_validate(persisted_plan.source_brief)
    template_vars = source_brief.to_template_vars()
    assert "RESEARCH FAILED" in template_vars["research"]
    assert "B2B marketing automation grew" not in template_vars["research"]


# ── Test C: Empty Research Results ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_research_results_marked_no_evidence():
    """C: Search executes successfully but yields no usable evidence -> status is no_evidence."""
    campaign_id = uuid4()
    user_id = uuid4()
    brief = _sample_brief()

    empty_research_result = {
        "session_id": str(uuid4()),
        "tier": "Standard",
        "research_brief": {
            "market": {"key_findings": [], "evidence_items": []},
            "competitor": {"key_findings": [], "evidence_items": []},
            "audience": {"key_findings": [], "evidence_items": []},
            "content": {"key_findings": [], "evidence_items": []},
            "channel": {"key_findings": [], "evidence_items": []},
            "trend": {"key_findings": [], "evidence_items": []},
        },
        "evidence_graph": {"nodes": {}, "edges": []},
    }

    mock_research_svc = MagicMock()
    mock_research_svc.draft_research = AsyncMock(return_value=empty_research_result)

    drafted_plan = _sample_plan(campaign_id)
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={"plan": drafted_plan, "failures": []})

    mock_repo = MagicMock()
    mock_repo.get_or_create_plan_row = AsyncMock(return_value={"id": str(uuid4())})
    mock_repo.get_latest_version = AsyncMock(return_value=None)
    mock_repo.add_version = AsyncMock()

    service = PlanRefinementService(repository=mock_repo)

    with (
        patch("src.modules.planning.services.plan_refinement_service.ResearchEngineService", return_value=mock_research_svc),
        patch("src.modules.planning.services.plan_refinement_service.plan_graph.compile_graph", return_value=mock_graph),
        patch("src.modules.planning.services.plan_refinement_service.normalize_calendar_slots", side_effect=lambda slots, sp: slots),
    ):
        result_plan = await service.draft_plan(
            campaign_id=campaign_id,
            created_by=user_id,
            brief=brief,
            tier="Standard",
        )

    assert result_plan.research_status == ResearchStatus.NO_EVIDENCE
    assert "no usable evidence" in result_plan.research_status_reason.lower()


# ── Test D: Degraded Dictionary Suppression Regression ───────────────────────

@pytest.mark.asyncio
async def test_degraded_research_context_does_not_suppress_specialist_search():
    """D: A truthy degraded/no-evidence research_context object must NOT suppress specialist direct searches."""
    degraded_context = {"status": "degraded", "error": "Search network error"}
    brief = _sample_brief(research_context=degraded_context)

    # 1. Verify brief.has_usable_research() returns False despite non-empty dictionary
    assert brief.has_usable_research() is False

    # 2. Verify panel specialists invoke their direct parallel search methods when research is degraded
    with (
        patch("src.modules.planning.agents.panel._parallel_research", new=AsyncMock(return_value="DIRECT SEARCH RESULTS")) as mock_direct_research,
        patch("src.modules.planning.agents.panel.ask_json", new=AsyncMock(return_value={"goals": []})),
    ):
        await audience_research(brief)
        mock_direct_research.assert_awaited_once()

    with (
        patch("src.modules.planning.agents.panel._parallel_competitor_research", new=AsyncMock(return_value="COMPETITOR SEARCH RESULTS")) as mock_comp_research,
        patch("src.modules.planning.agents.panel.ask_json", new=AsyncMock(return_value={"landscape": []})),
    ):
        await competitive(brief)
        mock_comp_research.assert_awaited_once()

    # 3. Conversely, when usable research IS present, duplicate direct searches ARE skipped
    usable_context = {
        "status": "available",
        "research_brief": {
            "market": {"key_findings": ["Verified market fact"]},
        },
    }
    usable_brief = _sample_brief(research_context=usable_context)
    assert usable_brief.has_usable_research() is True

    with (
        patch("src.modules.planning.agents.panel._parallel_research", new=AsyncMock()) as mock_direct_research,
        patch("src.modules.planning.agents.panel.ask_json", new=AsyncMock(return_value={"goals": []})),
    ):
        await audience_research(usable_brief)
        mock_direct_research.assert_not_awaited()


# ── Test E: Persist and Retrieve Truthfulness ──────────────────────────────────

@pytest.mark.asyncio
async def test_persist_and_retrieve_preserves_degraded_research_status():
    """E: Persist a degraded plan and retrieve it through the API path -> status remains degraded."""
    campaign_id = uuid4()
    user_id = str(uuid4())
    user = AuthenticatedUser(id=user_id, roles=["user"], permissions=[])

    plan = _sample_plan(
        campaign_id,
        research_status=ResearchStatus.DEGRADED,
        research_reason="DDGS connection reset",
    )

    inputs = SimpleNamespace(
        brand=SAMPLE_BRAND,
        intake={"updated_at": "2026-09-17T10:00:00+00:00"},
        campaign=SimpleNamespace(name="Apex", schedule=None, goals=None, platforms=[]),
    )

    app.dependency_overrides[get_authenticated_user] = lambda: user
    client = TestClient(app)

    try:
        with (
            patch("src.api.v1.plans.CampaignContextResolver.resolve", new=AsyncMock(return_value=inputs)),
            patch("src.api.v1.plans.check_plan_freshness", return_value=(False, None)),
            patch("src.modules.planning.services.plan_refinement_service.PlanRefinementService.get_plan", new=AsyncMock(return_value=plan)),
        ):
            response = client.get(f"/api/v1/campaigns/{campaign_id}/plan")

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["research_status"] == "degraded"
        assert payload["data"]["research_status_reason"] == "DDGS connection reset"
    finally:
        app.dependency_overrides.pop(get_authenticated_user, None)


# ── Test F: Legacy Plan Handled Safely ────────────────────────────────────────

def test_legacy_plan_without_research_status_not_falsely_claimed_research_backed():
    """F: Plan without explicit research-status metadata must NOT be falsely classified as available."""
    legacy_document = {
        "plan_id": str(uuid4()),
        "campaign_id": str(uuid4()),
        "version": 1,
        "language": "en",
        "status": "Draft",
        "title": "Legacy Campaign Plan",
        "executive_summary": "Legacy summary without research metadata",
        "source_brief": {},
        # Intentionally no "research_status" key
    }

    plan = CampaignPlan.from_document(legacy_document)
    assert plan.research_status != ResearchStatus.AVAILABLE
    assert plan.research_status == ResearchStatus.NOT_REQUESTED

    # Ensure document representation does not claim research backing
    doc = plan.to_document()
    assert doc["research_status"] != "available"
