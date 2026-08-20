from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app
from src.models.campaign_image import CompanyProfile
from src.services.pollinations_service import (
    PollinationsRateLimitError,
    PollinationsServerError,
    PollinationsServiceError,
    PollinationsTimeoutError,
)

client = TestClient(app)


def _make_profile(**overrides) -> CompanyProfile:
    defaults = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Test Corp",
        "brand_colors": ["#FF6B35", "#004E89"],
        "brand_personality": "modern minimalist",
        "style_guide": "Clean lines, ample whitespace",
        "logo_url": None,
        "reference_images": None,
    }
    defaults.update(overrides)
    return CompanyProfile(**defaults)


VALID_REQUEST = {
    "company_profile_id": "550e8400-e29b-41d4-a716-446655440000",
    "campaign_prompt": "Summer sale campaign with vibrant colors",
}


class TestGenerateCampaignImageSuccess:
    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.ImageValidationService")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_success_with_brand(
        self, mock_pollinations_cls, mock_validation_cls, mock_profile_svc
    ) -> None:
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_pollinations = AsyncMock()
        mock_pollinations.generate_image = AsyncMock(
            return_value=("https://image.pollinations.ai/prompt/test?model=kontext", 5000)
        )
        mock_pollinations.__aenter__ = AsyncMock(return_value=mock_pollinations)
        mock_pollinations.__aexit__ = AsyncMock(return_value=False)
        mock_pollinations_cls.return_value = mock_pollinations

        mock_validation = AsyncMock()
        validation_result = MagicMock()
        validation_result.is_valid = True
        validation_result.width = 1080
        validation_result.height = 1080
        mock_validation.validate_image_url = AsyncMock(return_value=validation_result)
        mock_validation.__aenter__ = AsyncMock(return_value=mock_validation)
        mock_validation.__aexit__ = AsyncMock(return_value=False)
        mock_validation_cls.return_value = mock_validation

        response = client.post("/api/campaign-images", json=VALID_REQUEST)

        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "kontext"
        assert data["fallback_used"] is False
        assert data["brand_applied"] is True
        assert data["validation"]["passed"] is True

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.ImageValidationService")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_success_without_brand(
        self, mock_pollinations_cls, mock_validation_cls, mock_profile_svc
    ) -> None:
        mock_profile_svc.get_profile = AsyncMock(
            return_value=_make_profile(brand_colors=None, brand_personality=None, style_guide=None)
        )

        mock_pollinations = AsyncMock()
        mock_pollinations.generate_image = AsyncMock(
            return_value=("https://image.pollinations.ai/prompt/test?model=kontext", 5000)
        )
        mock_pollinations.__aenter__ = AsyncMock(return_value=mock_pollinations)
        mock_pollinations.__aexit__ = AsyncMock(return_value=False)
        mock_pollinations_cls.return_value = mock_pollinations

        mock_validation = AsyncMock()
        validation_result = MagicMock()
        validation_result.is_valid = True
        validation_result.width = 1080
        validation_result.height = 1080
        mock_validation.validate_image_url = AsyncMock(return_value=validation_result)
        mock_validation.__aenter__ = AsyncMock(return_value=mock_validation)
        mock_validation.__aexit__ = AsyncMock(return_value=False)
        mock_validation_cls.return_value = mock_validation

        response = client.post("/api/campaign-images", json=VALID_REQUEST)

        assert response.status_code == 200
        data = response.json()
        assert data["brand_applied"] is False


