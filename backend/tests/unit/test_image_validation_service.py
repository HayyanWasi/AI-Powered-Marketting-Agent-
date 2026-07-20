from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.services.image_validation_service import ImageValidationService


@pytest.fixture
def mock_client() -> AsyncMock:
    client = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def service(mock_client: AsyncMock) -> ImageValidationService:
    return ImageValidationService(client=mock_client)


def _make_head_response(
    status_code: int = 200, content_type: str = "image/png", content_length: str = "1024000"
) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.headers = {"content-type": content_type, "content-length": content_length}
    return response


def _make_image_bytes(width: int = 1080, height: int = 1080) -> bytes:
    """Create minimal valid PNG bytes with specified dimensions."""
    from io import BytesIO

    from PIL import Image

    img = Image.new("RGB", (width, height), color="red")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestValidateImageUrl:
    @pytest.mark.asyncio
    async def test_valid_image(
        self, service: ImageValidationService, mock_client: AsyncMock
    ) -> None:
        head_resp = _make_head_response(200, "image/png", "1024000")
        get_resp = MagicMock()
        get_resp.status_code = 200
        get_resp.content = _make_image_bytes(1080, 1080)
        get_resp.raise_for_status = MagicMock()
        mock_client.head.return_value = head_resp
        mock_client.get.return_value = get_resp

        result = await service.validate_image_url("https://example.com/image.png")

        assert result.is_valid is True
        assert result.width == 1080
        assert result.height == 1080
        assert result.url_accessible is True
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_image_too_small(
        self, service: ImageValidationService, mock_client: AsyncMock
    ) -> None:
        head_resp = _make_head_response(200, "image/png", "100000")
        get_resp = MagicMock()
        get_resp.status_code = 200
        get_resp.content = _make_image_bytes(800, 600)
        get_resp.raise_for_status = MagicMock()
        mock_client.head.return_value = head_resp
        mock_client.get.return_value = get_resp

        result = await service.validate_image_url("https://example.com/small.png")

        assert result.is_valid is False
        assert result.width == 800
        assert result.height == 600
        assert any("below minimum" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_url_inaccessible(
        self, service: ImageValidationService, mock_client: AsyncMock
    ) -> None:
        mock_client.head.side_effect = httpx.RequestError("connection refused")

        result = await service.validate_image_url("https://example.com/missing.png")

        assert result.is_valid is False
        assert result.url_accessible is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_head_timeout(
        self, service: ImageValidationService, mock_client: AsyncMock
    ) -> None:
        mock_client.head.side_effect = httpx.TimeoutException("timeout")

        result = await service.validate_image_url("https://example.com/slow.png")

        assert result.is_valid is False
        assert result.url_accessible is False

    @pytest.mark.asyncio
    async def test_non_image_content_type(
        self, service: ImageValidationService, mock_client: AsyncMock
    ) -> None:
        head_resp = _make_head_response(200, "text/html", "1024")
        mock_client.head.return_value = head_resp

        result = await service.validate_image_url("https://example.com/page.html")

        assert result.is_valid is False
        assert result.url_accessible is True
        assert any("content type" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_head_returns_non_200(
        self, service: ImageValidationService, mock_client: AsyncMock
    ) -> None:
        mock_client.head.return_value = _make_head_response(404)

        result = await service.validate_image_url("https://example.com/missing.png")

        assert result.is_valid is False
        assert result.url_accessible is False

    @pytest.mark.asyncio
    async def test_get_request_fails(
        self, service: ImageValidationService, mock_client: AsyncMock
    ) -> None:
        head_resp = _make_head_response(200, "image/png", "1024000")
        mock_client.head.return_value = head_resp
        mock_client.get.side_effect = httpx.RequestError("download failed")

        result = await service.validate_image_url("https://example.com/image.png")

        assert result.is_valid is False
        assert result.url_accessible is True

    @pytest.mark.asyncio
    async def test_get_timeout(
        self, service: ImageValidationService, mock_client: AsyncMock
    ) -> None:
        head_resp = _make_head_response(200, "image/png", "1024000")
        mock_client.head.return_value = head_resp
        mock_client.get.side_effect = httpx.TimeoutException("timeout")

        result = await service.validate_image_url("https://example.com/image.png")

        assert result.is_valid is False
        assert result.url_accessible is True
