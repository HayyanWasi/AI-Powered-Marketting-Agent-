from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from src.models.audience import AudienceProfile
from src.models.brand_context import BrandContext
from src.models.intake import CampaignType, IntakeChecklist
from src.modules.linkedin.generators.post_generator import LinkedInPostGenerator
from src.modules.linkedin.models import LinkedInPost
from src.modules.linkedin.scheduling import ScheduleOptimizer
from src.modules.planning.models.campaign_plan import CalendarSlot, CampaignPlan, ChannelPlan
from src.services.campaign_context_service import compute_intake_fingerprint


def test_inferred_audience_can_complete_intake_without_redundant_question():
    checklist = IntakeChecklist(
        campaign_type=CampaignType.GENERAL_PROMOTION,
        campaign_name="Say Boo to the Flu",
        objective="Educate the community about seasonal flu prevention",
        value_proposition="Clear preventive care guidance and vaccination awareness",
        audience_profile=AudienceProfile(
            summary="Community members who need seasonal preventive-care information",
            industries=("community health",),
            attention_patterns=("lunch", "after work"),
            source="inferred",
            confidence="high",
            evidence=("The campaign explicitly addresses community preventive care",),
        ),
    )
    assert checklist.target_audience is None
    assert checklist.is_complete() is True


def test_evergreen_density_is_bounded_and_explainable():
    plan = ScheduleOptimizer.build(
        campaign_start=date(2026, 9, 14),
        campaign_end=date(2026, 9, 27),
        timezone_name="Asia/Karachi",
        audience=AudienceProfile(
            summary="Local consumer audience",
            attention_patterns=("lunch", "after work"),
            source="inferred",
            confidence="medium",
        ),
        campaign_type="general_promotion",
        now=datetime(2026, 9, 14, tzinfo=UTC),
    )
    assert 3 <= len(plan.slots) <= 5
    assert plan.target_post_count == len(plan.slots)
    assert plan.density_score > 0
    assert plan.density_factors
    assert len({slot.local_date for slot in plan.slots}) == len(plan.slots)
    assert all(slot.scheduled_at_utc.tzinfo is not None for slot in plan.slots)
    assert all("score=" in slot.schedule_reason for slot in plan.slots)


def test_time_bound_campaign_uses_dynamic_density_and_audience_changes_freshness():
    plan = ScheduleOptimizer.build(
        campaign_start=date(2026, 9, 14),
        campaign_end=date(2026, 9, 27),
        timezone_name="UTC",
        campaign_type="webinar",
        event_date="2026-09-27",
        now=datetime(2026, 9, 14, tzinfo=UTC),
    )
    assert 4 <= len(plan.slots) <= 7
    assert "3 posts per week" not in plan.recommended_cadence
    a = compute_intake_fingerprint({"target_audience": "Founders"})
    b = compute_intake_fingerprint(
        {
            "target_audience": "Founders",
            "audience_profile": {"summary": "Founders", "confidence": "high"},
        }
    )
    assert a != b


def test_objective_and_deadline_proximity_change_density():
    common = {
        "campaign_start": date(2026, 9, 14),
        "campaign_end": date(2026, 10, 13),
        "timezone_name": "UTC",
        "campaign_type": "app_launch",
        "now": datetime(2026, 9, 14, tzinfo=UTC),
    }
    awareness = ScheduleOptimizer.build(
        **common,
        objective="Build thought leadership and expert authority",
        event_date="2026-11-13",
    )
    conversion = ScheduleOptimizer.build(
        **common,
        objective="Acquire app downloads and registrations",
        event_date="2026-09-15",
    )
    far_launch = ScheduleOptimizer.build(
        **common,
        objective="Acquire app downloads and registrations",
        event_date="2026-11-13",
    )
    assert len(conversion.slots) > len(awareness.slots)
    assert len(conversion.slots) > len(far_launch.slots)
    assert conversion.density_score > far_launch.density_score


def test_density_guardrails_prevent_zero_and_runaway_counts():
    one_day = ScheduleOptimizer.build(
        campaign_start=date(2026, 9, 20),
        campaign_end=date(2026, 9, 20),
        timezone_name="UTC",
        objective="Build community awareness",
        now=datetime(2026, 9, 20, tzinfo=UTC),
    )
    long_urgent = ScheduleOptimizer.build(
        campaign_start=date(2026, 9, 14),
        campaign_end=date(2027, 3, 14),
        timezone_name="UTC",
        campaign_type="physical_event",
        objective="Acquire registrations",
        event_date="2026-09-15",
        now=datetime(2026, 9, 14, tzinfo=UTC),
    )
    assert len(one_day.slots) == 1
    assert len(long_urgent.slots) <= 24


