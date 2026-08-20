"""Tests for the validation service."""

from unittest.mock import AsyncMock

import pytest

from src.models.platform import Platform
from src.models.validation import ValidationRequest, ValidationStatus
from src.services.image_validation_service import ImageValidationService, ValidationResult
from src.services.validation_service import ValidationService


@pytest.fixture
def mock_image_service() -> AsyncMock:
    """Create a mock ImageValidationService."""
    service = AsyncMock(spec=ImageValidationService)
    service.validate_image_url = AsyncMock()
    service.__aenter__ = AsyncMock(return_value=service)
    service.__aexit__ = AsyncMock(return_value=None)
    return service


@pytest.fixture
def validation_service(mock_image_service: AsyncMock) -> ValidationService:
    """Create a ValidationService with mocked image service."""
    return ValidationService(image_validation_service=mock_image_service)


def _make_valid_image_result() -> ValidationResult:
    """Create a valid image validation result."""
    return ValidationResult(
        is_valid=True,
        width=1080,
        height=1080,
        content_type="image/png",
        errors=[],
        url_accessible=True,
    )


def _make_invalid_image_result(errors: list[str] | None = None) -> ValidationResult:
    """Create an invalid image validation result."""
    return ValidationResult(
        is_valid=False,
        width=0,
        height=0,
        content_type="",
        errors=errors or ["Image resolution below minimum"],
        url_accessible=True,
    )


class TestValidationService:
    """Tests for ValidationService.validate()."""

    @pytest.mark.asyncio
    async def test_valid_text_no_image(
        self,
        validation_service: ValidationService,
    ) -> None:
        request = ValidationRequest(
            campaign_id="test-123",
            text_content="A" * 1000,
            image_url=None,
            platform=Platform.LINKEDIN,
        )

        result = await validation_service.validate(request)

        assert result.status == ValidationStatus.PASS
        assert result.text_result.passed is True
        assert result.image_result.passed is True
        assert result.to_response().can_preview is True

    @pytest.mark.asyncio
    async def test_text_exceeds_limit(
        self,
        validation_service: ValidationService,
    ) -> None:
        request = ValidationRequest(
            campaign_id="test-456",
            text_content="B" * 5000,
            image_url=None,
            platform=Platform.LINKEDIN,
        )

        result = await validation_service.validate(request)

        assert result.status == ValidationStatus.FAIL
        assert result.text_result.passed is False
        assert len(result.text_result.violations) == 1
        assert result.to_response().can_preview is False

    @pytest.mark.asyncio
    async def test_valid_text_with_valid_image(
        self,
        validation_service: ValidationService,
        mock_image_service: AsyncMock,
    ) -> None:
        mock_image_service.validate_image_url.return_value = _make_valid_image_result()

        request = ValidationRequest(
            campaign_id="test-789",
            text_content="C" * 500,
            image_url="https://example.com/image.png",
            platform=Platform.INSTAGRAM,
        )

        result = await validation_service.validate(request)

        assert result.status == ValidationStatus.PASS
        assert result.text_result.passed is True
        assert result.image_result.passed is True
        assert result.image_result.width == 1080
        assert result.to_response().can_preview is True

    @pytest.mark.asyncio
    async def test_valid_text_with_invalid_image(
        self,
        validation_service: ValidationService,
        mock_image_service: AsyncMock,
    ) -> None:
        mock_image_service.validate_image_url.return_value = _make_invalid_image_result()

        request = ValidationRequest(
            campaign_id="test-img-fail",
            text_content="D" * 500,
            image_url="https://example.com/small.png",
            platform=Platform.INSTAGRAM,
        )

        result = await validation_service.validate(request)

        assert result.status == ValidationStatus.FAIL
        assert result.text_result.passed is True
        assert result.image_result.passed is False
        assert len(result.image_result.violations) > 0
        assert result.to_response().can_preview is False

    @pytest.mark.asyncio
    async def test_both_text_and_image_fail(
        self,
        validation_service: ValidationService,
        mock_image_service: AsyncMock,
    ) -> None:
        mock_image_service.validate_image_url.return_value = _make_invalid_image_result()

        request = ValidationRequest(
            campaign_id="test-both-fail",
            text_content="E" * 10000,
            image_url="https://example.com/bad.png",
            platform=Platform.INSTAGRAM,
        )

        result = await validation_service.validate(request)

        assert result.status == ValidationStatus.FAIL
        assert result.text_result.passed is False
        assert result.image_result.passed is False
        assert result.to_response().can_preview is False

    @pytest.mark.asyncio
    async def test_image_validation_exception(
        self,
        validation_service: ValidationService,
        mock_image_service: AsyncMock,
    ) -> None:
        mock_image_service.validate_image_url.side_effect = Exception("Network error")

        request = ValidationRequest(
            campaign_id="test-img-err",
            text_content="F" * 100,
            image_url="https://example.com/error.png",
            platform=Platform.FACEBOOK,
        )

        result = await validation_service.validate(request)

        assert result.status == ValidationStatus.FAIL
        assert result.image_result.passed is False
        assert len(result.image_result.violations) == 1
        assert "Network error" in result.image_result.violations[0].message

    @pytest.mark.asyncio
    async def test_facebook_platform(
        self,
        validation_service: ValidationService,
    ) -> None:
        request = ValidationRequest(
            campaign_id="test-fb",
            text_content="G" * 1000,
            image_url=None,
            platform=Platform.FACEBOOK,
        )

        result = await validation_service.validate(request)

        assert result.status == ValidationStatus.PASS
        assert result.text_result.character_limit == 63206
        assert result.to_response().can_preview is True

    @pytest.mark.asyncio
    async def test_image_result_includes_dimensions(
        self,
        validation_service: ValidationService,
        mock_image_service: AsyncMock,
    ) -> None:
        mock_image_service.validate_image_url.return_value = ValidationResult(
            is_valid=True,
            width=1920,
            height=1080,
            content_type="image/jpeg",
            errors=[],
            url_accessible=True,
        )

        request = ValidationRequest(
            campaign_id="test-dims",
            text_content="H" * 200,
            image_url="https://example.com/wide.png",
            platform=Platform.LINKEDIN,
        )

        result = await validation_service.validate(request)

        assert result.image_result.width == 1920
        assert result.image_result.height == 1080
        assert result.image_result.content_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_validated_at_is_set(
        self,
        validation_service: ValidationService,
    ) -> None:
        request = ValidationRequest(
            campaign_id="test-time",
            text_content="I" * 100,
            image_url=None,
            platform=Platform.LINKEDIN,
        )

        result = await validation_service.validate(request)

        assert result.validated_at != ""
        assert "T" in result.validated_at  # ISO format contains T separator
