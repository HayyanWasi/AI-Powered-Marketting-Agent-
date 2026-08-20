"""Refinement turn — targeted sections change, everything else is preserved."""

from unittest.mock import patch

import pytest

from src.modules.planning.models.brief import PlanBrief
from src.modules.planning.models.campaign_plan import CampaignPlan, PlanStatus
from src.modules.workflow_engine.graphs import plan_refinement as graph_mod

_BRIEF = PlanBrief(
    user_goal="AI hackathon campaign",
    company_name="Test Corp",
    event_name="AI Hackathon",
    platforms=("linkedin",),
)

_PLAN = CampaignPlan.model_validate(
    {
        "title": "AI Hackathon 2026",
        "core_strategy": {
            "objective": "Drive 500 registrations",
            "unique_selling_proposition": "Build with the people building the future.",
            "messaging_pillars": ["Build", "Learn", "Win"],
            "tone_of_voice": "Energetic.",
        },
        "channel_plan": {
            "platforms": [{"platform": "linkedin", "posting_cadence": "3x per week"}],
            "phases": [{"phase": "teaser", "primary_cta": "Follow for updates"}],
            "calendar_slots": [
                {"date": "2026-09-01", "platform": "linkedin", "phase": "teaser"}
            ],
            "overall_cadence": "Ramp from 2x to daily.",
        },
        "measurement": {
            "kpis": [{"name": "Registrations", "funnel_stage": "conversion", "target": "500"}],
            "definition_of_success": "500 registrations.",
        },
        "competitive": {"differentiation_angle": "Student-first."},
    }
)


def _fake_ask(*, targets, revised=None, language="en", is_approval=False, fail=frozenset()):
    """Stand in for the LLM across routing, revision and reply."""

    async def _ask(template_name, variables, **kw):
        if template_name in fail:
            raise RuntimeError(f"{template_name} unavailable")
        if template_name == "plan_route_critique":
            return {
                "target_sections": list(targets),
                "instructions": dict.fromkeys(targets, "change it"),
                "language": language,
                "is_approval": is_approval,
            }
        if template_name == "plan_revise_section":
            return {variables["section_name"]: revised or {}}
        if template_name == "plan_compose_reply":
            return {"reply": f"[{variables['language']}] Updated {variables['sections_changed']}."}
        raise AssertionError(f"Unexpected template {template_name}")

    return _ask


async def _run(**kwargs):
    critique = kwargs.pop("critique", "change something")
    with patch("src.modules.planning.agents.reviser.ask_json", new=_fake_ask(**kwargs)):
        return await graph_mod.compile_graph().ainvoke(
            graph_mod.initial_state(_PLAN, _BRIEF, critique)
        )


class TestRefinementIsolation:
    @pytest.mark.asyncio
    async def test_untargeted_sections_are_byte_identical(self):
        state = await _run(
            targets=["channel_plan"],
            revised={
                "platforms": [{"platform": "linkedin", "posting_cadence": "daily"}],
                "phases": [{"phase": "launch", "primary_cta": "Register now"}],
                "calendar_slots": [
                    {"date": "2026-09-05", "platform": "linkedin", "phase": "launch"}
                ],
                "overall_cadence": "Daily throughout.",
            },
        )
        revised = state["revised_plan"]

        assert state["sections_changed"] == ("channel_plan",)
        assert revised.channel_plan.overall_cadence == "Daily throughout."
        # The other three sections must be untouched.
        for section in ("core_strategy", "measurement", "competitive"):
            assert getattr(revised, section).model_dump(mode="json") == getattr(
                _PLAN, section
            ).model_dump(mode="json")

    @pytest.mark.asyncio
    async def test_version_bumps_and_approval_resets(self):
        state = await _run(
            targets=["measurement"],
            revised={"kpis": [{"name": "Signups", "target": "700"}], "definition_of_success": "700."},
        )
        revised = state["revised_plan"]

        assert revised.version == _PLAN.version + 1
        assert revised.status is PlanStatus.REFINING
        assert revised.approved is False

    @pytest.mark.asyncio
    async def test_no_targets_leaves_plan_untouched(self):
        state = await _run(targets=[], critique="what does USP mean?")

        assert state["sections_changed"] == ()
        assert state["revised_plan"].to_document() == _PLAN.to_document()
        assert state["reply"] != ""

    @pytest.mark.asyncio
    async def test_unusable_revision_is_discarded(self):
        """An empty revision must not blank out a section."""
        state = await _run(targets=["core_strategy"], revised={})

        assert state["sections_changed"] == ()
        assert state["revised_plan"].core_strategy.model_dump(
            mode="json"
        ) == _PLAN.core_strategy.model_dump(mode="json")

    @pytest.mark.asyncio
    async def test_reply_mirrors_the_marketers_language(self):
        state = await _run(
            targets=["competitive"],
            revised={"differentiation_angle": "Sirf students ke liye."},
            language="roman_ur",
        )

        assert state["language"] == "roman_ur"
        assert "roman_ur" in state["reply"]

    @pytest.mark.asyncio
    async def test_approval_intent_is_surfaced(self):
        state = await _run(targets=[], is_approval=True, critique="looks great, approve it")

        assert state["is_approval"] is True

    @pytest.mark.asyncio
    async def test_failed_routing_does_not_corrupt_the_plan(self):
        state = await _run(targets=["core_strategy"], fail={"plan_route_critique"})

        assert state["sections_changed"] == ()
        assert state["revised_plan"].to_document() == _PLAN.to_document()
        assert state["reply"] != ""
