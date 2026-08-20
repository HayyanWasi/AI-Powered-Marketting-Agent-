import asyncio
import logging
import time
from typing import Any
from urllib.parse import quote

import httpx

from src.config.settings import settings
from src.models.brand_style import BrandStyleContextInternal

logger = logging.getLogger(__name__)


class PollinationsServiceError(Exception):
    """Base exception for PollinationsService."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retry_after: int | None = None,
    ):
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(message)


class PollinationsServerError(PollinationsServiceError):
    """Pollinations server error (5xx)."""

    pass


class PollinationsRateLimitError(PollinationsServiceError):
    """Pollinations rate limit error (429)."""

    pass


class PollinationsTimeoutError(PollinationsServiceError):
    """Pollinations request timeout."""

    pass


class PollinationsService:
    """Service for generating images via Pollinations API."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        api_token: str | None = None,
        image_width: int | None = None,
        image_height: int | None = None,
    ):
        self._base_url = base_url or settings.pollinations_base_url
        self._model = model or settings.pollinations_model
        self._timeout = timeout_seconds or settings.pollinations_timeout_seconds
        self._max_retries = max_retries or settings.pollinations_max_retries
        self._api_token = api_token or settings.pollinations_api_token
        self._image_width = image_width or settings.pollinations_image_width
        self._image_height = image_height or settings.pollinations_image_height

        headers = {}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"

        self._client = client or httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=True,
            headers=headers,
        )
        self._own_client = client is None

    @property
    def model(self) -> str:
        """The image model in use (empty string means Pollinations default)."""
        return self._model or "flux"

    async def __aenter__(self) -> "PollinationsService":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._own_client:
            await self._client.aclose()

    def _build_image_url(self, prompt: str) -> str:
        """Build the full Pollinations image URL."""
        encoded_prompt = quote(prompt, safe="")
        params = [f"width={self._image_width}", f"height={self._image_height}"]
        if self._model:
            params.append(f"model={self._model}")
        return f"{self._base_url}/{encoded_prompt}?{'&'.join(params)}"

    def _build_fallback_prompt(self, brand_context: BrandStyleContextInternal | None) -> str:
        """Build a branded fallback prompt."""
        parts = ["Professional branded placeholder"]
        if brand_context:
            if brand_context.color_palette:
                parts.append(f"brand colors {brand_context.color_palette}")
            if brand_context.personality_descriptors:
                parts.append(f"{brand_context.personality_descriptors} style")
            if brand_context.style_guidance:
                parts.append(brand_context.style_guidance)
        return ", ".join(parts)

    async def generate_image(
        self,
        prompt: str,
        brand_context: BrandStyleContextInternal | None = None,
    ) -> tuple[str, int]:
        """
        Generate an image via Pollinations API with retry logic.

        Args:
            prompt: The complete prompt for image generation
            brand_context: Optional brand context for fallback generation

        Returns:
            Tuple of (image_url, generation_time_ms)

        Raises:
            PollinationsServiceError: If generation fails after all retries
        """
        start_time = time.monotonic()
        last_exception: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                image_url = self._build_image_url(prompt)
                logger.info(
                    "Pollinations request attempt %d/%d: %s",
                    attempt,
                    self._max_retries,
                    image_url[:100],
                )

                response = await self._client.get(image_url)

                if response.status_code == 200:
                    elapsed_ms = int((time.monotonic() - start_time) * 1000)
                    logger.info("Pollinations generation succeeded in %dms", elapsed_ms)
                    return image_url, elapsed_ms

                # Handle different error status codes
                if response.status_code == 429:
                    # Rate limited - respect Retry-After header
                    retry_after = response.headers.get("Retry-After")
                    wait_time = (
                        int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                    )
                    logger.warning(
                        "Pollinations rate limited (429), waiting %ds (attempt %d/%d)",
                        wait_time,
                        attempt,
                        self._max_retries,
                    )
                    last_exception = PollinationsRateLimitError(
                        "Rate limited by Pollinations",
                        status_code=429,
                        retry_after=wait_time,
                    )
                    if attempt < self._max_retries:
                        await asyncio.sleep(wait_time)
                        continue

                elif 500 <= response.status_code < 600:
                    # Server error - retry with exponential backoff
                    wait_time = 2**attempt
                    logger.warning(
                        "Pollinations server error (%d), waiting %ds (attempt %d/%d)",
                        response.status_code,
                        wait_time,
                        attempt,
                        self._max_retries,
                    )
                    last_exception = PollinationsServerError(
                        f"Pollinations server error: {response.status_code}",
                        status_code=response.status_code,
                    )
                    if attempt < self._max_retries:
                        await asyncio.sleep(wait_time)
                        continue

                else:
                    # Client error - don't retry
                    logger.error(
                        "Pollinations client error (%d): %s",
                        response.status_code,
                        response.text[:200],
                    )
                    raise PollinationsServiceError(
                        f"Pollinations error: {response.status_code}",
                        status_code=response.status_code,
                    )

            except httpx.TimeoutException:
                wait_time = 2**attempt
                logger.warning(
                    "Pollinations request timeout, waiting %ds (attempt %d/%d)",
                    wait_time,
                    attempt,
                    self._max_retries,
                )
                last_exception = PollinationsTimeoutError(
                    "Pollinations request timed out",
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(wait_time)
                    continue

            except httpx.RequestError as e:
                logger.error("Pollinations request error: %s", e)
                last_exception = PollinationsServiceError(f"Request failed: {e}")
                if attempt < self._max_retries:
                    await asyncio.sleep(2**attempt)
                    continue

        # All retries exhausted
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        logger.error(
            "Pollinations generation failed after %d attempts in %dms: %s",
            self._max_retries,
            elapsed_ms,
            last_exception,
        )
        raise PollinationsServiceError(
            f"Failed after {self._max_retries} attempts: {last_exception}"
        ) from last_exception

    async def generate_fallback(
        self,
        brand_context: BrandStyleContextInternal | None = None,
    ) -> tuple[str, int]:
        """
        Generate a branded fallback image.

        Args:
            brand_context: Brand context for fallback styling

        Returns:
            Tuple of (fallback_image_url, generation_time_ms)
        """
        start_time = time.monotonic()
        fallback_prompt = self._build_fallback_prompt(brand_context)
        image_url = self._build_image_url(fallback_prompt)

        logger.info("Generating fallback image: %s", image_url[:100])

        try:
            response = await self._client.get(image_url)
            if response.status_code == 200:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                logger.info("Fallback generation succeeded in %dms", elapsed_ms)
                return image_url, elapsed_ms
            else:
                logger.warning("Fallback generation returned %d", response.status_code)
        except Exception as e:
            logger.error("Fallback generation failed: %s", e)

        # Return URL anyway - Pollinations CDN will serve something
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return image_url, elapsed_ms
