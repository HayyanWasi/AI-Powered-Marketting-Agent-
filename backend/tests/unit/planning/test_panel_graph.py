"""Panel graph fan-out — five specialists merge into one validated plan."""

from unittest.mock import patch

import pytest

from src.modules.planning.models.brief import PlanBrief
from src.modules.planning.models.campaign_plan import CampaignPlan
from src.modules.workflow_engine.graphs import campaign_plan as graph_mod

_BRIEF = PlanBrief(
    user_goal="mujhe aik ai hackathon k liye campaigns generate krwani hai",
    company_name="Test Corp",
    event_name="AI Hackathon",
    event_date="2026-09-20",
    platforms=("linkedin", "instagram"),
)

_PANEL_RESPONSES = {
    "plan_audience_research": {
        "objective": "Drive 500 hackathon registrations",
        "smart_goals": [{"goal": "500 signups", "metric": "registrations", "target": "500"}],
        "personas": [{"name": "Final-year CS student", "motivations": ["portfolio"]}],
    },
    "plan_positioning": {
        "positioning_statement": "For student builders, this is the hackathon that ships.",
        "unique_selling_proposition": "Build with the people building the future.",
        "messaging_pillars": ["Build", "Learn", "Win"],
        "tone_of_voice": "Energetic and concrete.",
        "objection_handling": [{"objection": "No time", "response": "One weekend."}],
    },
    "plan_channel": {
        "platforms": [{"platform": "linkedin", "posting_cadence": "3x per week"}],
        "phases": [{"phase": "teaser", "primary_cta": "Follow for updates"}],
        "calendar_slots": [{"date": "2026-09-01", "platform": "linkedin", "phase": "teaser"}],
        "overall_cadence": "Ramp from 2x to daily.",
    },
    "plan_measurement": {
        "kpis": [{"name": "Registrations", "funnel_stage": "conversion", "target": "500"}],
        "definition_of_success": "500 registrations by launch day.",
    },
    "plan_competitive": {
        "landscape": [{"name": "Other Hackathon", "positioning": "Corporate"}],
        "differentiation_angle": "Student-first, ship-first.",
    },
}


def _fake_ask(*, fail: set[str] = frozenset()):
    """Stand in for the LLM: return the canned section for each template."""

    async def _ask(template_name, variables, **kw):
        if template_name in fail:
            raise RuntimeError(f"{template_name} unavailable")
        if template_name == "plan_chief_strategist":
            return {
                "title": "AI Hackathon 2026",
                "executive_summary": "A student-first hackathon campaign.",
                "core_strategy": {
                    **_PANEL_RESPONSES["plan_audience_research"],
                    **_PANEL_RESPONSES["plan_positioning"],
                },
                "channel_plan": _PANEL_RESPONSES["plan_channel"],
                "measurement": _PANEL_RESPONSES["plan_measurement"],
                "competitive": _PANEL_RESPONSES["plan_competitive"],
            }
        # Map template names to response dictionary
        key = template_name
        if key not in _PANEL_RESPONSES and f"plan_{key}" in _PANEL_RESPONSES:
            key = f"plan_{key}"
        return _PANEL_RESPONSES[key]

    return _ask


@pytest.fixture(autouse=True)
def _no_network():
    """Specialists must not hit DuckDuckGo in tests."""
    with patch(
        "src.services.search.GuestSearchService.search", return_value=[]
    ):
        yield


async def _run(fail: set[str] = frozenset()) -> CampaignPlan:
    with patch("src.modules.planning.agents.panel.ask_json", new=_fake_ask(fail=fail)), patch(
        "src.modules.planning.agents.chief_strategist.ask_json", new=_fake_ask(fail=fail)
    ):
        state = await graph_mod.compile_graph().ainvoke(graph_mod.initial_state(_BRIEF))
    return state["plan"]


class TestPanelGraph:
    @pytest.mark.asyncio
    async def test_all_five_sections_populated(self):
        plan = await _run()

        assert isinstance(plan, CampaignPlan)
        assert plan.core_strategy.unique_selling_proposition != ""
        assert plan.core_strategy.objective != ""
        assert len(plan.core_strategy.messaging_pillars) == 3
        assert len(plan.channel_plan.calendar_slots) == 1
        assert len(plan.measurement.kpis) == 1
        assert plan.competitive.differentiation_angle != ""

    @pytest.mark.asyncio
    async def test_every_specialist_contributes(self):
        """The reducer must merge all five concurrent writes, not clobber."""
        with patch("src.modules.planning.agents.panel.ask_json", new=_fake_ask()), patch(
            "src.modules.planning.agents.chief_strategist.ask_json", new=_fake_ask()
        ):
            state = await graph_mod.compile_graph().ainvoke(graph_mod.initial_state(_BRIEF))

        assert len(state["sections"]) == 5
        assert {s["name"] for s in state["sections"]} == {
            "audience_research",
            "positioning",
            "channel_plan",
            "measurement",
            "competitive",
        }

    @pytest.mark.asyncio
    async def test_one_failing_specialist_does_not_sink_the_plan(self):
        plan = await _run(fail={"plan_competitive"})

        assert isinstance(plan, CampaignPlan)
        assert plan.core_strategy.unique_selling_proposition != ""

    @pytest.mark.asyncio
    async def test_failed_synthesis_falls_back_to_direct_assembly(self):
        plan = await _run(fail={"plan_chief_strategist"})

        # Assembly merges audience_research + positioning into core_strategy.
        assert plan.core_strategy.objective != ""
        assert plan.core_strategy.unique_selling_proposition != ""
        assert len(plan.measurement.kpis) == 1

    @pytest.mark.asyncio
    async def test_plan_round_trips_through_jsonb(self):
        plan = await _run()

        restored = CampaignPlan.from_document(plan.to_document())
        assert restored.to_document() == plan.to_document()
