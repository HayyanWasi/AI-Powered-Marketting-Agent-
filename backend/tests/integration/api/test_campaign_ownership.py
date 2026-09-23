"""Tests to verify campaign and intake ownership boundaries.
Ensure User A cannot read or modify User B's campaigns or intake data.
"""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.api.v1.campaigns import create_campaign
from src.main import app
from src.schemas import CreateCampaignRequest
from src.services.intake_access_service import IntakeAccessDenied

client = TestClient(app)

USER_A_ID = "00000000-0000-0000-0000-00000000000A"
USER_B_ID = "00000000-0000-0000-0000-00000000000B"
CAMPAIGN_B_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def mock_user_a() -> AuthenticatedUser:
    return AuthenticatedUser(id=USER_A_ID, roles=["user"], permissions=[])


@pytest.fixture
def user_a_client() -> Generator[TestClient]:
    app.dependency_overrides[get_authenticated_user] = mock_user_a
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_campaign_b():
    """Mock a campaign owned by User B."""
    mock = MagicMock()
    mock.id = UUID(CAMPAIGN_B_ID)
    mock.organization_id = UUID(USER_B_ID)
    mock.company_profile_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-cccccccccccc")

    # Ensure it works nicely with `if existing_campaign:`
    mock.__bool__ = lambda self: True
    return mock


# --- Tests ---

def test_list_assets_cross_user_denied(user_a_client, mock_campaign_b):
    with patch("src.api.v1.campaigns.CampaignService") as mock_svc_cls:
        # Mock get_campaign to return None (which happens when UUID(user.id) doesn't match owner)
        mock_svc = MagicMock()
        mock_svc.get_campaign = AsyncMock(return_value=None)
        mock_svc_cls.return_value = mock_svc

        response = user_a_client.get(f"/api/campaigns/{CAMPAIGN_B_ID}/assets")
        assert response.status_code == 404


def test_get_campaign_posts_cross_user_denied(user_a_client, mock_campaign_b):
    with patch("src.api.v1.campaigns.CampaignService") as mock_svc_cls:
        # Mock get_campaign to return None
        mock_svc = MagicMock()
        mock_svc.get_campaign = AsyncMock(return_value=None)
        mock_svc_cls.return_value = mock_svc

        response = user_a_client.get(f"/api/campaigns/{CAMPAIGN_B_ID}/posts")
        assert response.status_code == 404


def test_migrate_intake_cross_user_denied(user_a_client):
    with (
        patch("src.api.v1.intake.intake_access.authorize", new=AsyncMock(return_value=None)),
        patch(
            "src.api.v1.intake.intake_access.require_campaign",
            new=AsyncMock(side_effect=IntakeAccessDenied),
        ),
    ):
        response = user_a_client.post(
            "/api/campaigns/intake/migrate",
            json={"session_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "campaign_id": CAMPAIGN_B_ID},
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Intake resource not found or access denied."


def test_confirm_guest_cross_user_denied(user_a_client):
    with patch(
        "src.api.v1.intake.intake_access.authorize",
        new=AsyncMock(side_effect=IntakeAccessDenied),
    ):
        response = user_a_client.post(
            "/api/campaigns/intake/confirm-guest",
            json={"campaign_id": CAMPAIGN_B_ID, "guest_name": "Test Guest", "confirmed": True},
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Intake resource not found or access denied."


def test_reset_intake_session_cross_user_denied(user_a_client):
    with patch(
        "src.api.v1.intake.intake_access.authorize",
        new=AsyncMock(side_effect=IntakeAccessDenied),
    ):
        response = user_a_client.delete(f"/api/campaigns/intake/{CAMPAIGN_B_ID}")
        assert response.status_code == 404
        assert response.json()["message"] == "Intake resource not found or access denied."


@pytest.mark.asyncio
async def test_foreign_company_profile_is_rejected_before_campaign_insert():
    now = datetime.now(UTC)
    request = CreateCampaignRequest(
        name="Blocked foreign brand",
        company_profile_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-cccccccccccc"),
        goals={"primary": "Test ownership"},
        target_audience={},
        platforms=["LinkedIn"],
        schedule={
            "start_date": now,
            "end_date": now + timedelta(days=1),
            "timezone": "UTC",
        },
    )
    campaign_service = AsyncMock()

    with patch(
        "src.api.v1.campaigns.require_profile",
        side_effect=HTTPException(404, "Company profile not found or access denied."),
    ):
        with pytest.raises(HTTPException) as exc:
            await create_campaign(request, campaign_service, mock_user_a())

    assert exc.value.status_code == 404
    campaign_service.create_campaign.assert_not_awaited()

