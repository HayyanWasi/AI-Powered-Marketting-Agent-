import io
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from PIL import Image

from src.config.settings import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Get or create the shared httpx client."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=settings.image_validation_timeout_seconds,
            follow_redirects=True,
        )
    return _client


@dataclass
class ValidationResult:
    """Result of image validation."""

    is_valid: bool
    width: int
    height: int
    content_type: str
    errors: list[str]
    url_accessible: bool


class ImageValidationServiceError(Exception):
    """Base exception for ImageValidationService."""

    pass


class ImageValidationService:
    """Service for validating generated images."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client or _get_client()
        self._own_client = client is None

    async def __aenter__(self) -> "ImageValidationService":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._own_client and self._client is not _client:
            await self._client.aclose()

    async def validate_image_url(self, image_url: str) -> ValidationResult:
        """
        Validate an image URL by checking accessibility and resolution.

        Args:
            image_url: URL of the image to validate

        Returns:
            ValidationResult with validation status and image metadata

        Raises:
            ImageValidationServiceError: If validation fails due to network error
        """
        errors = []

        # First, check URL accessibility with HEAD request
        url_accessible = False
        content_type = ""
        content_length = 0

        try:
            head_response = await self._client.head(image_url)
            if head_response.status_code == 200:
                url_accessible = True
                content_type = head_response.headers.get("content-type", "")
                content_length_str = head_response.headers.get("content-length")
                if content_length_str:
                    content_length = int(content_length_str)
                logger.debug(
                    "HEAD check passed: content_type=%s, content_length=%d",
                    content_type,
                    content_length,
                )
            else:
                errors.append(f"HEAD request returned status {head_response.status_code}")
                logger.warning("HEAD check failed: status=%d", head_response.status_code)
        except httpx.TimeoutException:
            errors.append("HEAD request timed out")
            logger.warning("HEAD request timed out for %s", image_url)
        except httpx.RequestError as e:
            errors.append(f"HEAD request failed: {str(e)}")
            logger.warning("HEAD request failed for %s: %s", image_url, e)

        if not url_accessible:
            return ValidationResult(
                is_valid=False,
                width=0,
                height=0,
                content_type="",
                errors=errors,
                url_accessible=False,
            )

        # Validate content type
        if not content_type.startswith("image/"):
            errors.append(f"Invalid content type: {content_type} (expected image/*)")
            return ValidationResult(
                is_valid=False,
                width=0,
                height=0,
                content_type=content_type,
                errors=errors,
                url_accessible=True,
            )

        # Download and validate image dimensions
        try:
            get_response = await self._client.get(image_url)
            get_response.raise_for_status()
            image_data = get_response.content

            # Open image with Pillow
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size
            actual_format = image.format or "UNKNOWN"

            logger.debug(
                "Image validation: width=%d, height=%d, format=%s",
                width,
                height,
                actual_format,
            )

            # Check minimum resolution
            min_width = settings.min_image_width
            min_height = settings.min_image_height

            if width < min_width or height < min_height:
                errors.append(
                    f"Image resolution {width}x{height} below minimum {min_width}x{min_height}"
                )

            return ValidationResult(
                is_valid=len(errors) == 0,
                width=width,
                height=height,
                content_type=content_type,
                errors=errors,
                url_accessible=True,
            )

        except httpx.TimeoutException:
            errors.append("GET request timed out")
            logger.warning("GET request timed out for %s", image_url)
        except httpx.RequestError as e:
            errors.append(f"GET request failed: {str(e)}")
            logger.warning("GET request failed for %s: %s", image_url, e)
        except Exception as e:
            errors.append(f"Image processing failed: {str(e)}")
            logger.error("Image processing failed for %s: %s", image_url, e)

        return ValidationResult(
            is_valid=False,
            width=0,
            height=0,
            content_type=content_type,
            errors=errors,
            url_accessible=True,
        )
