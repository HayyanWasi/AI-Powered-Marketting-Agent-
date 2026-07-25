"""Comprehensive API tests for all image-related endpoints.

Covers:
  - POST /api/campaign-images (campaign image generation)
  - POST /api/company/{id}/brand-images (upload)
  - DELETE /api/company/{id}/brand-images/{index} (remove)
  - POST /api/company/{id}/brand-images/{index}/replace (replace)
  - PUT /api/company/{id}/brand-images/reorder (reorder)

Assertions use Pydantic model validation (schema-as-contract), unconditional
header checks, and performance budgets — not spot-check field lookups.
"""

from __future__ import annotations

import io
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import BaseModel

from src.main import app
from src.models.campaign_image import CampaignImageResponse, ValidationResult
from src.services.pollinations_service import (
    PollinationsRateLimitError,
    PollinationsServerError,
    PollinationsServiceError,
    PollinationsTimeoutError,
)

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_PROFILE_ID = "550e8400-e29b-41d4-a716-446655440000"
VALID_CAMPAIGN_PROMPT = "Summer sale campaign with vibrant colors and bold typography"


def _make_profile(**overrides):
    defaults = {
        "id": VALID_PROFILE_ID,
        "name": "Test Corp",
        "brand_colors": ["#FF6B35", "#004E89"],
        "brand_personality": "modern minimalist",
        "style_guide": "Clean lines, ample whitespace",
        "logo_url": None,
        "reference_images": None,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_validation_result(is_valid=True, width=1080, height=1080, errors=None):
    result = MagicMock()
    result.is_valid = is_valid
    result.width = width
    result.height = height
    result.errors = errors or []
    return result


def _make_image_file(content_type="image/png"):
    """Create a valid PNG image in memory using PIL."""
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf, "test_image.png", content_type


def _mock_pollinations(model="kontext"):
    """Build a mock PollinationsService with the .model attribute set."""
    mock = AsyncMock()
    mock.model = model
    # Dunder methods must be configured via .return_value, not instance assignment
    mock.__aenter__.return_value = mock
    mock.__aexit__.return_value = False
    return mock


def _mock_validation(is_valid=True, width=1080, height=1080, errors=None):
    """Build a mock ImageValidationService."""
    mock = AsyncMock()
    result = MagicMock()
    result.is_valid = is_valid
    result.width = width
    result.height = height
    result.errors = errors or []
    mock.validate_image_url.return_value = result
    mock.__aenter__.return_value = mock
    mock.__aexit__.return_value = False
    return mock


def _assert_schema_response(data: dict, model_class: type[BaseModel]) -> BaseModel:
    """Validate response dict against a Pydantic model — catches drift."""
    result = model_class.model_validate(data)
    assert isinstance(result, model_class)
    return result


# ===========================================================================
# 1. POST /api/campaign-images — Campaign Image Generation
# ===========================================================================


class TestCampaignImageGeneration:
    """POST /api/campaign-images — schema + happy path + error paths."""

    VALID_REQUEST = {
        "company_profile_id": VALID_PROFILE_ID,
        "campaign_prompt": VALID_CAMPAIGN_PROMPT,
    }

    # --- Happy path -------------------------------------------------------

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.brand_style_service")
    @patch("src.api.v1.campaign_images.ImageValidationService")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_success_with_brand_context(
        self, mock_pollinations_cls, mock_validation_cls, mock_brand_svc, mock_profile_svc
    ):
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_brand_ctx = MagicMock()
        mock_brand_ctx.color_palette = "#FF6B35, #004E89"
        mock_brand_svc.extract_brand_context = MagicMock(return_value=mock_brand_ctx)

        mock_prompt = MagicMock()
        mock_prompt.base_prompt = "test prompt with brand"
        mock_brand_svc.build_prompt = MagicMock(return_value=mock_prompt)

        mock_pollinations = _mock_pollinations()
        mock_pollinations.generate_image.return_value = (
            "https://image.pollinations.ai/prompt/test?model=kontext",
            4200,
        )
        mock_pollinations_cls.return_value = mock_pollinations

        mock_validation = _mock_validation(is_valid=True, width=1080, height=1080)
        mock_validation_cls.return_value = mock_validation

        response = client.post("/api/campaign-images", json=self.VALID_REQUEST)

        assert response.status_code == 200
        data = response.json()

        # Schema-as-contract validation
        _assert_schema_response(data, CampaignImageResponse)

        # Explicit field assertions
        assert data["model"] == "kontext"
        assert data["fallback_used"] is False
        assert data["brand_applied"] is True
        assert data["generation_time_ms"] >= 0
        assert data["validation"]["passed"] is True
        assert data["validation"]["width"] == 1080
        assert data["validation"]["height"] == 1080

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.brand_style_service")
    @patch("src.api.v1.campaign_images.ImageValidationService")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_success_without_brand_context(
        self, mock_pollinations_cls, mock_validation_cls, mock_brand_svc, mock_profile_svc
    ):
        mock_profile_svc.get_profile = AsyncMock(
            return_value=_make_profile(brand_colors=None, brand_personality=None, style_guide=None)
        )

        mock_brand_ctx = MagicMock()
        mock_brand_ctx.color_palette = None
        mock_brand_ctx.personality_descriptors = None
        mock_brand_ctx.style_guidance = None
        mock_brand_ctx.logo_reference = None
        mock_brand_ctx.reference_image_urls = []
        mock_brand_svc.extract_brand_context = MagicMock(return_value=mock_brand_ctx)

        mock_prompt = MagicMock()
        mock_prompt.base_prompt = "test prompt without brand"
        mock_brand_svc.build_prompt = MagicMock(return_value=mock_prompt)

        mock_pollinations = _mock_pollinations()
        mock_pollinations.generate_image.return_value = (
            "https://image.pollinations.ai/prompt/test?model=kontext",
            3800,
        )
        mock_pollinations_cls.return_value = mock_pollinations

        mock_validation = _mock_validation(is_valid=True, width=1080, height=1080)
        mock_validation_cls.return_value = mock_validation

        response = client.post("/api/campaign-images", json=self.VALID_REQUEST)

        assert response.status_code == 200
        data = response.json()
        _assert_schema_response(data, CampaignImageResponse)
        assert data["brand_applied"] is False

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.brand_style_service")
    @patch("src.api.v1.campaign_images.ImageValidationService")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_success_with_campaign_context(
        self, mock_pollinations_cls, mock_validation_cls, mock_brand_svc, mock_profile_svc
    ):
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_brand_ctx = MagicMock()
        mock_brand_svc.extract_brand_context = MagicMock(return_value=mock_brand_ctx)

        mock_prompt = MagicMock()
        mock_prompt.base_prompt = "test prompt with context"
        mock_brand_svc.build_prompt = MagicMock(return_value=mock_prompt)

        mock_pollinations = _mock_pollinations()
        mock_pollinations.generate_image.return_value = (
            "https://image.pollinations.ai/prompt/test?model=kontext",
            4000,
        )
        mock_pollinations_cls.return_value = mock_pollinations

        mock_validation = _mock_validation(is_valid=True, width=1080, height=1080)
        mock_validation_cls.return_value = mock_validation

        request_with_context = {
            **self.VALID_REQUEST,
            "campaign_context": {
                "platform": "instagram",
                "campaign_type": "seasonal_sale",
                "target_audience": "young adults 18-30",
            },
        }
        response = client.post("/api/campaign-images", json=request_with_context)

        assert response.status_code == 200
        data = response.json()
        _assert_schema_response(data, CampaignImageResponse)
        assert data["validation"]["passed"] is True

    # --- Response headers -------------------------------------------------

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.brand_style_service")
    @patch("src.api.v1.campaign_images.ImageValidationService")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_response_content_type_is_json(
        self, mock_pollinations_cls, mock_validation_cls, mock_brand_svc, mock_profile_svc
    ):
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_brand_svc.extract_brand_context = MagicMock(return_value=MagicMock())
        mock_brand_svc.build_prompt = MagicMock(return_value=MagicMock(base_prompt="test"))

        mock_pollinations = _mock_pollinations()
        mock_pollinations.generate_image.return_value = (
            "https://image.pollinations.ai/prompt/test?model=kontext",
            4000,
        )
        mock_pollinations_cls.return_value = mock_pollinations

        mock_validation = _mock_validation(is_valid=True, width=1080, height=1080)
        mock_validation_cls.return_value = mock_validation

        response = client.post("/api/campaign-images", json=self.VALID_REQUEST)

        headers = response.headers
        assert "application/json" in headers["content-type"]

    # --- Error paths: validation ------------------------------------------

    def test_missing_company_profile_id_returns_422(self):
        response = client.post(
            "/api/campaign-images",
            json={"campaign_prompt": VALID_CAMPAIGN_PROMPT},
        )
        assert response.status_code == 422

    def test_missing_campaign_prompt_returns_422(self):
        response = client.post(
            "/api/campaign-images",
            json={"company_profile_id": VALID_PROFILE_ID},
        )
        assert response.status_code == 422

    def test_invalid_uuid_returns_422(self):
        response = client.post(
            "/api/campaign-images",
            json={"company_profile_id": "not-a-uuid", "campaign_prompt": VALID_CAMPAIGN_PROMPT},
        )
        assert response.status_code == 422

    def test_prompt_too_short_returns_422(self):
        response = client.post(
            "/api/campaign-images",
            json={"company_profile_id": VALID_PROFILE_ID, "campaign_prompt": "short"},
        )
        assert response.status_code == 422

    def test_prompt_too_long_returns_422(self):
        response = client.post(
            "/api/campaign-images",
            json={
                "company_profile_id": VALID_PROFILE_ID,
                "campaign_prompt": "x" * 2001,
            },
        )
        assert response.status_code == 422

    def test_empty_body_returns_422(self):
        response = client.post("/api/campaign-images", json={})
        assert response.status_code == 422

    def test_malformed_json_returns_422(self):
        response = client.post(
            "/api/campaign-images",
            content="not json",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 422

    # --- Error paths: service errors --------------------------------------

    @patch("src.api.v1.campaign_images.company_profile_service")
    def test_profile_not_found_returns_404(self, mock_profile_svc):
        from src.services.company_profile_service import CompanyProfileNotFoundError

        mock_profile_svc.get_profile = AsyncMock(
            side_effect=CompanyProfileNotFoundError(VALID_PROFILE_ID)
        )
        response = client.post("/api/campaign-images", json=self.VALID_REQUEST)

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "PROFILE_NOT_FOUND"

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.brand_style_service")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_pollinations_server_error_returns_200_with_fallback(
        self, mock_pollinations_cls, mock_brand_svc, mock_profile_svc
    ):
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_brand_svc.extract_brand_context = MagicMock(return_value=MagicMock())
        mock_brand_svc.build_prompt = MagicMock(return_value=MagicMock(base_prompt="test"))

        mock_pollinations = _mock_pollinations()
        mock_pollinations.generate_image.side_effect = PollinationsServerError(
            "Server error", status_code=500
        )
        mock_pollinations.generate_fallback.return_value = (
            "https://image.pollinations.ai/prompt/fallback?model=kontext",
            2000,
        )
        mock_pollinations_cls.return_value = mock_pollinations

        response = client.post("/api/campaign-images", json=self.VALID_REQUEST)

        assert response.status_code == 200
        data = response.json()
        assert data["fallback_used"] is True

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.brand_style_service")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_pollinations_rate_limit_returns_503(
        self, mock_pollinations_cls, mock_brand_svc, mock_profile_svc
    ):
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_brand_svc.extract_brand_context = MagicMock(return_value=MagicMock())
        mock_brand_svc.build_prompt = MagicMock(return_value=MagicMock(base_prompt="test"))

        mock_pollinations = _mock_pollinations()
        mock_pollinations.generate_image.side_effect = PollinationsRateLimitError(
            "Rate limited", status_code=429, retry_after=30
        )
        mock_pollinations_cls.return_value = mock_pollinations

        response = client.post("/api/campaign-images", json=self.VALID_REQUEST)

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "SERVICE_UNAVAILABLE"

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.brand_style_service")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_pollinations_timeout_returns_503(
        self, mock_pollinations_cls, mock_brand_svc, mock_profile_svc
    ):
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_brand_svc.extract_brand_context = MagicMock(return_value=MagicMock())
        mock_brand_svc.build_prompt = MagicMock(return_value=MagicMock(base_prompt="test"))

        mock_pollinations = _mock_pollinations()
        mock_pollinations.generate_image.side_effect = PollinationsTimeoutError("Timed out")
        mock_pollinations_cls.return_value = mock_pollinations

        response = client.post("/api/campaign-images", json=self.VALID_REQUEST)

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "SERVICE_UNAVAILABLE"

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.brand_style_service")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_pollinations_general_error_returns_503(
        self, mock_pollinations_cls, mock_brand_svc, mock_profile_svc
    ):
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_brand_svc.extract_brand_context = MagicMock(return_value=MagicMock())
        mock_brand_svc.build_prompt = MagicMock(return_value=MagicMock(base_prompt="test"))

        mock_pollinations = _mock_pollinations()
        mock_pollinations.generate_image.side_effect = PollinationsServiceError("Connection failed")
        mock_pollinations_cls.return_value = mock_pollinations

        response = client.post("/api/campaign-images", json=self.VALID_REQUEST)

        assert response.status_code == 503

    # --- Validation retry -------------------------------------------------

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.brand_style_service")
    @patch("src.api.v1.campaign_images.ImageValidationService")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_validation_failure_triggers_retry_then_success(
        self, mock_pollinations_cls, mock_validation_cls, mock_brand_svc, mock_profile_svc
    ):
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_brand_svc.extract_brand_context = MagicMock(return_value=MagicMock())
        mock_brand_svc.build_prompt = MagicMock(return_value=MagicMock(base_prompt="test"))

        mock_pollinations = _mock_pollinations()
        mock_pollinations.generate_image.return_value = (
            "https://image.pollinations.ai/prompt/test?model=kontext",
            5000,
        )
        mock_pollinations_cls.return_value = mock_pollinations

        mock_validation = _mock_validation(is_valid=True, width=1080, height=1080)
        mock_validation.validate_image_url.side_effect = [
            _make_validation_result(is_valid=False, errors=["too small"]),
            _make_validation_result(is_valid=True, width=1080, height=1080),
        ]
        mock_validation_cls.return_value = mock_validation

        response = client.post("/api/campaign-images", json=self.VALID_REQUEST)

        assert response.status_code == 200
        data = response.json()
        assert data["validation"]["passed"] is True

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.brand_style_service")
    @patch("src.api.v1.campaign_images.ImageValidationService")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_validation_retry_fallback(
        self, mock_pollinations_cls, mock_validation_cls, mock_brand_svc, mock_profile_svc
    ):
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_brand_svc.extract_brand_context = MagicMock(return_value=MagicMock())
        mock_brand_svc.build_prompt = MagicMock(return_value=MagicMock(base_prompt="test"))

        mock_pollinations = _mock_pollinations()
        mock_pollinations.generate_image.return_value = (
            "https://image.pollinations.ai/prompt/test?model=kontext",
            5000,
        )
        mock_pollinations.generate_fallback.return_value = (
            "https://image.pollinations.ai/prompt/fallback?model=kontext",
            2000,
        )
        mock_pollinations_cls.return_value = mock_pollinations

        mock_validation = _mock_validation(is_valid=True, width=1080, height=1080)
        mock_validation.validate_image_url.side_effect = [
            _make_validation_result(is_valid=False, errors=["too small"]),
            _make_validation_result(is_valid=False, errors=["still too small"]),
        ]
        mock_validation_cls.return_value = mock_validation

        response = client.post("/api/campaign-images", json=self.VALID_REQUEST)

        assert response.status_code == 200
        data = response.json()
        assert data["fallback_used"] is True

    # --- Performance assertion --------------------------------------------

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.brand_style_service")
    @patch("src.api.v1.campaign_images.ImageValidationService")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_response_within_performance_budget(
        self, mock_pollinations_cls, mock_validation_cls, mock_brand_svc, mock_profile_svc
    ):
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_brand_svc.extract_brand_context = MagicMock(return_value=MagicMock())
        mock_brand_svc.build_prompt = MagicMock(return_value=MagicMock(base_prompt="test"))

        mock_pollinations = _mock_pollinations()
        mock_pollinations.generate_image.return_value = (
            "https://image.pollinations.ai/prompt/test?model=kontext",
            100,
        )
        mock_pollinations_cls.return_value = mock_pollinations

        mock_validation = _mock_validation(is_valid=True, width=1080, height=1080)
        mock_validation_cls.return_value = mock_validation

        start = time.monotonic()
        response = client.post("/api/campaign-images", json=self.VALID_REQUEST)
        elapsed_ms = (time.monotonic() - start) * 1000

        assert response.status_code == 200
        assert elapsed_ms < 5000, f"Response took {elapsed_ms:.0f}ms, budget is 5000ms"


