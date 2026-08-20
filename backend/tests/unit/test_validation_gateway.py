"""Tests for the validation gateway."""

from unittest.mock import AsyncMock

import pytest

from src.gateways.validation_gateway import ValidationGateway
from src.models.platform import Platform
from src.models.validation import (
    ValidationResponse,
    ValidationResultInternal,
    ValidationStatus,
)


@pytest.fixture
def mock_validation_service() -> AsyncMock:
    """Create a mock ValidationService."""
    service = AsyncMock()
    service.validate = AsyncMock()
    return service


@pytest.fixture
def gateway(mock_validation_service: AsyncMock) -> ValidationGateway:
    """Create a ValidationGateway with mocked service."""
    return ValidationGateway(validation_service=mock_validation_service)


class TestValidationGateway:
    """Tests for ValidationGateway.validate_campaign()."""

    @pytest.mark.asyncio
    async def test_validate_returns_response(
        self,
        gateway: ValidationGateway,
        mock_validation_service: AsyncMock,
    ) -> None:
        result = ValidationResultInternal(
            campaign_id="gw-test-1",
            platform=Platform.LINKEDIN,
            status=ValidationStatus.PASS,
        )
        mock_validation_service.validate.return_value = result

        response = await gateway.validate_campaign(
            campaign_id="gw-test-1",
            text_content="Hello world",
            platform="linkedin",
        )

        assert isinstance(response, ValidationResponse)
        assert response.campaign_id == "gw-test-1"
        assert response.status == ValidationStatus.PASS
        assert response.can_preview is True

    @pytest.mark.asyncio
    async def test_validate_passes_request_to_service(
        self,
        gateway: ValidationGateway,
        mock_validation_service: AsyncMock,
    ) -> None:
        result = ValidationResultInternal(
            campaign_id="gw-test-2",
            platform=Platform.INSTAGRAM,
            status=ValidationStatus.PASS,
        )
        mock_validation_service.validate.return_value = result

        await gateway.validate_campaign(
            campaign_id="gw-test-2",
            text_content="Test content",
            platform="instagram",
            image_url="https://example.com/img.png",
        )

        call_args = mock_validation_service.validate.call_args[0][0]
        assert call_args.campaign_id == "gw-test-2"
        assert call_args.text_content == "Test content"
        assert call_args.platform == Platform.INSTAGRAM
        assert call_args.image_url == "https://example.com/img.png"

    @pytest.mark.asyncio
    async def test_can_preview_true(
        self,
        gateway: ValidationGateway,
        mock_validation_service: AsyncMock,
    ) -> None:
        result = ValidationResultInternal(
            campaign_id="gw-preview",
            platform=Platform.LINKEDIN,
            status=ValidationStatus.PASS,
        )
        mock_validation_service.validate.return_value = result

        response = await gateway.validate_campaign(
            campaign_id="gw-preview",
            text_content="OK",
            platform="linkedin",
        )

        assert gateway.can_preview(response) is True

    @pytest.mark.asyncio
    async def test_can_preview_false(
        self,
        gateway: ValidationGateway,
        mock_validation_service: AsyncMock,
    ) -> None:
        result = ValidationResultInternal(
            campaign_id="gw-no-preview",
            platform=Platform.LINKEDIN,
            status=ValidationStatus.FAIL,
        )
        mock_validation_service.validate.return_value = result

        response = await gateway.validate_campaign(
            campaign_id="gw-no-preview",
            text_content="Too long content here",
            platform="linkedin",
        )

        assert gateway.can_preview(response) is False

    @pytest.mark.asyncio
    async def test_platform_case_insensitive(
        self,
        gateway: ValidationGateway,
        mock_validation_service: AsyncMock,
    ) -> None:
        result = ValidationResultInternal(
            campaign_id="gw-case",
            platform=Platform.LINKEDIN,
            status=ValidationStatus.PASS,
        )
        mock_validation_service.validate.return_value = result

        response = await gateway.validate_campaign(
            campaign_id="gw-case",
            text_content="Test",
            platform="LINKEDIN",
        )

        assert response.platform == Platform.LINKEDIN
