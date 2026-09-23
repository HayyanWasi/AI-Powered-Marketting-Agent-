"""Cloudflare Workers AI image generation service (free tier).

Provides image-to-image generation from a reference image (Stable Diffusion
img2img) and text-to-image generation (FLUX schnell) as a fallback. Both models
run on Cloudflare Workers AI, which is free within the daily neuron allowance.

Response formats differ between models (verified against the live API):
- img2img (`@cf/runwayml/stable-diffusion-v1-5-img2img`) returns raw PNG bytes.
- flux (`@cf/black-forest-labs/flux-1-schnell`) returns JSON with a base64 image
  string at ``result.image``.
"""

from __future__ import annotations

import asyncio
import base64
import logging

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)


class CloudflareImageServiceError(Exception):
    """Base exception for Cloudflare Workers AI image generation failures."""


class CloudflareConfigError(CloudflareImageServiceError):
    """Raised when required Cloudflare credentials are not configured."""


class CloudflareImageService:
    """Async client for Cloudflare Workers AI image models."""

    def __init__(
        self,
        account_id: str | None = None,
        token: str | None = None,
        gateway_id: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._account_id = account_id or settings.cloudflare_account_id
        self._token = token or settings.cloudflare_ai_token
        self._gateway_id = gateway_id or settings.cloudflare_gateway_id
        self._base_url = settings.cloudflare_ai_base_url.rstrip("/")
        self._img2img_model = settings.cloudflare_img2img_model
        self._text2img_model = settings.cloudflare_text2img_model
        self._timeout = settings.cloudflare_image_timeout_seconds
        self._max_retries = settings.cloudflare_max_retries
        self._width = settings.cloudflare_image_width
        self._height = settings.cloudflare_image_height
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> CloudflareImageService:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    @property
    def img2img_model(self) -> str:
        return self._img2img_model

    @property
    def text2img_model(self) -> str:
        return self._text2img_model

    async def __aexit__(self, *exc: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _require_config(self) -> None:
        if not self._account_id or not self._token:
            raise CloudflareConfigError(
                "Cloudflare account id / token not configured "
                "(set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_AI_TOKEN)"
            )

    def _run_url(self) -> str:
        return f"{self._base_url}/{self._account_id}/ai/run"

    @property
    def _headers(self) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._token}"}
        if self._gateway_id:
            headers["cf-aig-gateway-id"] = self._gateway_id
        return headers

    async def _post(self, model: str, payload: dict) -> httpx.Response:
        """POST to a Workers AI model with retry/backoff on 429 and 5xx."""
        self._require_config()
        assert self._client is not None  # set by __aenter__
        url = self._run_url()
        last_error: Exception | None = None
        
        envelope_payload = {
            "model": model,
            "input": payload
        }

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._client.post(url, json=envelope_payload, headers=self._headers)
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "Cloudflare request error (attempt %d/%d) for %s: %s",
                    attempt,
                    self._max_retries,
                    model,
                    exc,
                )
                await self._sleep_before_retry(attempt)
                continue

            if response.status_code == 200:
                return response

            if response.status_code == 429 or response.status_code >= 500:
                last_error = CloudflareImageServiceError(
                    f"Cloudflare {model} returned {response.status_code}"
                )
                logger.warning(
                    "Cloudflare %s returned %d (attempt %d/%d)",
                    model,
                    response.status_code,
                    attempt,
                    self._max_retries,
                )
                retry_after = self._retry_after_seconds(response)
                await self._sleep_before_retry(attempt, retry_after)
                continue

            # Non-retryable client error (400/401/403/404 …)
            raise CloudflareImageServiceError(
                f"Cloudflare {model} failed with {response.status_code}: {response.text[:300]}"
            )

        raise CloudflareImageServiceError(
            f"Cloudflare {model} failed after {self._max_retries} attempts"
        ) from last_error

    @staticmethod
    def _retry_after_seconds(response: httpx.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    async def _sleep_before_retry(self, attempt: int, retry_after: float | None = None) -> None:
        if attempt >= self._max_retries:
            return
        delay = retry_after if retry_after is not None else float(2**attempt)
        await asyncio.sleep(delay)

    async def generate_from_reference(
        self,
        prompt: str,
        reference_image_bytes: bytes,
        strength: float = 0.6,
        num_steps: int = 20,
    ) -> bytes:
        """Generate an image guided by a reference image (img2img).

        Args:
            prompt: Text prompt describing the desired output.
            reference_image_bytes: Raw bytes of the reference image.
            strength: How much to transform the reference (0-1). Lower keeps the
                reference closer; higher lets the prompt dominate.
            num_steps: Diffusion steps.

        Returns:
            Raw PNG image bytes.
        """
        payload = {
            "prompt": prompt,
            "image": list(reference_image_bytes),
            "strength": strength,
            "num_steps": num_steps,
            "width": self._width,
            "height": self._height,
        }
        logger.info(
            "Cloudflare img2img generating (%d ref bytes, strength=%.2f)",
            len(reference_image_bytes),
            strength,
        )
        response = await self._post(self._img2img_model, payload)
        return response.content

    async def generate_from_text(self, prompt: str, steps: int = 4) -> bytes:
        """Generate an image from text only (FLUX schnell).

        Returns:
            Decoded image bytes (the model returns base64 JSON).
        """
        payload = {"prompt": prompt, "steps": steps}
        logger.info("Cloudflare text2img generating (flux, steps=%d)", steps)
        response = await self._post(self._text2img_model, payload)

        data = response.json()
        image_b64 = data.get("result", {}).get("image")
        if not image_b64:
            raise CloudflareImageServiceError("Cloudflare text2img response missing result.image")
        try:
            return base64.b64decode(image_b64)
        except (ValueError, TypeError) as exc:
            raise CloudflareImageServiceError(
                f"Failed to decode base64 image from Cloudflare: {exc}"
            ) from exc

    async def download_reference(self, url: str) -> bytes | None:
        """Download a reference image URL to bytes. Returns None on failure."""
        assert self._client is not None
        try:
            response = await self._client.get(url)
            if response.status_code == 200:
                return response.content
            logger.warning("Reference image download returned %d: %s", response.status_code, url)
        except httpx.HTTPError as exc:
            logger.warning("Reference image download failed for %s: %s", url, exc)
        return None
