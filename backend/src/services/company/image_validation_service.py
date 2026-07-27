import logging

from src.services.supabase import IMAGE_TYPES, MAX_IMAGE_SIZE, MAX_IMAGES

logger = logging.getLogger(__name__)


class ImageValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ImageValidationService:
    """Validates brand reference image files and count limits."""

    VALID_TYPES = IMAGE_TYPES
    MAX_SIZE = MAX_IMAGE_SIZE
    MAX_IMAGES = MAX_IMAGES

    def validate_image_file(self, content_type: str, file_size: int) -> None:
        """Validate a single image file's format and size."""
        if content_type not in self.VALID_TYPES:
            raise ImageValidationError(
                f"Unsupported image format: {content_type}. " f"Accepted formats: JPEG, PNG, WebP"
            )
        if file_size > self.MAX_SIZE:
            raise ImageValidationError(
                f"Image file too large: {file_size} bytes "
                f"(max {self.MAX_SIZE // (1024 * 1024)}MB)"
            )

    def validate_image_count(self, current_count: int, add_count: int = 1) -> None:
        """Enforce the maximum of six brand reference images per company."""
        if current_count + add_count > self.MAX_IMAGES:
            remaining = self.MAX_IMAGES - current_count
            raise ImageValidationError(
                f"Maximum of {self.MAX_IMAGES} brand reference images allowed per company "
                f"profile. You have {current_count} and can add {remaining} more."
            )
