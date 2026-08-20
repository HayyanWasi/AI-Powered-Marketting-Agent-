"""Comprehensive API tests for all non-image endpoints.

Covers:
  - GET /, GET /health (root)
  - POST/GET/PUT/DELETE /api/company (company CRUD)
  - GET /api/company/{id}/brand-info
  - POST /api/guest/search
  - POST/GET/PUT/DELETE /campaigns (campaign CRUD)
  - POST /campaigns/{id}/transition, /archive, /restore
  - GET /campaigns/{id}/history
  - POST/GET /campaigns/{id}/assets
  - POST /api/campaigns/{id}/validate
  - GET /api/campaigns/{id}/preview/check
  - POST /workflow/execute, /resume, /approve, /reject
  - GET /workflow/status/{thread_id}

Schema-as-contract via Pydantic model_validate. Unconditional header checks.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from pydantic import BaseModel

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.main import app
from src.models.validation import (
    ImageValidationResult,
    TextValidationResult,
    ValidationResponse,
    ValidationStatus,
)
from src.schemas import (
    AssetListResponse,
    AssetResponse,
    CampaignListResponse,
    CampaignResponse,
    HistoryListResponse,
    StateTransitionResponse,
)

client = TestClient(app)

# Mock authenticated user for all v1 routes (id must be valid UUID for services that call UUID(user.id))
_mock_user = AuthenticatedUser(
    id="00000000-0000-0000-0000-000000000001", roles=["admin"], permissions=["all"]
)
app.dependency_overrides[get_authenticated_user] = lambda: _mock_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_PROFILE_ID = "550e8400-e29b-41d4-a716-446655440000"
VALID_CAMPAIGN_ID = "660e8400-e29b-41d4-a716-446655440000"
ORG_ID = "00000000-0000-0000-0000-000000000001"
ACTOR_ID = "00000000-0000-0000-0000-000000000002"


def _assert_schema(data: dict, model_class: type[BaseModel]) -> BaseModel:
    result = model_class.model_validate(data)
    assert isinstance(result, model_class)
    return result


def _assert_json_content_type(response):
    headers = response.headers
    assert "application/json" in headers["content-type"]


def _make_campaign_request(**overrides) -> dict:
    defaults = {
        "name": "Test Campaign",
        "goals": {"primary": "Brand awareness", "metrics": ["impressions"], "targets": {}},
        "target_audience": {
            "segments": ["tech professionals"],
            "demographics": {"age": "25-40"},
            "interests": ["AI", "SaaS"],
        },
        "platforms": ["linkedin"],
        "schedule": {
            "start_date": "2026-08-01T00:00:00Z",
            "end_date": "2026-08-31T23:59:59Z",
            "timezone": "UTC",
        },
    }
    defaults.update(overrides)
    return defaults


def _campaign_dict(**overrides) -> dict:
    """Build a minimal CampaignResponse-shaped dict."""
    d = {
        "id": VALID_CAMPAIGN_ID,
        "organization_id": ORG_ID,
        "company_profile_id": None,
        "name": "Test Campaign",
        "goals": {"primary": "awareness", "metrics": [], "targets": {}},
        "target_audience": {"segments": [], "demographics": {}, "interests": []},
        "platforms": ["linkedin"],
        "schedule": {
            "start_date": "2026-08-01T00:00:00Z",
            "end_date": "2026-08-31T23:59:59Z",
            "timezone": "UTC",
        },
        "metadata": {},
        "state": "Draft",
        "version": 1,
        "created_at": "2026-07-20T00:00:00Z",
        "updated_at": "2026-07-20T00:00:00Z",
        "published_at": None,
        "archived_at": None,
        "created_by": ACTOR_ID,
        "updated_by": ACTOR_ID,
    }
    d.update(overrides)
    return d


def _make_mock_campaign(**overrides) -> MagicMock:
    """Create a mock campaign that passes `if not campaign:` truthiness."""
    data = _campaign_dict(**overrides)
    m = MagicMock()
    m.__dict__.update(data)
    m.to_dict.return_value = data
    # Ensure truthiness works for `if not campaign:` checks
    m.__bool__ = lambda self: True
    m.__repr__ = lambda self: f"MockCampaign({data['id']})"
    return m


def _mock_validation_response(
    campaign_id: str = VALID_CAMPAIGN_ID,
    platform: str = "instagram",
    status: str = "pass",
    text_passed: bool = True,
    image_passed: bool = True,
) -> ValidationResponse:
    """Build a proper ValidationResponse matching the real schema."""
    return ValidationResponse(
        campaign_id=campaign_id,
        platform=platform,
        status=ValidationStatus(status),
        text_validation=TextValidationResult(
            passed=text_passed,
            character_count=100,
            character_limit=2200,
            violations=[],
        ),
        image_validation=ImageValidationResult(
            passed=image_passed,
            width=1080,
            height=1080,
            content_type="image/png",
            violations=[],
        ),
        can_preview=(status == "pass" and text_passed and image_passed),
    )


# ===========================================================================
# 1. Root / Health
# ===========================================================================


class TestRootAndHealth:
    """GET /api/health — smoke test."""

    def test_health_returns_healthy(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "healthy"
        _assert_json_content_type(response)


# ===========================================================================
# 2. Company Profile CRUD
# ===========================================================================


class TestCompanyCRUD:
    """POST/GET/PUT/DELETE /api/company — full lifecycle."""

    @patch(
        "src.api.v1.company.ListCompanyService",
        return_value=MagicMock(execute=MagicMock(return_value=[])),
    )
    def test_list_profiles_returns_list(self, mock_cls):
        response = client.get("/api/company")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        _assert_json_content_type(response)

    def test_create_profile_success(self):
        mock_profile = type(
            "Profile",
            (),
            {
                "id": VALID_PROFILE_ID,
                "company_name": "API Test Co",
                "brand_guidelines": "Test guidelines",
                "brand_tone": "Professional",
                "reference_image_urls": [],
                "created_at": "2026-01-01",
                "updated_at": "2026-01-01",
            },
        )()

        with patch("src.api.v1.company.CreateCompanyService") as mock_cls:
            mock_cls.return_value.execute.return_value = mock_profile
            response = client.post(
                "/api/company",
                json={
                    "company_name": "API Test Co",
                    "brand_guidelines": "Test guidelines",
                    "brand_tone": "Professional",
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == VALID_PROFILE_ID
            assert data["company_name"] == "API Test Co"
            assert "reference_image_urls" in data
            _assert_json_content_type(response)

    def test_create_profile_duplicate_returns_409(self):
        with patch("src.api.v1.company.CreateCompanyService") as mock_cls:
            mock_cls.return_value.execute.side_effect = ValueError(
                "Company name 'DupCo' already exists"
            )
            response = client.post(
                "/api/company",
                json={"company_name": "DupCo", "brand_guidelines": "guidelines"},
            )
            assert response.status_code == 409

    def test_create_profile_missing_fields_returns_422(self):
        response = client.post("/api/company", json={})
        assert response.status_code == 422

    def test_create_profile_empty_name_returns_422(self):
        response = client.post(
            "/api/company",
            json={"company_name": "", "brand_guidelines": "guidelines"},
        )
        assert response.status_code == 422

    def test_get_profile_success(self):
        with patch("src.api.v1.company.GetCompanyService") as mock_cls:
            mock_cls.return_value.execute.return_value = {
                "id": VALID_PROFILE_ID,
                "company_name": "Test Co",
                "brand_guidelines": "guidelines",
                "brand_tone": "Pro",
                "reference_image_urls": [],
                "created_at": "2026-01-01",
                "updated_at": "2026-01-01",
                "is_complete": True,
            }
            response = client.get(f"/api/company/{VALID_PROFILE_ID}")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == VALID_PROFILE_ID
            _assert_json_content_type(response)

    def test_get_profile_not_found_returns_404(self):
        with patch("src.api.v1.company.GetCompanyService") as mock_cls:
            mock_cls.return_value.execute.side_effect = ValueError("Company profile not found")
            response = client.get(f"/api/company/{VALID_PROFILE_ID}")
            assert response.status_code == 404

    def test_get_profile_invalid_uuid_returns_422(self):
        response = client.get("/api/company/not-a-uuid")
        assert response.status_code == 422

    def test_update_profile_success(self):
        mock_profile = type(
            "Profile",
            (),
            {
                "id": VALID_PROFILE_ID,
                "company_name": "Updated Co",
                "brand_guidelines": "updated guidelines",
                "brand_tone": "Casual",
                "reference_image_urls": [],
                "created_at": "2026-01-01",
                "updated_at": "2026-01-02",
            },
        )()

        with patch("src.api.v1.company.UpdateCompanyService") as mock_cls:
            mock_cls.return_value.execute.return_value = mock_profile
            response = client.put(
                f"/api/company/{VALID_PROFILE_ID}",
                json={"company_name": "Updated Co", "brand_tone": "Casual"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["company_name"] == "Updated Co"
            _assert_json_content_type(response)

    def test_update_profile_not_found_returns_404(self):
        with patch("src.api.v1.company.UpdateCompanyService") as mock_cls:
            mock_cls.return_value.execute.side_effect = ValueError("Company profile not found")
            response = client.put(
                f"/api/company/{VALID_PROFILE_ID}",
                json={"company_name": "X"},
            )
            assert response.status_code == 404

    def test_update_profile_no_fields_returns_422(self):
        response = client.put(f"/api/company/{VALID_PROFILE_ID}", json={})
        assert response.status_code == 422

    def test_delete_profile_success(self):
        with patch("src.api.v1.company.DeleteCompanyService") as mock_cls:
            mock_cls.return_value.execute.return_value = None
            response = client.delete(f"/api/company/{VALID_PROFILE_ID}")
            assert response.status_code == 204

    def test_delete_profile_not_found_returns_404(self):
        with patch("src.api.v1.company.DeleteCompanyService") as mock_cls:
            mock_cls.return_value.execute.side_effect = ValueError("Company profile not found")
            response = client.delete(f"/api/company/{VALID_PROFILE_ID}")
            assert response.status_code == 404

    def test_brand_info_success(self):
        with patch("src.api.v1.company.CampaignLookupService") as mock_cls:
            mock_cls.return_value.execute.return_value = {
                "id": VALID_PROFILE_ID,
                "company_name": "Brand Co",
                "brand_guidelines": "guidelines",
                "is_complete": True,
            }
            response = client.get(f"/api/company/{VALID_PROFILE_ID}/brand-info")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == VALID_PROFILE_ID
            _assert_json_content_type(response)

    def test_brand_info_incomplete_returns_422(self):
        with patch("src.api.v1.company.CampaignLookupService") as mock_cls:
            mock_cls.return_value.execute.side_effect = ValueError("Profile is incomplete")
            response = client.get(f"/api/company/{VALID_PROFILE_ID}/brand-info")
            assert response.status_code == 422

    def test_brand_info_not_found_returns_404(self):
        with patch("src.api.v1.company.CampaignLookupService") as mock_cls:
            mock_cls.return_value.execute.side_effect = ValueError("Company profile not found")
            response = client.get(f"/api/company/{VALID_PROFILE_ID}/brand-info")
            assert response.status_code == 404


# ===========================================================================
# 3. Guest Search
# ===========================================================================


class TestGuestSearch:
    """POST /api/guest/search — guest info lookup."""

    @patch("src.api.v1.guest.llm_service")
    @patch("src.api.v1.guest.search_service")
    def test_search_success(self, mock_search, mock_llm):
        mock_search.search.return_value = [
            {"title": "John Doe CEO", "body": "CEO of TechCorp", "href": "https://example.com"}
        ]

        profile_data = MagicMock()
        profile_data.full_name = "John Doe"
        profile_data.current_position = "CEO"
        profile_data.organization = "TechCorp"
        profile_data.professional_biography = "Experienced leader"
        profile_data.areas_of_expertise = ["leadership", "tech"]
        profile_data.confidence_level = "HIGH"
        mock_llm.analyze_search_results.return_value = profile_data

        response = client.post(
            "/api/guest/search",
            json={"guest_name": "John Doe", "company_name": "TechCorp"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["needs_manual_input"] is False
        assert data["profile"]["full_name"] == "John Doe"
        assert data["profile"]["current_position"] == "CEO"
        _assert_json_content_type(response)

    @patch("src.api.v1.guest.search_service")
    def test_search_no_results_returns_needs_manual(self, mock_search):
        mock_search.search.return_value = []
        response = client.post(
            "/api/guest/search",
            json={"guest_name": "Unknown Person"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["needs_manual_input"] is True
        assert "error" in data

    @patch("src.api.v1.guest.search_service")
    def test_search_service_error_returns_502(self, mock_search):
        from src.services.search import SearchError

        mock_search.search.side_effect = SearchError("Service unavailable")
        response = client.post(
            "/api/guest/search",
            json={"guest_name": "John Doe"},
        )
        assert response.status_code == 502

    def test_search_missing_name_returns_422(self):
        response = client.post("/api/guest/search", json={})
        assert response.status_code == 422

    def test_search_empty_name_returns_422(self):
        response = client.post("/api/guest/search", json={"guest_name": ""})
        assert response.status_code == 422


# ===========================================================================
# 4. Campaign Management
# ===========================================================================


class TestCampaignCRUD:
    """POST/GET/PUT/DELETE /campaigns — full lifecycle with schema validation."""

    @patch("src.api.v1.campaigns.CampaignService")
    def test_create_campaign_success(self, mock_svc_cls):
        campaign_data = _campaign_dict()
        campaign = MagicMock()
        campaign.to_dict.return_value = campaign_data
        mock_svc = MagicMock()
        mock_svc.create_campaign = AsyncMock(return_value=campaign)
        mock_svc_cls.return_value = mock_svc

        response = client.post("/api/campaigns", json=_make_campaign_request())

        assert response.status_code == 201
        data = response.json()
        _assert_schema(data, CampaignResponse)
        assert data["name"] == "Test Campaign"
        assert data["state"] == "Draft"
        assert data["version"] == 1
        _assert_json_content_type(response)

    def test_create_campaign_missing_body_returns_422(self):
        response = client.post("/api/campaigns", json={})
        assert response.status_code == 422

    def test_create_campaign_missing_name_returns_422(self):
        response = client.post(
            "/api/campaigns",
            json={
                "goals": {"primary": "awareness"},
                "target_audience": {"segments": []},
                "platforms": ["linkedin"],
                "schedule": {
                    "start_date": "2026-08-01T00:00:00Z",
                    "end_date": "2026-08-31T23:59:59Z",
                    "timezone": "UTC",
                },
            },
        )
        assert response.status_code == 422

    def test_create_campaign_empty_platforms_returns_422(self):
        response = client.post("/api/campaigns", json=_make_campaign_request(platforms=[]))
        assert response.status_code == 422

    @patch("src.api.v1.campaigns.CampaignService")
    def test_create_campaign_duplicate_name_returns_409(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.create_campaign = AsyncMock(
            side_effect=ValueError("Campaign name 'Test Campaign' already exists")
        )
        response = client.post("/api/campaigns", json=_make_campaign_request())
        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "conflict"

    @patch("src.api.v1.campaigns.CampaignService")
    def test_list_campaigns_success(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.list_campaigns = AsyncMock(return_value=([], 0))

        response = client.get("/api/campaigns")
        assert response.status_code == 200
        data = response.json()
        _assert_schema(data, CampaignListResponse)
        assert data["campaigns"] == []
        assert data["total"] == 0
        _assert_json_content_type(response)

    @patch("src.api.v1.campaigns.CampaignService")
    def test_list_campaigns_with_pagination(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.list_campaigns = AsyncMock(return_value=([], 50))

        response = client.get("/api/campaigns?page=2&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10

    def test_list_campaigns_invalid_page_returns_422(self):
        response = client.get("/api/campaigns?page=0")
        assert response.status_code == 422

    @patch("src.api.v1.campaigns.CampaignService")
    def test_get_campaign_success(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_campaign = AsyncMock(return_value=_make_mock_campaign())

        response = client.get(f"/api/campaigns/{VALID_CAMPAIGN_ID}")
        assert response.status_code == 200
        data = response.json()
        _assert_schema(data, CampaignResponse)
        assert data["id"] == VALID_CAMPAIGN_ID
        _assert_json_content_type(response)

    @patch("src.api.v1.campaigns.CampaignService")
    def test_get_campaign_not_found(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_campaign = AsyncMock(return_value=None)

        response = client.get(f"/api/campaigns/{VALID_CAMPAIGN_ID}")
        assert response.status_code == 404

    def test_get_campaign_invalid_uuid_returns_422(self):
        response = client.get("/api/campaigns/not-a-uuid")
        assert response.status_code == 422

    @patch("src.api.v1.campaigns.CampaignService")
    def test_delete_campaign_success(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.delete_campaign = AsyncMock(return_value=None)

        response = client.delete(f"/api/campaigns/{VALID_CAMPAIGN_ID}")
        assert response.status_code == 204

    @patch("src.api.v1.campaigns.CampaignService")
    def test_delete_campaign_not_found(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        from src.models.errors import NotFoundError as NE

        mock_svc.delete_campaign = AsyncMock(side_effect=NE("Campaign", VALID_CAMPAIGN_ID))
        response = client.delete(f"/api/campaigns/{VALID_CAMPAIGN_ID}")
        assert response.status_code == 404


class TestCampaignStateTransitions:
    """POST /campaigns/{id}/transition, /archive, /restore."""

    @patch("src.api.v1.campaigns.HistoryService")
    @patch("src.api.v1.campaigns.CampaignService")
    def test_transition_success(self, mock_svc_cls, mock_hist_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_hist = MagicMock()
        mock_hist_cls.return_value = mock_hist

        mock_svc.transition_campaign = AsyncMock(
            return_value=_make_mock_campaign(state="Review", version=2)
        )
        mock_hist.get_history = AsyncMock(return_value=([], 0))

        response = client.post(
            f"/api/campaigns/{VALID_CAMPAIGN_ID}/transition",
            json={"to_state": "Review", "reason": "Ready for review"},
        )
        assert response.status_code == 200
        data = response.json()
        _assert_schema(data, StateTransitionResponse)
        assert data["campaign"]["state"] == "Review"
        _assert_json_content_type(response)

    @patch("src.api.v1.campaigns.CampaignService")
    def test_transition_not_found(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        from src.models.errors import NotFoundError as NE

        mock_svc.transition_campaign = AsyncMock(side_effect=NE("Campaign", VALID_CAMPAIGN_ID))
        response = client.post(
            f"/api/campaigns/{VALID_CAMPAIGN_ID}/transition",
            json={"to_state": "Review"},
        )
        assert response.status_code == 404

    @patch("src.api.v1.campaigns.CampaignService")
    def test_transition_invalid_state_returns_409(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        from src.models.errors import StateTransitionError as STE

        mock_svc.transition_campaign = AsyncMock(
            side_effect=STE("Draft", "Published", ["Review", "Archived"])
        )
        response = client.post(
            f"/api/campaigns/{VALID_CAMPAIGN_ID}/transition",
            json={"to_state": "Published"},
        )
        assert response.status_code == 409

    def test_transition_missing_body_returns_422(self):
        response = client.post(f"/api/campaigns/{VALID_CAMPAIGN_ID}/transition", json={})
        assert response.status_code == 422

    @patch("src.api.v1.campaigns.CampaignService")
    def test_archive_success(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.archive_campaign = AsyncMock(
            return_value=_make_mock_campaign(state="Archived", version=3)
        )

        response = client.post(
            f"/api/campaigns/{VALID_CAMPAIGN_ID}/archive",
            params={"reason": "No longer needed"},
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        _assert_schema(data, CampaignResponse)
        assert data["state"] == "Archived"

    @patch("src.api.v1.campaigns.CampaignService")
    def test_archive_not_found(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        from src.models.errors import NotFoundError as NE

        mock_svc.archive_campaign = AsyncMock(side_effect=NE("Campaign", VALID_CAMPAIGN_ID))
        response = client.post(f"/api/campaigns/{VALID_CAMPAIGN_ID}/archive", json={})
        assert response.status_code == 404

    @patch("src.api.v1.campaigns.CampaignService")
    def test_restore_success(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.restore_campaign = AsyncMock(
            return_value=_make_mock_campaign(state="Draft", version=4)
        )

        response = client.post(f"/api/campaigns/{VALID_CAMPAIGN_ID}/restore", json={})
        assert response.status_code == 200
        data = response.json()
        _assert_schema(data, CampaignResponse)
        assert data["state"] == "Draft"

    @patch("src.api.v1.campaigns.CampaignService")
    def test_restore_not_found(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        from src.models.errors import NotFoundError as NE

        mock_svc.restore_campaign = AsyncMock(side_effect=NE("Campaign", VALID_CAMPAIGN_ID))
        response = client.post(f"/api/campaigns/{VALID_CAMPAIGN_ID}/restore", json={})
        assert response.status_code == 404


class TestCampaignHistory:
    """GET /campaigns/{id}/history — paginated history."""

    @patch("src.api.v1.campaigns.HistoryService")
    @patch("src.api.v1.campaigns.CampaignService")
    def test_history_success(self, mock_svc_cls, mock_hist_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_hist = MagicMock()
        mock_hist_cls.return_value = mock_hist

        mock_svc.get_campaign = AsyncMock(return_value=_make_mock_campaign())
        mock_hist.get_history = AsyncMock(return_value=([], 0))

        response = client.get(f"/api/campaigns/{VALID_CAMPAIGN_ID}/history")
        assert response.status_code == 200
        data = response.json()
        _assert_schema(data, HistoryListResponse)
        assert data["history"] == []
        _assert_json_content_type(response)

    @patch("src.api.v1.campaigns.CampaignService")
    def test_history_not_found(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_campaign = AsyncMock(return_value=None)

        response = client.get(f"/api/campaigns/{VALID_CAMPAIGN_ID}/history")
        assert response.status_code == 404

    @patch("src.api.v1.campaigns.HistoryService")
    @patch("src.api.v1.campaigns.CampaignService")
    def test_history_with_pagination(self, mock_svc_cls, mock_hist_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_hist = MagicMock()
        mock_hist_cls.return_value = mock_hist

        mock_svc.get_campaign = AsyncMock(return_value=_make_mock_campaign())
        mock_hist.get_history = AsyncMock(return_value=([], 25))

        response = client.get(f"/api/campaigns/{VALID_CAMPAIGN_ID}/history?page=2&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10


class TestCampaignAssets:
    """POST/GET /campaigns/{id}/assets — asset management."""

    @patch("src.api.v1.campaigns.AssetService")
    @patch("src.api.v1.campaigns.CampaignService")
    def test_create_asset_success(self, mock_svc_cls, mock_asset_cls):
        mock_svc = MagicMock()
        mock_svc.get_campaign = AsyncMock(return_value=_make_mock_campaign())
        mock_svc_cls.return_value = mock_svc

        asset = MagicMock()
        asset.id = "770e8400-e29b-41d4-a716-446655440000"
        asset.campaign_id = VALID_CAMPAIGN_ID
        asset.asset_type = "copy"
        asset.content = {"text": "Hello World"}
        asset.storage_path = None
        asset.source = "ai"
        asset.created_at = "2026-07-20T00:00:00Z"
        asset.created_by = ACTOR_ID
        asset.to_dict.return_value = {
            "id": "770e8400-e29b-41d4-a716-446655440000",
            "campaign_id": VALID_CAMPAIGN_ID,
            "asset_type": "copy",
            "content": {"text": "Hello World"},
            "storage_path": None,
            "source": "ai",
            "created_at": "2026-07-20T00:00:00Z",
            "created_by": ACTOR_ID,
        }
        mock_asset_cls.return_value.create_asset = AsyncMock(return_value=asset)

        response = client.post(
            f"/api/campaigns/{VALID_CAMPAIGN_ID}/assets",
            json={
                "asset_type": "copy",
                "content": {"text": "Hello World"},
                "source": "ai",
            },
        )
        assert response.status_code == 201
        data = response.json()
        _assert_schema(data, AssetResponse)
        assert data["asset_type"] == "copy"
        _assert_json_content_type(response)

    @patch("src.api.v1.campaigns.CampaignService")
    def test_create_asset_campaign_not_found(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_campaign = AsyncMock(return_value=None)

        response = client.post(
            f"/api/campaigns/{VALID_CAMPAIGN_ID}/assets",
            json={"asset_type": "copy", "content": {}, "source": "ai"},
        )
        assert response.status_code == 404

    def test_create_asset_missing_body_returns_422(self):
        response = client.post(f"/api/campaigns/{VALID_CAMPAIGN_ID}/assets", json={})
        assert response.status_code == 422

    @patch("src.api.v1.campaigns.AssetService")
    @patch("src.api.v1.campaigns.CampaignService")
    def test_list_assets_success(self, mock_svc_cls, mock_asset_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc

        mock_svc.get_campaign = AsyncMock(return_value=_make_mock_campaign())
        mock_asset_cls.return_value.list_assets = AsyncMock(return_value=[])

        response = client.get(f"/api/campaigns/{VALID_CAMPAIGN_ID}/assets")
        assert response.status_code == 200
        data = response.json()
        _assert_schema(data, AssetListResponse)
        assert data["assets"] == []
        _assert_json_content_type(response)

    @patch("src.api.v1.campaigns.CampaignService")
    def test_list_assets_campaign_not_found(self, mock_svc_cls):
        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_campaign = AsyncMock(return_value=None)

        response = client.get(f"/api/campaigns/{VALID_CAMPAIGN_ID}/assets")
        assert response.status_code == 404


# ===========================================================================
# 5. Validation
# ===========================================================================


class TestValidation:
    """POST /api/campaigns/{id}/validate, GET /api/campaigns/{id}/preview/check."""

    @patch("src.api.v1.validation.validation_gateway")
    def test_validate_success(self, mock_gw):
        mock_gw.validate_campaign = AsyncMock(return_value=_mock_validation_response(status="pass"))

        response = client.post(
            f"/api/campaigns/{VALID_CAMPAIGN_ID}/validate",
            json={"text_content": "Check out our summer sale!", "platform": "instagram"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pass"
        assert data["can_preview"] is True
        _assert_json_content_type(response)

    @patch("src.api.v1.validation.validation_gateway")
    def test_validate_with_image(self, mock_gw):
        mock_gw.validate_campaign = AsyncMock(return_value=_mock_validation_response(status="pass"))

        response = client.post(
            f"/api/campaigns/{VALID_CAMPAIGN_ID}/validate",
            json={
                "text_content": "Summer sale!",
                "platform": "facebook",
                "image_url": "https://example.com/image.png",
            },
        )
        assert response.status_code == 200

    def test_validate_missing_text_returns_422(self):
        response = client.post(
            f"/api/campaigns/{VALID_CAMPAIGN_ID}/validate",
            json={"platform": "instagram"},
        )
        assert response.status_code == 422

    def test_validate_missing_platform_returns_422(self):
        response = client.post(
            f"/api/campaigns/{VALID_CAMPAIGN_ID}/validate",
            json={"text_content": "Hello"},
        )
        assert response.status_code == 422

    def test_validate_invalid_platform_returns_422(self):
        response = client.post(
            f"/api/campaigns/{VALID_CAMPAIGN_ID}/validate",
            json={"text_content": "Hello", "platform": "invalid_platform"},
        )
        assert response.status_code == 422

    @patch("src.api.v1.validation.validation_gateway")
    def test_validate_error_returns_500(self, mock_gw):
        mock_gw.validate_campaign = AsyncMock(side_effect=Exception("Unexpected"))
        response = client.post(
            f"/api/campaigns/{VALID_CAMPAIGN_ID}/validate",
            json={"text_content": "Hello", "platform": "instagram"},
        )
        assert response.status_code == 500

    @patch("src.api.v1.validation.validation_gateway")
    def test_preview_check_success(self, mock_gw):
        resp = _mock_validation_response(status="pass")
        mock_gw.validate_campaign = AsyncMock(return_value=resp)
        mock_gw.can_preview.return_value = True

        response = client.get(
            f"/api/campaigns/{VALID_CAMPAIGN_ID}/preview/check",
            params={"text_content": "Hello", "platform": "instagram"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["campaign_id"] == VALID_CAMPAIGN_ID
        assert data["can_preview"] is True
        _assert_json_content_type(response)

    @patch("src.api.v1.validation.validation_gateway")
    def test_preview_check_fails_validation(self, mock_gw):
        resp = _mock_validation_response(status="fail", text_passed=False)
        mock_gw.validate_campaign = AsyncMock(return_value=resp)
        mock_gw.can_preview.return_value = False

        response = client.get(
            f"/api/campaigns/{VALID_CAMPAIGN_ID}/preview/check",
            params={"text_content": "x" * 2500, "platform": "linkedin"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["can_preview"] is False

    def test_preview_check_missing_params_returns_422(self):
        response = client.get(f"/api/campaigns/{VALID_CAMPAIGN_ID}/preview/check")
        assert response.status_code == 422


# ===========================================================================
# 6. Workflow Engine
# ===========================================================================


class TestWorkflow:
    """POST /api/workflows, GET /api/workflows/{id} — v1 workflow stubs."""

    def test_execute_workflow_success(self):
        response = client.post(
            "/api/workflows",
            params={"workflow_type": "campaign_generation", "campaign_id": VALID_CAMPAIGN_ID},
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        _assert_json_content_type(response)

    def test_get_workflow_status_success(self):
        response = client.get(f"/api/workflows/{VALID_CAMPAIGN_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        _assert_json_content_type(response)

    def test_approve_workflow_success(self):
        response = client.post(f"/api/workflows/{VALID_CAMPAIGN_ID}/approve", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        _assert_json_content_type(response)

    def test_reject_workflow_success(self):
        response = client.post(f"/api/workflows/{VALID_CAMPAIGN_ID}/reject", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        _assert_json_content_type(response)


# ===========================================================================
# 7. Performance assertions
# ===========================================================================


class TestPerformance:
    """Response time budget tests for hot endpoints."""

    def test_health_responds_within_budget(self):
        start = time.monotonic()
        response = client.get("/api/health")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert response.status_code == 200
        assert elapsed_ms < 1000, f"Health took {elapsed_ms:.0f}ms, budget 1000ms"

    @patch(
        "src.api.v1.company.ListCompanyService",
        return_value=MagicMock(execute=MagicMock(return_value=[])),
    )
    def test_list_profiles_responds_within_budget(self, mock_cls):
        start = time.monotonic()
        response = client.get("/api/company")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert response.status_code == 200
        assert elapsed_ms < 2000, f"List took {elapsed_ms:.0f}ms, budget 2000ms"

    def test_workflow_execute_responds_within_budget(self):
        start = time.monotonic()
        response = client.post(
            "/api/workflows",
            params={"workflow_type": "test", "campaign_id": VALID_CAMPAIGN_ID},
            json={},
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        assert response.status_code == 200
        assert elapsed_ms < 1000, f"Workflow took {elapsed_ms:.0f}ms, budget 1000ms"
