"""draft_plan must never save a partial CampaignPlan.

Root cause (read-only audit, prior turn): a specialist that fails upstream
degrades to an empty section rather than crashing the graph. When that
specialist was channel_plan, the empty calendar reached
``normalize_calendar_slots`` and raised a generic "Added, removed, or
unknown schedule slot" mismatch, which draft_plan then mislabeled as
"Channel planner changed the fixed schedule slots" — conflating a missing
section with an actual identity mutation.

These tests pin the corrected contract: a recorded specialist failure (any
of the 5) fails the whole draft truthfully, before persistence; a genuine
non-empty-but-mutated calendar still raises the original strict message;
and a real success still persists exactly once.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.modules.planning.models.brief import PlanBrief
from src.modules.planning.models.campaign_plan import (
    CalendarSlot,
    CampaignPlan,
    ChannelPlan,
    Competitive,
    CoreStrategy,
    Measurement,
    PlanStatus,
)
from src.modules.planning.services.plan_refinement_service import (
    PlanDraftError,
    PlanRefinementService,
)


def _brief() -> PlanBrief:
    return PlanBrief(user_goal="Launch a product", company_name="TestCo")


def _plan(campaign_id: UUID, calendar_slots: tuple[CalendarSlot, ...] = ()) -> CampaignPlan:
    return CampaignPlan(
        campaign_id=campaign_id,
        version=1,
        title="Test Plan",
        status=PlanStatus.DRAFT,
        core_strategy=CoreStrategy(
            positioning_statement="x", unique_selling_proposition="y"
        ),
        channel_plan=ChannelPlan(calendar_slots=calendar_slots),
        measurement=Measurement(),
        competitive=Competitive(),
    )


def _service(mock_graph) -> tuple[PlanRefinementService, MagicMock]:
    mock_repo = MagicMock()
    mock_repo.get_or_create_plan_row = AsyncMock(return_value={"id": str(uuid4())})
    mock_repo.get_latest_version = AsyncMock(return_value=None)
    mock_repo.add_version = AsyncMock()
    service = PlanRefinementService(repository=mock_repo)
    return service, mock_repo


@pytest.mark.asyncio
async def test_a_channel_plan_succeeds_with_canonical_slots_planning_succeeds():
    campaign_id = uuid4()
    plan = _plan(campaign_id, calendar_slots=(CalendarSlot(slot_id=str(uuid4())),))
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={"plan": plan, "failures": []})
    service, mock_repo = _service(mock_graph)

    with (
        patch(
            "src.modules.planning.services.plan_refinement_service.plan_graph.compile_graph",
            return_value=mock_graph,
        ),
        patch(
            "src.modules.planning.services.plan_refinement_service.normalize_calendar_slots",
            side_effect=lambda slots, sp: slots,
        ),
    ):
        result = await service.draft_plan(
            campaign_id=campaign_id, created_by=uuid4(), brief=_brief()
        )

    assert isinstance(result, CampaignPlan)
    mock_repo.add_version.assert_awaited_once()


@pytest.mark.asyncio
async def test_b_channel_plan_specialist_failure_is_classified_truthfully_not_as_mutation():
    campaign_id = uuid4()
    plan = _plan(campaign_id, calendar_slots=())  # graph degraded the failed specialist to empty
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(
        return_value={"plan": plan, "failures": ["channel_plan: simulated 429 rate limit"]}
    )
    service, mock_repo = _service(mock_graph)

    with patch(
        "src.modules.planning.services.plan_refinement_service.plan_graph.compile_graph",
        return_value=mock_graph,
    ), pytest.raises(PlanDraftError) as excinfo:
        await service.draft_plan(campaign_id=campaign_id, created_by=uuid4(), brief=_brief())

    assert str(excinfo.value) == "Channel planning failed. Please retry planning."
    assert "changed the fixed schedule slots" not in str(excinfo.value)
    mock_repo.add_version.assert_not_awaited()


@pytest.mark.asyncio
async def test_c_non_empty_mutated_calendar_still_reports_fixed_slot_mutation():
    campaign_id = uuid4()
    # Non-empty calendar, but slot_id can't match the real canonical schedule
    # draft_plan builds internally -> real normalize_calendar_slots rejects it.
    plan = _plan(campaign_id, calendar_slots=(CalendarSlot(slot_id="not-a-real-canonical-id"),))
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={"plan": plan, "failures": []})
    service, mock_repo = _service(mock_graph)

    with patch(
        "src.modules.planning.services.plan_refinement_service.plan_graph.compile_graph",
        return_value=mock_graph,
    ), pytest.raises(PlanDraftError) as excinfo:
        await service.draft_plan(campaign_id=campaign_id, created_by=uuid4(), brief=_brief())

    assert str(excinfo.value) == "Channel planner changed the fixed schedule slots. Please retry planning."
    mock_repo.add_version.assert_not_awaited()


@pytest.mark.asyncio
async def test_d_other_specialist_failure_fails_the_whole_draft_truthfully():
    campaign_id = uuid4()
    plan = _plan(campaign_id, calendar_slots=(CalendarSlot(slot_id=str(uuid4())),))
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(
        return_value={"plan": plan, "failures": ["audience_research: simulated 429 rate limit"]}
    )
    service, mock_repo = _service(mock_graph)

    with patch(
        "src.modules.planning.services.plan_refinement_service.plan_graph.compile_graph",
        return_value=mock_graph,
    ), pytest.raises(PlanDraftError) as excinfo:
        await service.draft_plan(campaign_id=campaign_id, created_by=uuid4(), brief=_brief())

    message = str(excinfo.value)
    assert "audience_research" in message
    assert "changed the fixed schedule slots" not in message
    assert "Channel planning failed" not in message
    mock_repo.add_version.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failures,calendar_slots",
    [
        (["channel_plan: simulated 429 rate limit"], ()),
        ([], (CalendarSlot(slot_id="not-a-real-canonical-id"),)),
        (["measurement: simulated 429 rate limit"], (CalendarSlot(slot_id="x"),)),
    ],
    ids=["channel-specialist-failure", "genuine-mutation", "other-specialist-failure"],
)
async def test_e_no_partial_plan_is_ever_persisted_on_any_failure_path(failures, calendar_slots):
    campaign_id = uuid4()
    plan = _plan(campaign_id, calendar_slots=calendar_slots)
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={"plan": plan, "failures": failures})
    service, mock_repo = _service(mock_graph)

    with patch(
        "src.modules.planning.services.plan_refinement_service.plan_graph.compile_graph",
        return_value=mock_graph,
    ), pytest.raises(PlanDraftError):
        await service.draft_plan(campaign_id=campaign_id, created_by=uuid4(), brief=_brief())

    mock_repo.add_version.assert_not_awaited()
    mock_repo.get_or_create_plan_row.assert_awaited()  # row lookup is fine; version is not