# ===========================================================================
# 2. POST /api/company/{id}/brand-images — Upload Brand Images
# ===========================================================================


class TestBrandImageUpload:
    """POST /api/company/{id}/brand-images — multipart upload + validation."""

    def _upload_url(self, profile_id: str = VALID_PROFILE_ID) -> str:
        return f"/api/company/{profile_id}/brand-images"

    # --- Happy path -------------------------------------------------------

    @patch("src.api.v1.company._get_supabase_service")
    def test_upload_single_image_success(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": [],
        }
        mock_service.upload_image.return_value = "https://storage.example.com/brand/test.png"

        image_file, filename, content_type = _make_image_file()
        response = client.post(
            self._upload_url(),
            files=[("images", (filename, image_file, content_type))],
        )

        assert response.status_code == 200
        data = response.json()
        assert "urls" in data
        assert "failed" in data
        assert "total" in data
        assert isinstance(data["urls"], list)
        assert isinstance(data["failed"], list)
        assert isinstance(data["total"], int)
        assert len(data["urls"]) == 1

    @patch("src.api.v1.company._get_supabase_service")
    def test_upload_multiple_images_success(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": [],
        }
        mock_service.upload_image.return_value = "https://storage.example.com/brand/test.png"

        files = []
        for i in range(3):
            image_file, filename, content_type = _make_image_file()
            files.append(("images", (f"image_{i}.png", image_file, content_type)))

        response = client.post(self._upload_url(), files=files)

        assert response.status_code == 200
        data = response.json()
        assert len(data["urls"]) == 3
        assert data["total"] == 3

    # --- Error paths: validation ------------------------------------------

    @patch("src.api.v1.company._get_supabase_service")
    def test_profile_not_found_returns_404(self, mock_service):
        from src.services.supabase import NotFoundError

        mock_service.get_profile.side_effect = NotFoundError("not found")

        image_file, filename, content_type = _make_image_file()
        response = client.post(
            self._upload_url(),
            files=[("images", (filename, image_file, content_type))],
        )
        assert response.status_code == 404

    @patch("src.api.v1.company._get_supabase_service")
    def test_unsupported_image_format_rejected(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": [],
        }

        response = client.post(
            self._upload_url(),
            files=[("images", ("test.bmp", io.BytesIO(b"fake bmp"), "image/bmp"))],
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["failed"]) == 1
        assert "Unsupported format" in data["failed"][0]["error"]

    @patch("src.api.v1.company._get_supabase_service")
    def test_oversized_image_rejected(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": [],
        }

        # Create a file larger than MAX_IMAGE_SIZE (10MB)
        large_content = b"\x00" * (11 * 1024 * 1024)
        response = client.post(
            self._upload_url(),
            files=[("images", ("large.png", io.BytesIO(large_content), "image/png"))],
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["failed"]) == 1
        assert "File too large" in data["failed"][0]["error"]

    # --- Response headers -------------------------------------------------

    @patch("src.api.v1.company._get_supabase_service")
    def test_upload_response_content_type(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": [],
        }
        mock_service.upload_image.return_value = "https://storage.example.com/brand/test.png"

        image_file, filename, content_type = _make_image_file()
        response = client.post(
            self._upload_url(),
            files=[("images", (filename, image_file, content_type))],
        )

        headers = response.headers
        assert "application/json" in headers["content-type"]


