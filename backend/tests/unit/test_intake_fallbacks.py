import uuid
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.dependencies import AuthenticatedUser
from src.api.v1 import intake as intake_api
from src.models.intake import IntakeChatRequest, IntakeChecklist
from src.modules.research.services.llm_router import LLMRouterService
from src.services.intake_chat_service import IntakeChatService, IntakeProcessingError
from src.services.llm_service import LLMService


class RecordingLLM:
    def __init__(self, result: dict[str, Any] | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[Any] = []

    async def generate_json(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append((args, kwargs))
        if self.error:
            raise self.error
        return self.result


def test_intake_initializes_canonical_llm_router() -> None:
    service = IntakeChatService()

    assert isinstance(service.llm, LLMRouterService)
    assert isinstance(service.llm.llm, LLMService)


@pytest.mark.asyncio
async def test_successful_extraction_uses_injected_llm_and_updates_fields(monkeypatch):
async def test_successful_extraction_uses_injected_llm_and_updates_fields(monkeypatch: Any) -> None:
    llm = RecordingLLM(
        {
            "extracted": {
                "campaign_type": "product_launch",
                "campaign_name": "Atlas",
                "objective": "Drive trials",
                "target_audience": "Operations leaders",
                "value_proposition": "Faster planning",
            },
            "reply": "All details collected.",
        }
    )
    service = IntakeChatService(llm=llm)
    service = IntakeChatService(llm=cast(Any, llm))
    owner_id = uuid.uuid4()
    monkeypatch.setattr(service, "_save_message", lambda *args: None)
    monkeypatch.setattr(service, "_save_checklist", lambda *args: None)

    response = await service.process_chat_turn(
        uuid.uuid4(), "Launch Atlas", [], owner_id=owner_id
    )

    assert len(llm.calls) == 1
    assert response["checklist"].campaign_name == "Atlas"
    assert response["checklist"].objective == "Drive trials"
    assert response["checklist"].target_audience == "Operations leaders"
    assert response["checklist"].value_proposition == "Faster planning"
    assert response["is_complete"] is True


@pytest.mark.asyncio
async def test_missing_outcome_remains_none(monkeypatch):
async def test_missing_outcome_remains_none(monkeypatch: Any) -> None:
    llm = RecordingLLM(
        {
            "extracted": {
                "curriculum_breakdown": "Python programming",
                "outcome_deliverable": None,
            },
            "reply": "What is the outcome?",
        }
    )
    service = IntakeChatService(llm=llm)
    service = IntakeChatService(llm=cast(Any, llm))
    owner_id = uuid.uuid4()
    monkeypatch.setattr(service, "_save_message", lambda *args: None)
    monkeypatch.setattr(service, "_save_checklist", lambda *args: None)

    response = await service.process_chat_turn(
        uuid.uuid4(),
        "The curriculum is about Python programming.",
        [],
        owner_id=owner_id,
    )

    assert response["checklist"].curriculum_breakdown == "Python programming"
    assert response["checklist"].outcome_deliverable is None


@pytest.mark.asyncio
async def test_llm_failure_is_not_converted_to_successful_reply():
    service = IntakeChatService(llm=RecordingLLM(error=RuntimeError("provider unavailable")))
async def test_llm_failure_is_not_converted_to_successful_reply() -> None:
    service = IntakeChatService(llm=cast(Any, RecordingLLM(error=RuntimeError("provider unavailable"))))

    with pytest.raises(IntakeProcessingError) as exc_info:
        await service.process_chat_turn(
            uuid.uuid4(), "Launch Atlas", [], owner_id=uuid.uuid4()
        )

    assert isinstance(exc_info.value.__cause__, RuntimeError)


@pytest.mark.asyncio
async def test_api_maps_intake_processing_failure_to_502(monkeypatch):
async def test_api_maps_intake_processing_failure_to_502(monkeypatch: Any) -> None:
    campaign_id = uuid.uuid4()
    user_id = uuid.uuid4()

    monkeypatch.setattr(intake_api.intake_access, "authorize", AsyncMock(return_value=None))
    monkeypatch.setattr(intake_api.intake_service, "get_history", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        intake_api.intake_service, "get_checklist", AsyncMock(return_value=IntakeChecklist())
    )
    monkeypatch.setattr(
        intake_api.intake_service,
        "process_chat_turn",
        AsyncMock(side_effect=IntakeProcessingError("failed")),
    )

    with pytest.raises(HTTPException) as exc_info:
        await intake_api.chat_turn(
            IntakeChatRequest(campaign_id=campaign_id, user_message="Launch Atlas"),
            AuthenticatedUser(id=str(user_id)),
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Intake AI processing failed. Please retry."


@pytest.mark.asyncio
async def test_regression_a_ticket_not_supplied_remains_none(monkeypatch: Any) -> None:
    """Regression A: 'Ticket price has not been supplied.' -> is_free_or_paid is None."""
    llm = RecordingLLM(
        {
            "extracted": {
                "venue": "Pearl Continental Hotel",
                # Even if the LLM mistakenly inferred Paid, negation must override it
                "is_free_or_paid": "Paid",
            },
            "reply": "Noted venue. What else?",
        }
    )
    service = IntakeChatService(llm=cast(Any, llm))
    owner_id = uuid.uuid4()
    monkeypatch.setattr(service, "_save_message", lambda *args: None)
    monkeypatch.setattr(service, "_save_checklist", lambda *args: None)

    response = await service.process_chat_turn(
        uuid.uuid4(),
        "The venue is Pearl Continental Hotel. Ticket price has not been supplied.",
        [],
        owner_id=owner_id,
    )

    assert response["checklist"].is_free_or_paid is None


@pytest.mark.asyncio
async def test_regression_b_ticket_undecided_remains_none(monkeypatch: Any) -> None:
    """Regression B: 'We haven't decided the ticket price yet.' -> is_free_or_paid is None."""
    llm = RecordingLLM(
        {
            "extracted": {
                "event_date": "2026-10-15",
            },
            "reply": "Got the date.",
        }
    )
    service = IntakeChatService(llm=cast(Any, llm))
    owner_id = uuid.uuid4()
    monkeypatch.setattr(service, "_save_message", lambda *args: None)
    monkeypatch.setattr(service, "_save_checklist", lambda *args: None)

    for msg in [
        "We haven't decided the ticket price yet.",
        "Ticket price is unknown",
        "Ticket price is not decided yet",
        "Admission information is not available yet",
        "No ticket price yet",
    ]:
        response = await service.process_chat_turn(
            uuid.uuid4(),
            msg,
            [],
            owner_id=owner_id,
        )
        assert response["checklist"].is_free_or_paid is None, f"Failed for: {msg}"


@pytest.mark.asyncio
async def test_regression_c_explicit_paid_tickets(monkeypatch: Any) -> None:
    """Regression C: 'Tickets cost PKR 2,000.' -> is_free_or_paid == 'Paid'."""
    llm = RecordingLLM(
        {
            "extracted": {},
            "reply": "Noted.",
        }
    )
    service = IntakeChatService(llm=cast(Any, llm))
    owner_id = uuid.uuid4()
    monkeypatch.setattr(service, "_save_message", lambda *args: None)
    monkeypatch.setattr(service, "_save_checklist", lambda *args: None)

    response = await service.process_chat_turn(
        uuid.uuid4(),
        "Tickets cost PKR 2,000.",
        [],
        owner_id=owner_id,
    )

    assert response["checklist"].is_free_or_paid == "Paid"


@pytest.mark.asyncio
async def test_regression_d_explicit_free_admission(monkeypatch: Any) -> None:
    """Regression D: 'Admission is free.' and 'This is a free event' -> is_free_or_paid == 'Free'."""
    llm = RecordingLLM(
        {
            "extracted": {},
            "reply": "Noted.",
        }
    )
    service = IntakeChatService(llm=cast(Any, llm))
    owner_id = uuid.uuid4()
    monkeypatch.setattr(service, "_save_message", lambda *args: None)
    monkeypatch.setattr(service, "_save_checklist", lambda *args: None)

    response1 = await service.process_chat_turn(
        uuid.uuid4(),
        "Admission is free.",
        [],
        owner_id=owner_id,
    )
    assert response1["checklist"].is_free_or_paid == "Free"

    response2 = await service.process_chat_turn(
        uuid.uuid4(),
        "This is a free event.",
        [],
        owner_id=owner_id,
    )
    assert response2["checklist"].is_free_or_paid == "Free"


@pytest.mark.asyncio
async def test_regression_e_exact_objective_preservation(monkeypatch: Any) -> None:
    """Regression E: Exact user-supplied objective preserved across turns, extraction, and persistence."""
    saved_checklists = {}

    service = IntakeChatService(
        llm=cast(
            Any,
            RecordingLLM(
                {
                    "extracted": {
                        "campaign_type": "physical_event",
                        "campaign_name": "NovaCare Hospital Launch",
                        # Simulated LLM hallucinating a shortened/generic objective
                        "objective": "Build awareness",
                    },
                    "reply": "Noted hospital launch details.",
                }
            ),
        )
    )
    owner_id = uuid.uuid4()
    cid = uuid.uuid4()

    monkeypatch.setattr(service, "_save_message", lambda *args: None)
    monkeypatch.setattr(
        service,
        "_save_checklist",
        lambda _cid, _owner, chk: saved_checklists.update({str(_cid): chk}),
    )

    # Turn 1: User explicitly supplies exact objective
    exact_obj = "Build awareness for the new hospital and launch event"
    turn1_msg = (
        f"Campaign: NovaCare Hospital Launch\n"
        f"Objective: {exact_obj}\n"
        f"Audience: Healthcare professionals"
    )
    response1 = await service.process_chat_turn(cid, turn1_msg, [], owner_id=owner_id)

    assert response1["checklist"].objective == exact_obj
    assert saved_checklists[str(cid)].objective == exact_obj

    # Turn 2: User answers next question with venue and ticket negation
    # LLM might return a different/shortened objective or null in extracted
    service.llm = cast(
        Any,
        RecordingLLM(
            {
                "extracted": {
                    "venue": "Pearl Continental Hotel",
                    "objective": "Generic Awareness Goal",
                },
                "reply": "Noted venue.",
            }
        ),
    )
    response2 = await service.process_chat_turn(
        cid,
        "The venue is Pearl Continental Hotel. Ticket price has not been supplied.",
        [{"role": "user", "content": turn1_msg}],
        current_checklist=response1["checklist"],
        owner_id=owner_id,
    )

    # Objective must remain EXACT and not overwritten by subsequent LLM turn
    assert response2["checklist"].objective == exact_obj
    assert saved_checklists[str(cid)].objective == exact_obj
    assert response2["checklist"].is_free_or_paid is None


@pytest.mark.asyncio
async def test_regression_f_app_launch_campaign_type_neutrality(monkeypatch: Any) -> None:
    """Regression F: GlowBook app_launch does not infer ticket fields or require event fields."""
    service = IntakeChatService(
        llm=cast(
            Any,
            RecordingLLM(
                {
                    "extracted": {
                        "campaign_type": "app_launch",
                        "campaign_name": "GlowBook",
                        "objective": "Drive mobile app registrations",
                        "target_audience": "Book enthusiasts and mobile readers",
                        "value_proposition": "Interactive social reading experience",
                    },
                    "reply": "All details gathered.",
                }
            ),
        )
    )
    owner_id = uuid.uuid4()
    cid = uuid.uuid4()
    monkeypatch.setattr(service, "_save_message", lambda *args: None)
    monkeypatch.setattr(service, "_save_checklist", lambda *args: None)

    response = await service.process_chat_turn(
        cid,
        "Launching GlowBook for readers to connect and discover books.",
        [],
        owner_id=owner_id,
    )

    chk = response["checklist"]
    assert chk.campaign_type == "app_launch"
    assert chk.campaign_name == "GlowBook"
    assert chk.is_free_or_paid is None
    assert chk.event_date is None
    assert chk.venue is None
    assert chk.has_guest is None
    assert chk.is_complete() is True


