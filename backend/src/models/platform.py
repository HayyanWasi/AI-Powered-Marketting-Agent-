from enum import Enum


class Platform(str, Enum):
    """Supported social media platforms for campaign validation."""

    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"


# Platform-specific text character limits
PLATFORM_TEXT_LIMITS: dict[Platform, int] = {
    Platform.LINKEDIN: 3000,
    Platform.INSTAGRAM: 2200,
    Platform.FACEBOOK: 63206,
}

# Platform-specific image minimum dimensions
PLATFORM_IMAGE_MIN_DIMENSIONS: dict[Platform, tuple[int, int]] = {
    Platform.LINKEDIN: (1080, 1080),
    Platform.INSTAGRAM: (1080, 1080),
    Platform.FACEBOOK: (1080, 1080),
}

# Supported image formats
SUPPORTED_IMAGE_FORMATS = {"image/jpeg", "image/png", "image/webp"}

# Maximum image file size (10MB)
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