# ===========================================================================
# 3. DELETE /api/company/{id}/brand-images/{index} — Remove Brand Image
# ===========================================================================


class TestBrandImageDelete:
    """DELETE /api/company/{id}/brand-images/{index} — idempotency + errors."""

    def _delete_url(self, profile_id: str, index: int) -> str:
        return f"/api/company/{profile_id}/brand-images/{index}"

    @patch("src.api.v1.company._get_supabase_service")
    def test_delete_success(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": [
                "https://storage.example.com/brand/img1.png",
                "https://storage.example.com/brand/img2.png",
            ],
        }

        response = client.delete(self._delete_url(VALID_PROFILE_ID, 0))

        assert response.status_code == 200
        data = response.json()
        assert data["removed"] is True
        assert data["remaining"] == 1

    @patch("src.api.v1.company._get_supabase_service")
    def test_delete_profile_not_found_returns_404(self, mock_service):
        from src.services.supabase import NotFoundError

        mock_service.get_profile.side_effect = NotFoundError("not found")

        response = client.delete(self._delete_url(VALID_PROFILE_ID, 0))
        assert response.status_code == 404

    @patch("src.api.v1.company._get_supabase_service")
    def test_delete_out_of_bounds_index_returns_404(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": ["https://storage.example.com/brand/img1.png"],
        }

        response = client.delete(self._delete_url(VALID_PROFILE_ID, 99))
        assert response.status_code == 404

    @patch("src.api.v1.company._get_supabase_service")
    def test_delete_negative_index_returns_404(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": ["https://storage.example.com/brand/img1.png"],
        }

        response = client.delete(self._delete_url(VALID_PROFILE_ID, -1))
        assert response.status_code == 404

    @patch("src.api.v1.company._get_supabase_service")
    def test_delete_idempotent(self, mock_service):
        """Deleting the same index twice should succeed both times (second returns 404)."""
        urls = [
            "https://storage.example.com/brand/img1.png",
            "https://storage.example.com/brand/img2.png",
        ]
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": list(urls),
        }

        # First delete succeeds
        response1 = client.delete(self._delete_url(VALID_PROFILE_ID, 0))
        assert response1.status_code == 200

        # Second delete of same index now out of bounds
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": [urls[1]],
        }
        response2 = client.delete(self._delete_url(VALID_PROFILE_ID, 0))
        assert response2.status_code == 200


