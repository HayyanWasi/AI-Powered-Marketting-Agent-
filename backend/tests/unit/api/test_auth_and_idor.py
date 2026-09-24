"""Unit tests for Supabase JWT authentication and IDOR prevention."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.api.v1.autopilot import _get_user_settings
from src.models.campaign import Campaign, CampaignState
from src.services.campaign_service import CampaignService, NotFoundError


class TestJwtAuthenticationValidation:
    """Test backend validation logic for Supabase JWT."""

    async def test_invalid_bearer_scheme_raises_401(self) -> None:
        with pytest.raises(HTTPException) as exc:
            await get_authenticated_user(authorization="Basic dXNlcjpwYXNz")
        assert exc.value.status_code == 401
        assert "Invalid authorization scheme" in exc.value.detail

    async def test_empty_bearer_token_raises_401(self) -> None:
        with pytest.raises(HTTPException) as exc:
            await get_authenticated_user(authorization="Bearer   ")
        assert exc.value.status_code == 401
        assert "Empty bearer token" in exc.value.detail

    async def test_invalid_supabase_token_raises_401(self) -> None:
        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.side_effect = Exception("JWT expired or signature invalid")

        with patch("src.config.supabase.get_supabase_client", return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc:
                await get_authenticated_user(authorization="Bearer expired_or_fake_jwt_token")
            assert exc.value.status_code == 401
            assert "Token verification failed" in exc.value.detail

    async def test_valid_supabase_token_resolves_user(self) -> None:
        mock_user = MagicMock()
        user_uuid = str(uuid4())
        mock_user.id = user_uuid
        mock_user.email = "marketer@enterprise.com"
        mock_user.app_metadata = {"roles": ["authenticated", "admin"]}

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_supabase.auth.get_user.return_value = mock_response

        with patch("src.config.supabase.get_supabase_client", return_value=mock_supabase):
            user = await get_authenticated_user(authorization="Bearer valid_supabase_jwt")
            assert isinstance(user, AuthenticatedUser)
            assert user.id == user_uuid
            assert user.email == "marketer@enterprise.com"
            assert "admin" in user.roles

    async def test_invalid_x_user_id_uuid_raises_400(self) -> None:
        with patch("src.config.settings.settings.REQUIRE_AUTH", False):
            with pytest.raises(HTTPException) as exc:
                await get_authenticated_user(x_user_id="not-a-valid-uuid")
            assert exc.value.status_code == 400
            assert "Invalid X-User-Id header format" in exc.value.detail


class TestIdorPreventionCampaigns:
    """Test Insecure Direct Object Reference (IDOR) prevention on campaigns."""

    @pytest.fixture
    def campaign_service(self):
        service = CampaignService()
        service.campaign_repository = MagicMock()
        service.history_service = AsyncMock()
        return service

    async def test_user_cannot_access_other_organization_campaign(self, campaign_service) -> None:
        campaign_id = uuid4()
        user_a_org = uuid4()
        user_b_org = uuid4()

        # Mock repo: returns None when organization_id doesn't match
        async def mock_get_by_id(cid, org_id=None):
            if org_id == user_a_org:
                return Campaign(
                    id=campaign_id,
                    name="User A Campaign",
                    organization_id=user_a_org,
                    state=CampaignState.DRAFT,
                )
            return None

        campaign_service.campaign_repository.get_by_id = AsyncMock(side_effect=mock_get_by_id)

        # User A accessing their own campaign -> Succeeds
        campaign = await campaign_service.get_campaign(campaign_id, organization_id=user_a_org)
        assert campaign.id == campaign_id

        # User B attempting IDOR access to User A's campaign -> Fails with NotFoundError (404/403)
        with pytest.raises(NotFoundError):
            await campaign_service.get_campaign(campaign_id, organization_id=user_b_org)

    async def test_user_cannot_update_other_organization_campaign(self, campaign_service) -> None:
        campaign_id = uuid4()
        user_a_org = uuid4()
        attacker_id = uuid4()

        # Mock repo: returns None when caller is attacker
        async def mock_get_by_id(cid, org_id=None):
            if org_id == user_a_org:
                return Campaign(
                    id=campaign_id,
                    name="Protected Campaign",
                    organization_id=user_a_org,
                    state=CampaignState.DRAFT,
                    version=1,
                )
            return None

        campaign_service.campaign_repository.get_by_id = AsyncMock(side_effect=mock_get_by_id)

        # Attacker attempts to update User A's campaign -> IDOR check blocks it
        with pytest.raises(NotFoundError):
            await campaign_service.update_campaign(
                campaign_id=campaign_id,
                updates={"name": "Tampered Name"},
                expected_version=1,
                actor_id=attacker_id,
                organization_id=attacker_id,
            )


class TestIdorPreventionAutopilot:
    """Test Autopilot user-scoped isolation preventing cross-tenant mutation."""

    def test_autopilot_settings_are_isolated_per_user(self) -> None:
        user_a = str(uuid4())
        user_b = str(uuid4())

        settings_a = _get_user_settings(user_a)
        settings_b = _get_user_settings(user_b)

        # User A changes daily connections and pauses autopilot
        settings_a["daily_connections"] = 24
        settings_a["master_active"] = False

        # Verify User B's settings remain untouched at default
        assert settings_b["daily_connections"] == 25
        assert settings_b["master_active"] is True
        assert _get_user_settings(user_a)["master_active"] is False
        assert _get_user_settings(user_b)["master_active"] is True