def test_candidate_scoring_can_select_weekend_and_favors_b2b_weekdays():
    common = {
        "campaign_start": date(2026, 9, 14),
        "campaign_end": date(2026, 9, 27),
        "timezone_name": "UTC",
        "objective": "Build awareness",
        "now": datetime(2026, 9, 14, tzinfo=UTC),
    }
    consumer = ScheduleOptimizer.build(
        **common,
        audience=AudienceProfile(
            summary="Mobile consumer community",
            attention_patterns=("after work",),
            confidence="high",
        ),
    )
    executive = ScheduleOptimizer.build(
        **common,
        audience=AudienceProfile(
            summary="B2B executive founders and decision-makers",
            confidence="high",
        ),
    )
    assert any(slot.local_date.weekday() >= 5 for slot in consumer.slots)
    assert all(slot.local_date.weekday() < 5 for slot in executive.slots)


def test_time_selection_is_stable_when_campaign_start_moves():
    audience = AudienceProfile(
        summary="B2B executive founders",
        schedule_patterns=("before work", "evening"),
        confidence="high",
    )
    first = ScheduleOptimizer.build(
        campaign_start=date(2026, 9, 14),
        campaign_end=date(2026, 9, 27),
        timezone_name="UTC",
        audience=audience,
        now=datetime(2026, 9, 14, tzinfo=UTC),
    )
    second = ScheduleOptimizer.build(
        campaign_start=date(2026, 9, 15),
        campaign_end=date(2026, 9, 27),
        timezone_name="UTC",
        audience=audience,
        now=datetime(2026, 9, 14, tzinfo=UTC),
    )
    first_tuesday = next(slot for slot in first.slots if slot.local_date == date(2026, 9, 15))
    second_tuesday = next(slot for slot in second.slots if slot.local_date == date(2026, 9, 15))
    assert first_tuesday.local_time == second_tuesday.local_time


def test_same_inputs_produce_same_times_and_explanations():
    kwargs = {
        "campaign_start": date(2026, 9, 14),
        "campaign_end": date(2026, 9, 27),
        "timezone_name": "UTC",
        "audience": AudienceProfile(
            summary="Hospital shift workers",
            schedule_patterns=("shift handover",),
            confidence="high",
        ),
        "objective": "Educate staff",
        "now": datetime(2026, 9, 14, tzinfo=UTC),
    }
    first = ScheduleOptimizer.build(**kwargs)
    second = ScheduleOptimizer.build(**kwargs)
    assert [(s.local_date, s.local_time) for s in first.slots] == [
        (s.local_date, s.local_time) for s in second.slots
    ]
    assert [s.schedule_reason for s in first.slots] == [s.schedule_reason for s in second.slots]


@pytest.mark.asyncio
async def test_post_generation_count_and_times_come_only_from_schedule(monkeypatch):
    schedule = ScheduleOptimizer.build(
        campaign_start=date(2026, 9, 14),
        campaign_end=date(2026, 9, 20),
        timezone_name="Asia/Karachi",
        campaign_type="general_promotion",
        now=datetime(2026, 9, 14, tzinfo=UTC),
    )
    calendar = tuple(
        CalendarSlot(slot_id=str(slot.slot_id), platform="LinkedIn", theme=f"Theme {index}")
        for index, slot in enumerate(schedule.slots)
    )
    # Specialist ordering is presentation-only; generation restores schedule chronology.
    plan = CampaignPlan(
        schedule_plan=schedule,
        channel_plan=ChannelPlan(calendar_slots=tuple(reversed(calendar))),
    )
    campaign_id = uuid4()

    monkeypatch.setattr(
        "src.modules.linkedin.generators.post_generator.ContentContextBuilder.build_context",
        lambda *args, **kwargs: object(),
    )

    async def fake_generate(self, campaign_id, ctx, scheduled_at=None):
        return LinkedInPost(
            campaign_id=campaign_id,
            slot_id="temporary",
            scheduled_at=scheduled_at,
            hook="Hook",
            body="Body",
            cta_text="CTA",
            full_content="Hook\nBody\nCTA",
        )

    monkeypatch.setattr(LinkedInPostGenerator, "_generate_single_post", fake_generate)
    posts = await LinkedInPostGenerator().generate_all_posts(
        campaign_id,
        plan,
        brand=BrandContext(company_profile_id=uuid4(), company_name="Sentinel"),
    )
    assert len(posts) == len(schedule.slots)
    assert [post.scheduled_at for post in posts] == [
        slot.scheduled_at_utc for slot in schedule.slots
    ]
    assert [post.timezone for post in posts] == [slot.timezone for slot in schedule.slots]
