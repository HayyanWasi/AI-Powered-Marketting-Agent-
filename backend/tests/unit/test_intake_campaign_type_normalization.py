"""Focused regression coverage for natural-language campaign types."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.models.intake import CampaignType
from src.services.intake_chat_service import IntakeChatService, _normalize_campaign_type


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("GENERAL_PROMOTION", "general_promotion"),
        ("General Promotion", "general_promotion"),
        ("general-promotion", "general_promotion"),
        ("CampaignType.GENERAL_PROMOTION", "general_promotion"),
        ("APP LAUNCH", "app_launch"),
        ("mobile app launch", "app_launch"),
        ("launching a product", "product_launch"),
        ("New Service Launch", "service_launch"),
        ("in-person event", "physical_event"),
        ("Virtual Webinar", "webinar"),
        ("promotional campaign", "general_promotion"),
        (CampaignType.WEBINAR, "webinar"),
    ],
)
def test_normalize_campaign_type_accepts_human_and_llm_variants(
    raw_value: object, expected: str
) -> None:
    assert _normalize_campaign_type(raw_value) == expected


def test_normalize_campaign_type_rejects_unknown_value() -> None:
    assert _normalize_campaign_type("something entirely different") is None


@pytest.mark.asyncio
async def test_chat_turn_normalizes_uppercase_llm_campaign_type() -> None:
    llm = Mock()
    llm.generate_json = AsyncMock(
        return_value={
            "extracted": {
                "campaign_type": "GENERAL_PROMOTION",
                "campaign_name": "Freshness Sentinel",
                "objective": "Acquire registrations",
                "target_audience": "Product teams",
                "value_proposition": "Faster campaign planning",
            },
            "reply": "Thanks, I have the campaign details.",
        }
    )

    service = IntakeChatService(llm=llm)
    service._save_message = Mock()
    service._save_checklist = Mock()

    result = await service.process_chat_turn(
        uuid4(),
        "This is a general promotion.",
        [],
        owner_id=uuid4(),
    )

    assert result["checklist"].campaign_type is CampaignType.GENERAL_PROMOTION
    assert result["is_complete"] is True