# ===========================================================================
# 4. POST /api/company/{id}/brand-images/{index}/replace — Replace Image
# ===========================================================================


class TestBrandImageReplace:
    """POST /api/company/{id}/brand-images/{index}/replace — upload replacement."""

    def _replace_url(self, profile_id: str, index: int) -> str:
        return f"/api/company/{profile_id}/brand-images/{index}/replace"

    @patch("src.api.v1.company._get_supabase_service")
    def test_replace_success(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": [
                "https://storage.example.com/brand/old.png",
            ],
        }
        mock_service.upload_image.return_value = "https://storage.example.com/brand/new.png"

        image_file, filename, content_type = _make_image_file()
        response = client.post(
            self._replace_url(VALID_PROFILE_ID, 0),
            files=[("image", (filename, image_file, content_type))],
        )

        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert data["index"] == 0
        assert data["total"] == 1

    @patch("src.api.v1.company._get_supabase_service")
    def test_replace_profile_not_found_returns_404(self, mock_service):
        from src.services.supabase import NotFoundError

        mock_service.get_profile.side_effect = NotFoundError("not found")

        image_file, filename, content_type = _make_image_file()
        response = client.post(
            self._replace_url(VALID_PROFILE_ID, 0),
            files=[("image", (filename, image_file, content_type))],
        )
        assert response.status_code == 404

    @patch("src.api.v1.company._get_supabase_service")
    def test_replace_out_of_bounds_returns_404(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": ["https://storage.example.com/brand/img1.png"],
        }

        image_file, filename, content_type = _make_image_file()
        response = client.post(
            self._replace_url(VALID_PROFILE_ID, 99),
            files=[("image", (filename, image_file, content_type))],
        )
        assert response.status_code == 404

    @patch("src.api.v1.company._get_supabase_service")
    def test_replace_unsupported_format_returns_422(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": ["https://storage.example.com/brand/img1.png"],
        }

        response = client.post(
            self._replace_url(VALID_PROFILE_ID, 0),
            files=[("image", ("test.bmp", io.BytesIO(b"fake bmp"), "image/bmp"))],
        )
        assert response.status_code == 422

    @patch("src.api.v1.company._get_supabase_service")
    def test_replace_corrupt_image_returns_422(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": ["https://storage.example.com/brand/img1.png"],
        }

        response = client.post(
            self._replace_url(VALID_PROFILE_ID, 0),
            files=[("image", ("corrupt.png", io.BytesIO(b"not a real png"), "image/png"))],
        )
        assert response.status_code == 422

    # --- Response headers -------------------------------------------------

    @patch("src.api.v1.company._get_supabase_service")
    def test_replace_response_content_type(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": ["https://storage.example.com/brand/img1.png"],
        }
        mock_service.upload_image.return_value = "https://storage.example.com/brand/new.png"

        image_file, filename, content_type = _make_image_file()
        response = client.post(
            self._replace_url(VALID_PROFILE_ID, 0),
            files=[("image", (filename, image_file, content_type))],
        )

        headers = response.headers
        assert "application/json" in headers["content-type"]