class TestGenerateCampaignImageErrors:
    @patch("src.api.v1.campaign_images.company_profile_service")
    def test_profile_not_found(self, mock_profile_svc) -> None:
        from src.services.company_profile_service import CompanyProfileNotFoundError

        mock_profile_svc.get_profile = AsyncMock(
            side_effect=CompanyProfileNotFoundError("550e8400-e29b-41d4-a716-446655440000")
        )

        response = client.post("/api/campaign-images", json=VALID_REQUEST)

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "profile_not_found"

    def test_invalid_request_short_prompt(self) -> None:
        response = client.post(
            "/api/campaign-images",
            json={
                "company_profile_id": "550e8400-e29b-41d4-a716-446655440000",
                "campaign_prompt": "short",
            },
        )
        assert response.status_code == 422

    def test_missing_required_field(self) -> None:
        response = client.post(
            "/api/campaign-images",
            json={
                "campaign_prompt": "This is a valid campaign prompt with enough characters",
            },
        )
        assert response.status_code == 422

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_pollinations_server_error_returns_fallback(
        self, mock_pollinations_cls, mock_profile_svc
    ) -> None:
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_pollinations = AsyncMock()
        mock_pollinations.generate_image = AsyncMock(
            side_effect=PollinationsServerError("Server error", status_code=500)
        )
        mock_pollinations.generate_fallback = AsyncMock(
            return_value=("https://image.pollinations.ai/prompt/fallback?model=kontext", 3000)
        )
        mock_pollinations.__aenter__ = AsyncMock(return_value=mock_pollinations)
        mock_pollinations.__aexit__ = AsyncMock(return_value=False)
        mock_pollinations_cls.return_value = mock_pollinations

        response = client.post("/api/campaign-images", json=VALID_REQUEST)

        assert response.status_code == 200
        data = response.json()
        assert data["fallback_used"] is True

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_pollinations_rate_limit_returns_503(
        self, mock_pollinations_cls, mock_profile_svc
    ) -> None:
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_pollinations = AsyncMock()
        mock_pollinations.generate_image = AsyncMock(
            side_effect=PollinationsRateLimitError("Rate limited", status_code=429, retry_after=30)
        )
        mock_pollinations.__aenter__ = AsyncMock(return_value=mock_pollinations)
        mock_pollinations.__aexit__ = AsyncMock(return_value=False)
        mock_pollinations_cls.return_value = mock_pollinations

        response = client.post("/api/campaign-images", json=VALID_REQUEST)

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "service_unavailable"

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_pollinations_timeout_returns_503(
        self, mock_pollinations_cls, mock_profile_svc
    ) -> None:
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_pollinations = AsyncMock()
        mock_pollinations.generate_image = AsyncMock(
            side_effect=PollinationsTimeoutError("Timed out")
        )
        mock_pollinations.__aenter__ = AsyncMock(return_value=mock_pollinations)
        mock_pollinations.__aexit__ = AsyncMock(return_value=False)
        mock_pollinations_cls.return_value = mock_pollinations

        response = client.post("/api/campaign-images", json=VALID_REQUEST)

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "service_unavailable"

    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_pollinations_general_error_returns_503(
        self, mock_pollinations_cls, mock_profile_svc
    ) -> None:
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_pollinations = AsyncMock()
        mock_pollinations.generate_image = AsyncMock(
            side_effect=PollinationsServiceError("Connection failed")
        )
        mock_pollinations.__aenter__ = AsyncMock(return_value=mock_pollinations)
        mock_pollinations.__aexit__ = AsyncMock(return_value=False)
        mock_pollinations_cls.return_value = mock_pollinations

        response = client.post("/api/campaign-images", json=VALID_REQUEST)

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "service_unavailable"


class TestValidationRetry:
    @patch("src.api.v1.campaign_images.company_profile_service")
    @patch("src.api.v1.campaign_images.ImageValidationService")
    @patch("src.api.v1.campaign_images.PollinationsService")
    def test_validation_failure_triggers_retry_then_success(
        self, mock_pollinations_cls, mock_validation_cls, mock_profile_svc
    ) -> None:
        mock_profile_svc.get_profile = AsyncMock(return_value=_make_profile())

        mock_pollinations = AsyncMock()
        mock_pollinations.generate_image = AsyncMock(
            return_value=("https://image.pollinations.ai/prompt/test?model=kontext", 5000)
        )
        mock_pollinations.__aenter__ = AsyncMock(return_value=mock_pollinations)
        mock_pollinations.__aexit__ = AsyncMock(return_value=False)
        mock_pollinations_cls.return_value = mock_pollinations

        fail_result = MagicMock()
        fail_result.is_valid = False
        fail_result.errors = ["too small"]
        pass_result = MagicMock()
        pass_result.is_valid = True
        pass_result.width = 1080
        pass_result.height = 1080

        mock_validation = AsyncMock()
        mock_validation.validate_image_url = AsyncMock(side_effect=[fail_result, pass_result])
        mock_validation.__aenter__ = AsyncMock(return_value=mock_validation)
        mock_validation.__aexit__ = AsyncMock(return_value=False)
        mock_validation_cls.return_value = mock_validation

        response = client.post("/api/campaign-images", json=VALID_REQUEST)

        assert response.status_code == 200
        data = response.json()
        assert data["validation"]["passed"] is True
