import logging

from src.models.company import CompanyProfile

logger = logging.getLogger(__name__)


class CompanyValidationError(Exception):
    def __init__(self, message: str, field: str | None = None):
        self.message = message
        self.field = field
        super().__init__(message)


class CompanyValidator:
    """Business rule validation for company profiles."""

    @staticmethod
    def validate_complete(profile: CompanyProfile) -> None:
        """Check if a profile has the minimum required brand information.

        Raises:
            CompanyValidationError: If profile is incomplete
        """
        if not profile.company_name or not profile.company_name.strip():
            raise CompanyValidationError(
                "Company name is required before this profile can be used for campaign generation",
                field="company_name",
            )
        if not profile.brand_guidelines or not profile.brand_guidelines.strip():
            raise CompanyValidationError(
                "Brand guidelines are required before this profile can be used for campaign generation",
                field="brand_guidelines",
            )

    @staticmethod
    def validate_create_data(company_name: str, brand_guidelines: str) -> None:
        """Validate data before creating a new profile.

        Raises:
            CompanyValidationError: If validation fails
        """
        errors: list[str] = []
        if not company_name or not company_name.strip():
            errors.append("Company name is required")
        if not brand_guidelines or not brand_guidelines.strip():
            errors.append("Brand guidelines are required")
        if errors:
            raise CompanyValidationError("; ".join(errors))

    @staticmethod
    def validate_update_data(data: dict) -> None:
        """Validate data before updating a profile.

        Raises:
            CompanyValidationError: If validation fails
        """
        if "brand_guidelines" in data:
            val = data["brand_guidelines"]
            if val is not None and (not isinstance(val, str) or not val.strip()):
                raise CompanyValidationError(
                    "Brand guidelines cannot be empty", field="brand_guidelines"
                )

    @staticmethod
    def check_image_limit(current_count: int, max_images: int = 6) -> None:
        """Check if adding more images would exceed the limit.

        Raises:
            CompanyValidationError: If limit would be exceeded
        """
        if current_count >= max_images:
            raise CompanyValidationError(
                f"Maximum of {max_images} brand reference images allowed per company profile",
                field="reference_images",
            )

    @staticmethod
    def validate_image_file(
        content_type: str,
        valid_types: set[str],
        file_size: int,
        max_size: int,
    ) -> None:
        """Validate an uploaded image file.

        Raises:
            CompanyValidationError: If validation fails
        """
        if content_type not in valid_types:
            raise CompanyValidationError(
                f"Unsupported image format: {content_type}. "
                f"Accepted formats: {', '.join(sorted(valid_types))}",
                field="image",
            )
        if file_size > max_size:
            raise CompanyValidationError(
                f"Image file too large: {file_size} bytes (max {max_size} bytes)",
                field="image",
            )