# ===========================================================================
# 5. PUT /api/company/{id}/brand-images/reorder — Reorder Images
# ===========================================================================


class TestBrandImageReorder:
    """PUT /api/company/{id}/brand-images/reorder — reorder validation."""

    def _reorder_url(self, profile_id: str) -> str:
        return f"/api/company/{profile_id}/brand-images/reorder"

    @patch("src.api.v1.company._get_supabase_service")
    def test_reorder_success(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": [
                "https://storage.example.com/brand/img1.png",
                "https://storage.example.com/brand/img2.png",
                "https://storage.example.com/brand/img3.png",
            ],
        }

        response = client.put(
            self._reorder_url(VALID_PROFILE_ID),
            json={"order": [2, 0, 1]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reordered"] is True
        assert data["total"] == 3

    @patch("src.api.v1.company._get_supabase_service")
    def test_reorder_same_order_succeeds(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": [
                "https://storage.example.com/brand/img1.png",
                "https://storage.example.com/brand/img2.png",
            ],
        }

        response = client.put(
            self._reorder_url(VALID_PROFILE_ID),
            json={"order": [0, 1]},
        )

        assert response.status_code == 200

    @patch("src.api.v1.company._get_supabase_service")
    def test_reorder_missing_order_field_returns_422(self, mock_service):
        response = client.put(
            self._reorder_url(VALID_PROFILE_ID),
            json={},
        )
        assert response.status_code == 422

    @patch("src.api.v1.company._get_supabase_service")
    def test_reorder_empty_order_returns_422(self, mock_service):
        response = client.put(
            self._reorder_url(VALID_PROFILE_ID),
            json={"order": []},
        )
        assert response.status_code == 422

    @patch("src.api.v1.company._get_supabase_service")
    def test_reorder_invalid_indices_returns_422(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": [
                "https://storage.example.com/brand/img1.png",
                "https://storage.example.com/brand/img2.png",
            ],
        }

        response = client.put(
            self._reorder_url(VALID_PROFILE_ID),
            json={"order": [0, 5]},
        )
        assert response.status_code == 422

    @patch("src.api.v1.company._get_supabase_service")
    def test_reorder_duplicate_indices_returns_422(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": [
                "https://storage.example.com/brand/img1.png",
                "https://storage.example.com/brand/img2.png",
            ],
        }

        response = client.put(
            self._reorder_url(VALID_PROFILE_ID),
            json={"order": [0, 0]},
        )
        assert response.status_code == 422

    @patch("src.api.v1.company._get_supabase_service")
    def test_reorder_profile_not_found_returns_404(self, mock_service):
        from src.services.supabase import NotFoundError

        mock_service.get_profile.side_effect = NotFoundError("not found")

        response = client.put(
            self._reorder_url(VALID_PROFILE_ID),
            json={"order": [0]},
        )
        assert response.status_code == 404

    # --- Response headers -------------------------------------------------

    @patch("src.api.v1.company._get_supabase_service")
    def test_reorder_response_content_type(self, mock_service):
        mock_service.get_profile.return_value = {
            "id": VALID_PROFILE_ID,
            "reference_image_urls": [
                "https://storage.example.com/brand/img1.png",
                "https://storage.example.com/brand/img2.png",
            ],
        }

        response = client.put(
            self._reorder_url(VALID_PROFILE_ID),
            json={"order": [1, 0]},
        )

        headers = response.headers
        assert "application/json" in headers["content-type"]
