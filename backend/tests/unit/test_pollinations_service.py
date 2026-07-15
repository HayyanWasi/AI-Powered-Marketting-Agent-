from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.models.brand_style import BrandStyleContextInternal
from src.services.pollinations_service import (
    PollinationsService,
    PollinationsServiceError,
)


@pytest.fixture
def mock_client() -> AsyncMock:
    client = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def service(mock_client: AsyncMock) -> PollinationsService:
    return PollinationsService(
        client=mock_client,
        base_url="https://image.pollinations.ai/prompt",
        model="kontext",
        timeout_seconds=30,
        max_retries=3,
    )


class TestGenerateImage:
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(
        self, service: PollinationsService, mock_client: AsyncMock
    ) -> None:
        response = MagicMock()
        response.status_code = 200
        mock_client.get.return_value = response

        url, elapsed = await service.generate_image("test prompt")

        assert "test%20prompt" in url
        assert "model=kontext" in url
        assert elapsed >= 0
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_5xx(
        self, service: PollinationsService, mock_client: AsyncMock
    ) -> None:
        error_response = MagicMock()
        error_response.status_code = 500
        success_response = MagicMock()
        success_response.status_code = 200
        mock_client.get.side_effect = [error_response, success_response]

        url, elapsed = await service.generate_image("test prompt")

        assert mock_client.get.call_count == 2
        assert elapsed >= 0

    @pytest.mark.asyncio
    async def test_retries_on_429_with_retry_after(
        self, service: PollinationsService, mock_client: AsyncMock
    ) -> None:
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "1"}
        success_response = MagicMock()
        success_response.status_code = 200
        mock_client.get.side_effect = [rate_limit_response, success_response]

        with patch("src.services.pollinations_service.asyncio.sleep", new_callable=AsyncMock):
            url, elapsed = await service.generate_image("test prompt")

        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_timeout(
        self, service: PollinationsService, mock_client: AsyncMock
    ) -> None:
        mock_client.get.side_effect = [
            httpx.TimeoutException("timeout"),
            MagicMock(status_code=200),
        ]

        with patch("src.services.pollinations_service.asyncio.sleep", new_callable=AsyncMock):
            url, elapsed = await service.generate_image("test prompt")

        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_all_retries_exhausted(
        self, service: PollinationsService, mock_client: AsyncMock
    ) -> None:
        mock_client.get.return_value = MagicMock(status_code=500)

        with patch("src.services.pollinations_service.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(PollinationsServiceError, match="Failed after 3 attempts"):
                await service.generate_image("test prompt")

        assert mock_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_client_error_not_retried(
        self, service: PollinationsService, mock_client: AsyncMock
    ) -> None:
        mock_client.get.return_value = MagicMock(status_code=400, text="Bad request")

        with pytest.raises(PollinationsServiceError, match="Pollinations error: 400"):
            await service.generate_image("test prompt")

        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_request_error_retried(
        self, service: PollinationsService, mock_client: AsyncMock
    ) -> None:
        mock_client.get.side_effect = [
            httpx.RequestError("connection failed"),
            MagicMock(status_code=200),
        ]

        with patch("src.services.pollinations_service.asyncio.sleep", new_callable=AsyncMock):
            url, elapsed = await service.generate_image("test prompt")

        assert mock_client.get.call_count == 2


class TestGenerateFallback:
    @pytest.mark.asyncio
    async def test_returns_url(self, service: PollinationsService, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = MagicMock(status_code=200)

        url, elapsed = await service.generate_fallback()

        assert "placeholder" in url.lower() or "branded" in url.lower()
        assert elapsed >= 0

    @pytest.mark.asyncio
    async def test_with_brand_context(
        self, service: PollinationsService, mock_client: AsyncMock
    ) -> None:
        mock_client.get.return_value = MagicMock(status_code=200)
        brand_ctx = BrandStyleContextInternal(color_palette="#FF0000")

        url, elapsed = await service.generate_fallback(brand_ctx)

        assert "FF0000" in url or "placeholder" in url.lower()

    @pytest.mark.asyncio
    async def test_returns_url_even_on_failure(
        self, service: PollinationsService, mock_client: AsyncMock
    ) -> None:
        mock_client.get.return_value = MagicMock(status_code=500)

        url, elapsed = await service.generate_fallback()

        assert url.startswith("https://")


class TestBuildImageUrl:
    def test_url_encoding(self, service: PollinationsService) -> None:
        url = service._build_image_url("Hello World & Goodbye")
        assert "Hello%20World%20%26%20Goodbye" in url
        assert "model=kontext" in url

    def test_url_with_special_chars(self, service: PollinationsService) -> None:
        url = service._build_image_url("colors #FF6B35 and #004E89")
        assert "%23FF6B35" in url
