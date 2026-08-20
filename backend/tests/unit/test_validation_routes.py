"""Tests for validation API routes."""

import os
from unittest.mock import AsyncMock, patch

import pytest

# Set required env vars before any imports that trigger Settings
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

from fastapi.testclient import TestClient

from src.models.platform import Platform
from src.models.validation import (
    TextValidationResultInternal,
    ValidationResponse,
    ValidationResultInternal,
    ValidationStatus,
)


@pytest.fixture
def client() -> TestClient:
    """Create a test client with mocked gateway."""
    with patch("src.api.v1.validation.validation_gateway") as mock_gw:
        mock_gw.validate_campaign = AsyncMock()
        mock_gw.can_preview = lambda r: r.can_preview
        from src.main import app

        yield TestClient(app)


def _make_pass_response(campaign_id: str = "test-123") -> ValidationResponse:
    """Create a passing validation response."""
    result = ValidationResultInternal(
        campaign_id=campaign_id,
        platform=Platform.LINKEDIN,
        status=ValidationStatus.PASS,
    )
    return result.to_response()


def _make_fail_response(campaign_id: str = "test-456") -> ValidationResponse:
    """Create a failing validation response."""
    result = ValidationResultInternal(
        campaign_id=campaign_id,
        platform=Platform.LINKEDIN,
        status=ValidationStatus.FAIL,
        text_result=TextValidationResultInternal(
            passed=False,
            character_count=5000,
            character_limit=3000,
        ),
    )
    return result.to_response()


class TestValidateCampaignEndpoint:
    """Tests for POST /api/campaigns/{campaign_id}/validate."""

    def test_validate_campaign_success(self, client: TestClient) -> None:
        with patch("src.api.v1.validation.validation_gateway") as mock_gw:
            mock_gw.validate_campaign = AsyncMock(return_value=_make_pass_response())
            mock_gw.can_preview = lambda r: r.can_preview

            response = client.post(
                "/api/campaigns/test-123/validate",
                json={
                    "text_content": "Hello world",
                    "platform": "linkedin",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["campaign_id"] == "test-123"
            assert data["status"] == "pass"
            assert data["can_preview"] is True

    def test_validate_campaign_with_image(self, client: TestClient) -> None:
        with patch("src.api.v1.validation.validation_gateway") as mock_gw:
            mock_gw.validate_campaign = AsyncMock(return_value=_make_pass_response())
            mock_gw.can_preview = lambda r: r.can_preview

            response = client.post(
                "/api/campaigns/test-img/validate",
                json={
                    "text_content": "Post with image",
                    "platform": "instagram",
                    "image_url": "https://example.com/image.png",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["can_preview"] is True

    def test_validate_campaign_failure(self, client: TestClient) -> None:
        with patch("src.api.v1.validation.validation_gateway") as mock_gw:
            mock_gw.validate_campaign = AsyncMock(return_value=_make_fail_response())
            mock_gw.can_preview = lambda r: r.can_preview

            response = client.post(
                "/api/campaigns/test-456/validate",
                json={
                    "text_content": "A" * 5000,
                    "platform": "linkedin",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "fail"
            assert data["can_preview"] is False

    def test_validate_campaign_missing_text(self, client: TestClient) -> None:
        response = client.post(
            "/api/campaigns/test-missing/validate",
            json={
                "platform": "linkedin",
            },
        )

        assert response.status_code == 422

    def test_validate_campaign_invalid_platform(self, client: TestClient) -> None:
        response = client.post(
            "/api/campaigns/test-invalid/validate",
            json={
                "text_content": "Hello",
                "platform": "tiktok",
            },
        )

        assert response.status_code == 422

    def test_validate_campaign_exception(self, client: TestClient) -> None:
        with patch("src.api.v1.validation.validation_gateway") as mock_gw:
            mock_gw.validate_campaign = AsyncMock(side_effect=Exception("Unexpected"))

            response = client.post(
                "/api/campaigns/test-err/validate",
                json={
                    "text_content": "Hello",
                    "platform": "linkedin",
                },
            )

            assert response.status_code == 500


class TestPreviewCheckEndpoint:
    """Tests for GET /api/campaigns/{campaign_id}/preview/check."""

    def test_preview_check_passes(self, client: TestClient) -> None:
        with patch("src.api.v1.validation.validation_gateway") as mock_gw:
            mock_gw.validate_campaign = AsyncMock(return_value=_make_pass_response())
            mock_gw.can_preview = lambda r: r.can_preview

            response = client.get(
                "/api/campaigns/test-123/preview/check",
                params={
                    "text_content": "Hello",
                    "platform": "linkedin",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["can_preview"] is True
            assert data["status"] == "pass"
            assert "passed" in data["message"].lower()

    def test_preview_check_fails(self, client: TestClient) -> None:
        with patch("src.api.v1.validation.validation_gateway") as mock_gw:
            mock_gw.validate_campaign = AsyncMock(return_value=_make_fail_response())
            mock_gw.can_preview = lambda r: r.can_preview

            response = client.get(
                "/api/campaigns/test-456/preview/check",
                params={
                    "text_content": "A" * 5000,
                    "platform": "linkedin",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["can_preview"] is False
            assert data["status"] == "fail"
            assert "failed" in data["message"].lower()

    def test_preview_check_with_image(self, client: TestClient) -> None:
        with patch("src.api.v1.validation.validation_gateway") as mock_gw:
            mock_gw.validate_campaign = AsyncMock(return_value=_make_pass_response())
            mock_gw.can_preview = lambda r: r.can_preview

            response = client.get(
                "/api/campaigns/test-img/preview/check",
                params={
                    "text_content": "Hello",
                    "platform": "instagram",
                    "image_url": "https://example.com/image.png",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["can_preview"] is True
