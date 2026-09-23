"""Regression coverage for intake structured-state integrity.

Covers the confirmed defects where an acknowledged campaign_type never reached
canonical state (flat provider payloads silently discarded), where a later
re-ask of an already-collected campaign_type was not blocked, and where an
unresolvable campaign_type was skipped without telling the user.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from src.models.intake import CampaignType, IntakeChecklist
from src.services.intake_chat_service import IntakeChatService, IntakeProcessingError


class ScriptedLLM:
    """Returns one canned payload per turn, in order."""

    def __init__(self, payloads: list[Any]) -> None:
        self._payloads = list(payloads)
        self.prompts: list[str] = []

    async def generate_json(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> Any:
        self.prompts.append(user_prompt)
        return self._payloads.pop(0)


def _service(payloads: list[Any]) -> IntakeChatService:
    service = IntakeChatService(llm=ScriptedLLM(payloads))
    service._save_message = Mock()
    service._save_checklist = Mock()
    return service


async def _turn(
    service: IntakeChatService,
    message: str,
    checklist: IntakeChecklist | None,
    campaign_id: UUID,
    owner_id: UUID,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return await service.process_chat_turn(
        campaign_id,
        message,
        history or [],
        checklist,
        owner_id=owner_id,
    )


def _round_trip(checklist: IntakeChecklist) -> IntakeChecklist:
    """Mirror the persist -> reload cycle performed by the DB layer."""
    return IntakeChecklist.model_validate(checklist.model_dump(mode="json"))


# ── A. canonical wrapped payload ──


@pytest.mark.asyncio
async def test_wrapped_payload_persists_campaign_type() -> None:
    service = _service(
        [
            {
                "extracted": {"campaign_type": "general_promotion"},
                "reply": "Thanks for confirming the campaign type!",
            }
        ]
    )

    result = await _turn(service, "it is a general promotion only", None, uuid4(), uuid4())

    assert result["checklist"].campaign_type is CampaignType.GENERAL_PROMOTION
    service._save_checklist.assert_called_once()


# ── B. backward-compatible flat payload ──


@pytest.mark.asyncio
async def test_flat_payload_is_normalized_and_persisted() -> None:
    service = _service(
        [
            {
                "campaign_type": "General Promotion",
                "campaign_name": "September Discount",
                "reply": "Thanks for confirming the campaign type as a general promotion!",
            }
        ]
    )

    result = await _turn(service, "it is a general promotion only", None, uuid4(), uuid4())

    assert result["checklist"].campaign_type is CampaignType.GENERAL_PROMOTION
    assert result["checklist"].campaign_name == "September Discount"


@pytest.mark.asyncio
async def test_unrecognizable_payload_shape_fails_truthfully() -> None:
    service = _service([{"status": "ok", "reply": "All set!"}])

    with pytest.raises(IntakeProcessingError):
        await _turn(service, "it is a general promotion only", None, uuid4(), uuid4())

    service._save_checklist.assert_not_called()


# ── C. omitted fields must not erase confirmed state ──


@pytest.mark.asyncio
async def test_later_turn_omitting_campaign_type_preserves_it() -> None:
    campaign_id, owner_id = uuid4(), uuid4()
    service = _service(
        [
            {
                "extracted": {"campaign_type": "general_promotion"},
                "reply": "Thanks for confirming the campaign type!",
            },
            {
                "extracted": {"target_audience": "Families renting homes"},
                "reply": "Noted the audience.",
            },
            {
                "extracted": {"campaign_type": None, "objective": "Fill vacant rentals"},
                "reply": "Noted the objective.",
            },
        ]
    )

    checklist = None
    for message in (
        "it is a general promotion only",
        "our audience is families renting homes",
        "the objective is to fill vacant rentals",
    ):
        result = await _turn(service, message, checklist, campaign_id, owner_id)
        checklist = _round_trip(result["checklist"])

    assert checklist is not None
    assert checklist.campaign_type is CampaignType.GENERAL_PROMOTION
    assert checklist.target_audience == "Families renting homes"


# ── D. anti-repetition guard covers campaign_type ──


@pytest.mark.asyncio
async def test_reask_of_collected_campaign_type_is_rewritten() -> None:
    existing = IntakeChecklist(
        campaign_type=CampaignType.GENERAL_PROMOTION,
        campaign_name="September Discount",
    )
    service = _service(
        [
            {
                "extracted": {"target_audience": "Families renting homes"},
                "reply": "Thanks! We still need to know the type of campaign and the category.",
            }
        ]
    )

    result = await _turn(
        service, "our audience is families renting homes", existing, uuid4(), uuid4()
    )

    assert "type of campaign" not in result["reply"].lower()
    assert result["checklist"].campaign_type is CampaignType.GENERAL_PROMOTION


# ── E. explicit correction still wins ──


@pytest.mark.asyncio
async def test_explicit_correction_updates_campaign_type() -> None:
    existing = IntakeChecklist(campaign_type=CampaignType.GENERAL_PROMOTION)
    service = _service(
        [{"extracted": {"campaign_type": "webinar"}, "reply": "Updated to a webinar."}]
    )

    result = await _turn(service, "Actually make it a webinar", existing, uuid4(), uuid4())

    assert result["checklist"].campaign_type is CampaignType.WEBINAR


# ── F. unresolvable campaign type is never acknowledged ──


@pytest.mark.asyncio
async def test_unresolvable_campaign_type_is_not_acknowledged() -> None:
    service = _service(
        [
            {
                "extracted": {"campaign_type": "seasonal vibes blast"},
                "reply": "Thanks for confirming the campaign type!",
            }
        ]
    )

    result = await _turn(service, "it is a seasonal vibes blast", None, uuid4(), uuid4())

    assert result["checklist"].campaign_type is None
    assert result["is_complete"] is False
    assert "thanks for confirming" not in result["reply"].lower()
    assert "seasonal vibes blast" in result["reply"]


# ── G. existing completion behaviour unchanged ──


@pytest.mark.asyncio
async def test_complete_intake_still_completes() -> None:
    service = _service(
        [
            {
                "extracted": {
                    "campaign_type": "GENERAL_PROMOTION",
                    "campaign_name": "Freshness Sentinel",
                    "objective": "Acquire registrations",
                    "target_audience": "Product teams",
                    "value_proposition": "Faster campaign planning",
                },
                "reply": "Thanks, I have the campaign details.",
            }
        ]
    )

    result = await _turn(service, "This is a general promotion.", None, uuid4(), uuid4())

    assert result["checklist"].campaign_type is CampaignType.GENERAL_PROMOTION
    assert result["is_complete"] is True


# ── H. small-model "null" string sentinels must not fail the turn ──


@pytest.mark.asyncio
async def test_string_null_sentinels_do_not_fail_validation() -> None:
    service = _service(
        [
            {
                "extracted": {
                    "campaign_type": "general_promotion",
                    "value_proposition": "",
                    "cta_url": "",
                    "has_guest": "null",
                    "guest_name": "null",
                    "is_free_or_paid": "n/a",
                },
                "reply": "Noted.",
            }
        ]
    )

    result = await _turn(service, "It is a general promotion", None, uuid4(), uuid4())

    assert result["checklist"].campaign_type is CampaignType.GENERAL_PROMOTION
    assert result["checklist"].has_guest is None
    assert result["checklist"].guest_name is None
    assert result["checklist"].is_free_or_paid is None


# ── I. one bad nested field is dropped, not the whole turn (502 regression) ──


@pytest.mark.asyncio
async def test_invalid_audience_profile_field_does_not_502_the_turn() -> None:
    """Reproduces a live payload shape: the model puts a value valid for one
    Literal field ('source') into a sibling Literal field ('confidence').
    The whole turn must still succeed; only audience_profile is dropped.
    """
    service = _service(
        [
            {
                "extracted": {
                    "campaign_type": "general_promotion",
                    "campaign_name": "September Special",
                    "audience_profile": {
                        "summary": "Renters",
                        "source": "explicit",
                        "confidence": "fallback",  # invalid: not a confidence literal
                        "inference_version": "audience-v1",
                    },
                },
                "reply": "Thanks!",
            }
        ]
    )

    result = await _turn(service, "September Special, general promotion", None, uuid4(), uuid4())

    assert result["checklist"].campaign_type is CampaignType.GENERAL_PROMOTION
    assert result["checklist"].campaign_name == "September Special"
    assert result["checklist"].audience_profile is None


# ── J. deterministic campaign_type detection from a longer message ──


@pytest.mark.asyncio
async def test_deterministic_detection_fills_campaign_type_when_llm_misses_it() -> None:
    """Reproduces the live failure: the model omits campaign_type entirely on
    a turn where the user stated it in a longer sentence. The deterministic
    pre-extraction must catch what the LLM missed.
    """
    service = _service(
        [
            {
                "extracted": {
                    "campaign_name": "September Special",
                    "objective": "20% off on rentals",
                    # campaign_type omitted by the model, as observed live
                },
                "reply": "Thanks! What type of campaign is this?",
            }
        ]
    )

    result = await _turn(
        service,
        "we have 5 houses for rent, 20% off, it is general promotion, name is September Special",
        None,
        uuid4(),
        uuid4(),
    )

    assert result["checklist"].campaign_type is CampaignType.GENERAL_PROMOTION


@pytest.mark.asyncio
async def test_deterministic_detection_does_not_override_explicit_correction() -> None:
    """The deterministic pass only fills an unset field; an existing value is
    left for the normal LLM-driven explicit-correction path to update.
    """
    existing = IntakeChecklist(campaign_type=CampaignType.GENERAL_PROMOTION)
    service = _service(
        [{"extracted": {"campaign_type": "webinar"}, "reply": "Updated to a webinar."}]
    )

    result = await _turn(
        service,
        "Actually, general promotion isn't right, make it a webinar",
        existing,
        uuid4(),
        uuid4(),
    )

    assert result["checklist"].campaign_type is CampaignType.WEBINAR
