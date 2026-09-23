"""Channel planner must annotate fixed schedule slots, never mutate their identity.

The planner LLM references slots by numbered position (unreliable-to-mutate
small integers) instead of copying a 36-character slot_id verbatim. These
tests cover the index-to-slot_id resolution in panel.py and the chief
strategist's hard backstop that keeps calendar identity flowing from the
channel specialist regardless of what the synthesis model re-emits.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from unittest.mock import patch

import pytest

from src.modules.linkedin.scheduling.models import SchedulePlan, ScheduleSlot
from src.modules.linkedin.scheduling.slot_validation import (
    ScheduleSlotMismatchError,
    normalize_calendar_slots,
)
from src.modules.planning.agents import chief_strategist
from src.modules.planning.agents.panel import _resolve_calendar_slot_ids, channel_planner
from src.modules.planning.models.brief import PlanBrief


def _schedule(n: int = 3) -> SchedulePlan:
    slots = tuple(
        ScheduleSlot(
            scheduled_at_utc=datetime(2026, 9, 21 + i, 7, tzinfo=UTC),
            local_date=date(2026, 9, 21 + i),
            local_time=time(12),
            timezone="Asia/Karachi",
            schedule_reason=f"slot {i}",
        )
        for i in range(n)
    )
    return SchedulePlan(
        campaign_start=date(2026, 9, 21),
        campaign_end=date(2026, 9, 21 + n),
        primary_timezone="Asia/Karachi",
        recommended_cadence=f"{n} posts",
        cadence_reason="test",
        slots=slots,
    )


def _brief(schedule: SchedulePlan) -> PlanBrief:
    return PlanBrief(user_goal="Launch a product", schedule_plan=schedule)


class TestSlotIdResolution:
    def test_numbered_references_resolve_to_real_slot_ids(self):
        schedule = _schedule(3)
        brief = _brief(schedule)
        payload = {
            "calendar_slots": [
                {"slot_id": "1", "theme": "teaser"},
                {"slot_id": "2", "theme": "launch"},
                {"slot_id": "3", "theme": "sustain"},
            ]
        }

        resolved = _resolve_calendar_slot_ids(payload, brief)

        assert [c["slot_id"] for c in resolved["calendar_slots"]] == [
            str(s.slot_id) for s in schedule.slots
        ]

    def test_already_correct_uuid_is_left_untouched(self):
        schedule = _schedule(2)
        brief = _brief(schedule)
        real_id = str(schedule.slots[0].slot_id)
        payload = {"calendar_slots": [{"slot_id": real_id, "theme": "x"}]}

        resolved = _resolve_calendar_slot_ids(payload, brief)

        assert resolved["calendar_slots"][0]["slot_id"] == real_id

    def test_out_of_range_index_is_left_untouched_and_still_rejected(self):
        schedule = _schedule(2)
        brief = _brief(schedule)
        payload = {"calendar_slots": [{"slot_id": "99", "theme": "x"}]}

        resolved = _resolve_calendar_slot_ids(payload, brief)

        assert resolved["calendar_slots"][0]["slot_id"] == "99"

    def test_annotations_flow_through_unchanged(self):
        schedule = _schedule(1)
        brief = _brief(schedule)
        payload = {
            "calendar_slots": [
                {
                    "slot_id": "1",
                    "phase": "launch",
                    "theme": "custom theme",
                    "format_type": "carousel",
                    "messaging_pillar": "trust",
                    "cta": "Register now",
                }
            ]
        }

        resolved = _resolve_calendar_slot_ids(payload, brief)
        entry = resolved["calendar_slots"][0]

        assert entry["phase"] == "launch"
        assert entry["theme"] == "custom theme"
        assert entry["format_type"] == "carousel"
        assert entry["messaging_pillar"] == "trust"
        assert entry["cta"] == "Register now"


class TestChannelPlannerEndToEnd:
    @pytest.mark.asyncio
    async def test_channel_planner_output_passes_strict_validation(self):
        """A numbered LLM response survives the untouched, strict validator."""
        schedule = _schedule(4)
        brief = _brief(schedule)

        async def fake_ask(template_name, variables, **kw):
            return {
                "platforms": [],
                "phases": [],
                "calendar_slots": [
                    {"slot_id": str(i + 1), "theme": f"post {i + 1}"}
                    for i in range(4)
                ],
                "overall_cadence": "steady",
            }

        with patch("src.modules.planning.agents.panel.ask_json", new=fake_ask):
            payload = await channel_planner(brief)

        from src.modules.planning.models.campaign_plan import CalendarSlot

        calendar_slots = tuple(CalendarSlot(**c) for c in payload["calendar_slots"])
        normalized = normalize_calendar_slots(calendar_slots, schedule)

        assert len(normalized) == 4
        assert [s.slot_id for s in normalized] == [str(s.slot_id) for s in schedule.slots]
        for original, out in zip(schedule.slots, normalized, strict=True):
            assert out.scheduled_at_utc == original.scheduled_at_utc
            assert out.timezone == original.timezone

    @pytest.mark.asyncio
    async def test_deliberate_timestamp_mutation_still_rejected(self):
        """The validator itself was not weakened — real mutations still fail."""
        schedule = _schedule(2)
        from src.modules.planning.models.campaign_plan import CalendarSlot

        calendar_slots = (
            CalendarSlot(
                slot_id=str(schedule.slots[0].slot_id),
                scheduled_at_utc=datetime(2099, 1, 1, tzinfo=UTC),
            ),
            CalendarSlot(slot_id=str(schedule.slots[1].slot_id)),
        )

        with pytest.raises(ScheduleSlotMismatchError):
            normalize_calendar_slots(calendar_slots, schedule)


class TestChiefStrategistCalendarBackstop:
    @pytest.mark.asyncio
    async def test_synthesis_cannot_alter_calendar_identity(self):
        """Even if the synthesis model rewrites calendar_slots, the specialist's
        own (already-resolved) slots win."""
        schedule = _schedule(2)
        brief = _brief(schedule)
        real_ids = [str(s.slot_id) for s in schedule.slots]

        panel = {
            "audience_research": {"objective": "grow", "smart_goals": [], "personas": []},
            "positioning": {
                "positioning_statement": "x",
                "unique_selling_proposition": "y",
                "messaging_pillars": [],
                "tone_of_voice": "z",
                "objection_handling": [],
            },
            "channel_plan": {
                "platforms": [],
                "phases": [],
                "calendar_slots": [
                    {"slot_id": real_ids[0], "theme": "a"},
                    {"slot_id": real_ids[1], "theme": "b"},
                ],
                "overall_cadence": "steady",
            },
            "measurement": {"kpis": [], "definition_of_success": ""},
            "competitive": {"landscape": [], "differentiation_angle": ""},
        }

        async def corrupting_ask(template_name, variables, **kw):
            return {
                "title": "t",
                "executive_summary": "e",
                "core_strategy": {**panel["audience_research"], **panel["positioning"]},
                "channel_plan": {
                    "platforms": [],
                    "phases": [],
                    # Synthesis model garbles one slot_id and drops the other.
                    "calendar_slots": [{"slot_id": "not-a-real-id", "theme": "a"}],
                    "overall_cadence": "steady",
                },
                "measurement": panel["measurement"],
                "competitive": panel["competitive"],
            }

        with patch("src.modules.planning.agents.chief_strategist.ask_json", new=corrupting_ask):
            plan = await chief_strategist.synthesize(brief, panel)

        assert [s.slot_id for s in plan.channel_plan.calendar_slots] == real_ids
        normalized = normalize_calendar_slots(plan.channel_plan.calendar_slots, schedule)
        assert len(normalized) == 2


class TestIntegerSlotIdCoercion:
    """Small/local models emit ordinal slot_id as a JSON integer, not a string.

    Both validation gates (the provider's output_schema check and ask_json's
    explicit model_validate) run ChannelPlan.model_validate on the raw payload
    BEFORE _resolve_calendar_slot_ids maps the ordinal to a UUID. Without
    coercion the integer is rejected as a non-string, the specialist fails,
    and /plan/draft returns 502. This mirrors the observed runtime payload.
    """

    def test_channel_plan_accepts_integer_ordinal_slot_ids(self):
        from src.modules.planning.models.campaign_plan import ChannelPlan

        payload = {
            "calendar_slots": [
                {"slot_id": o, "theme": f"post {o}"} for o in (1, 3, 6, 2, 8)
            ],
        }

        plan = ChannelPlan.model_validate(payload)

        assert [s.slot_id for s in plan.calendar_slots] == ["1", "3", "6", "2", "8"]

    def test_missing_or_null_slot_id_gets_a_generated_id_not_a_type_error(self):
        from src.modules.planning.models.campaign_plan import CalendarSlot

        # A null slot_id must not raise a type error; it becomes a fresh id
        # that legitimately fails strict identity validation downstream.
        assert CalendarSlot.model_validate({"slot_id": None}).slot_id
        assert CalendarSlot.model_validate({"slot_id": ""}).slot_id

    def test_integer_ordinals_resolve_to_canonical_ids_then_validate(self):
        from src.modules.planning.models.campaign_plan import CalendarSlot

        schedule = _schedule(8)
        brief = _brief(schedule)
        # Raw payload exactly as the model emitted it at runtime: bare ints.
        payload = {
            "calendar_slots": [{"slot_id": o, "theme": "x"} for o in (1, 3, 6, 2, 8)]
        }

        resolved = _resolve_calendar_slot_ids(payload, brief)
        slots = tuple(CalendarSlot(**c) for c in resolved["calendar_slots"])

        expected = [str(schedule.slots[i - 1].slot_id) for i in (1, 3, 6, 2, 8)]
        assert [s.slot_id for s in slots] == expected


class TestChannelPlannerRepair:
    @pytest.mark.asyncio
    async def test_valid_exact_n_slot_channel_output(self):
        schedule = _schedule(3)
        brief = _brief(schedule)
        
        async def fake_ask(template_name, variables, **kw):
            assert template_name == "plan_channel"
            return {
                "calendar_slots": [{"slot_id": "1"}, {"slot_id": "2"}, {"slot_id": "3"}],
                "platforms": [], "phases": [], "overall_cadence": ""
            }
            
        with patch("src.modules.planning.agents.panel.ask_json", new=fake_ask):
            payload = await channel_planner(brief)
            
        assert len(payload["calendar_slots"]) == 3

    @pytest.mark.asyncio
    async def test_missing_one_slot_triggers_repair(self):
        schedule = _schedule(3)
        brief = _brief(schedule)
        
        call_count = 0
        async def fake_ask(template_name, variables, **kw):
            nonlocal call_count
            call_count += 1
            if template_name == "plan_channel":
                return {
                    "calendar_slots": [{"slot_id": "1"}, {"slot_id": "2"}],
                }
            if template_name == "plan_channel_repair":
                assert "exactly 3 are required" in variables["validation_error"]
                return {
                    "calendar_slots": [{"slot_id": "1"}, {"slot_id": "2"}, {"slot_id": "3"}],
                }
            raise ValueError("Unexpected template")
            
        with patch("src.modules.planning.agents.panel.ask_json", new=fake_ask):
            payload = await channel_planner(brief)
            
        assert call_count == 2
        assert len(payload["calendar_slots"]) == 3

    @pytest.mark.asyncio
    async def test_extra_slot_triggers_repair(self):
        schedule = _schedule(2)
        brief = _brief(schedule)
        
        async def fake_ask(template_name, variables, **kw):
            if template_name == "plan_channel":
                return {"calendar_slots": [{"slot_id": "1"}, {"slot_id": "2"}, {"slot_id": "3"}]}
            if template_name == "plan_channel_repair":
                assert "returned extra schedule slots" in variables["validation_error"]
                return {"calendar_slots": [{"slot_id": "1"}, {"slot_id": "2"}]}
            
        with patch("src.modules.planning.agents.panel.ask_json", new=fake_ask):
            payload = await channel_planner(brief)
            
        assert len(payload["calendar_slots"]) == 2

    @pytest.mark.asyncio
    async def test_duplicate_ordinal_triggers_repair(self):
        schedule = _schedule(2)
        brief = _brief(schedule)
        
        async def fake_ask(template_name, variables, **kw):
            if template_name == "plan_channel":
                return {"calendar_slots": [{"slot_id": "1"}, {"slot_id": "1"}]}
            if template_name == "plan_channel_repair":
                assert "Ordinal 1 was duplicated" in variables["validation_error"]
                return {"calendar_slots": [{"slot_id": "1"}, {"slot_id": "2"}]}
            
        with patch("src.modules.planning.agents.panel.ask_json", new=fake_ask):
            await channel_planner(brief)

    @pytest.mark.asyncio
    async def test_unknown_raw_hallucinated_slot_triggers_repair(self):
        schedule = _schedule(2)
        brief = _brief(schedule)
        
        async def fake_ask(template_name, variables, **kw):
            if template_name == "plan_channel":
                return {"calendar_slots": [{"slot_id": "1"}, {"slot_id": "abc"}]}
            if template_name == "plan_channel_repair":
                assert "unknown or invalid slot ordinals" in variables["validation_error"]
                return {"calendar_slots": [{"slot_id": "1"}, {"slot_id": "2"}]}
            
        with patch("src.modules.planning.agents.panel.ask_json", new=fake_ask):
            await channel_planner(brief)

    @pytest.mark.asyncio
    async def test_immutable_mutation_triggers_repair(self):
        schedule = _schedule(1)
        brief = _brief(schedule)
        
        async def fake_ask(template_name, variables, **kw):
            if template_name == "plan_channel":
                return {"calendar_slots": [{"slot_id": "1", "platform": "Instagram"}]}
            if template_name == "plan_channel_repair":
                assert "changed an immutable field" in variables["validation_error"]
                return {"calendar_slots": [{"slot_id": "1", "platform": "LinkedIn"}]}
            
        with patch("src.modules.planning.agents.panel.ask_json", new=fake_ask):
            await channel_planner(brief)

    @pytest.mark.asyncio
    async def test_repair_still_invalid_fails_specialist(self):
        schedule = _schedule(1)
        brief = _brief(schedule)
        
        async def fake_ask(template_name, variables, **kw):
            return {"calendar_slots": []}
            
        with patch("src.modules.planning.agents.panel.ask_json", new=fake_ask):
            with pytest.raises(ValueError, match="failed validation after repair"):
                await channel_planner(brief)
