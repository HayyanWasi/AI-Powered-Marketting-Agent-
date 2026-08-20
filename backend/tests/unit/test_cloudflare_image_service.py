import base64
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.services.cloudflare_image_service import (
    CloudflareConfigError,
    CloudflareImageService,
    CloudflareImageServiceError,
)


@pytest.fixture
def mock_client() -> AsyncMock:
    client = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def service(mock_client: AsyncMock) -> CloudflareImageService:
    svc = CloudflareImageService(
        account_id="acct123",
        token="cfut_test",
        client=mock_client,
    )
    return svc


def _response(
    status_code: int, *, content: bytes = b"", json_body: dict | None = None
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.content = content
    resp.headers = {}
    resp.text = ""
    if json_body is not None:
        resp.json.return_value = json_body
    return resp


class TestConfig:
    @pytest.mark.asyncio
    async def test_missing_credentials_raises(self, mock_client: AsyncMock) -> None:
        svc = CloudflareImageService(account_id="x", token="x", client=mock_client)
        svc._account_id = ""  # simulate unconfigured env
        svc._token = ""
        with pytest.raises(CloudflareConfigError):
            await svc.generate_from_text("hello")


class TestImg2Img:
    @pytest.mark.asyncio
    async def test_returns_raw_bytes(
        self, service: CloudflareImageService, mock_client: AsyncMock
    ) -> None:
        mock_client.post.return_value = _response(200, content=b"PNGDATA")

        result = await service.generate_from_reference("prompt", b"refbytes", strength=0.5)

        assert result == b"PNGDATA"
        assert mock_client.post.call_count == 1
        _, kwargs = mock_client.post.call_args
        assert kwargs["json"]["image"] == list(b"refbytes")
        assert kwargs["json"]["strength"] == 0.5
        assert kwargs["headers"]["Authorization"] == "Bearer cfut_test"


class TestText2Img:
    @pytest.mark.asyncio
    async def test_decodes_base64(
        self, service: CloudflareImageService, mock_client: AsyncMock
    ) -> None:
        raw = b"flux-image-bytes"
        encoded = base64.b64encode(raw).decode()
        mock_client.post.return_value = _response(200, json_body={"result": {"image": encoded}})

        result = await service.generate_from_text("prompt")

        assert result == raw

    @pytest.mark.asyncio
    async def test_missing_image_raises(
        self, service: CloudflareImageService, mock_client: AsyncMock
    ) -> None:
        mock_client.post.return_value = _response(200, json_body={"result": {}})

        with pytest.raises(CloudflareImageServiceError):
            await service.generate_from_text("prompt")


class TestRetry:
    @pytest.mark.asyncio
    async def test_retries_on_5xx_then_succeeds(
        self, service: CloudflareImageService, mock_client: AsyncMock
    ) -> None:
        mock_client.post.side_effect = [
            _response(500),
            _response(200, content=b"OK"),
        ]

        with patch("src.services.cloudflare_image_service.asyncio.sleep", new_callable=AsyncMock):
            result = await service.generate_from_reference("p", b"ref")

        assert result == b"OK"
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_429_with_retry_after(
        self, service: CloudflareImageService, mock_client: AsyncMock
    ) -> None:
        rate_limited = _response(429)
        rate_limited.headers = {"Retry-After": "1"}
        mock_client.post.side_effect = [rate_limited, _response(200, content=b"OK")]

        with patch(
            "src.services.cloudflare_image_service.asyncio.sleep", new_callable=AsyncMock
        ) as sleep_mock:
            result = await service.generate_from_reference("p", b"ref")

        assert result == b"OK"
        sleep_mock.assert_awaited()

    @pytest.mark.asyncio
    async def test_exhausts_retries_raises(
        self, service: CloudflareImageService, mock_client: AsyncMock
    ) -> None:
        mock_client.post.return_value = _response(503)

        with patch("src.services.cloudflare_image_service.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(CloudflareImageServiceError):
                await service.generate_from_text("p")

        assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_4xx_raises_immediately(
        self, service: CloudflareImageService, mock_client: AsyncMock
    ) -> None:
        mock_client.post.return_value = _response(400)

        with pytest.raises(CloudflareImageServiceError):
            await service.generate_from_text("p")

        assert mock_client.post.call_count == 1


class TestDownloadReference:
    @pytest.mark.asyncio
    async def test_success(self, service: CloudflareImageService, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _response(200, content=b"imgbytes")

        result = await service.download_reference("https://example.com/ref.png")

        assert result == b"imgbytes"

    @pytest.mark.asyncio
    async def test_failure_returns_none(
        self, service: CloudflareImageService, mock_client: AsyncMock
    ) -> None:
        mock_client.get.return_value = _response(404)

        result = await service.download_reference("https://example.com/missing.png")

        assert result is None

    @pytest.mark.asyncio
    async def test_http_error_returns_none(
        self, service: CloudflareImageService, mock_client: AsyncMock
    ) -> None:
        mock_client.get.side_effect = httpx.ConnectError("boom")

        result = await service.download_reference("https://example.com/ref.png")

        assert result is None
