import logging
from typing import Any

from src.models.company import CompanyProfile
from src.models.errors import ErrorCode
from src.services.supabase import NotFoundError, SupabaseService, SupabaseServiceError

logger = logging.getLogger(__name__)


class CompanyProfileServiceError(Exception):
    """Base exception for CompanyProfileService."""

    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        self.error_code = error_code
        self.message = message
        self.details = details
        super().__init__(message)


class CompanyProfileNotFoundError(CompanyProfileServiceError):
    """Raised when company profile is not found."""

    def __init__(self, profile_id: str):
        super().__init__(
            error_code=ErrorCode.PROFILE_NOT_FOUND,
            message="Company profile not found",
            details={"profile_id": profile_id},
        )


class CompanyProfileService:
    """Service for fetching company profiles from Supabase."""

    def __init__(self, supabase_service: SupabaseService | None = None):
        self._supabase = supabase_service or SupabaseService()

    async def get_profile(self, profile_id: str) -> CompanyProfile:
        """
        Fetch a company profile by ID.

        Args:
            profile_id: UUID of the company profile

        Returns:
            CompanyProfile with all brand fields

        Raises:
            CompanyProfileNotFoundError: If profile not found
            CompanyProfileServiceError: If Supabase error occurs
        """
        try:
            logger.info("Fetching company profile: %s", profile_id)
            data = self._supabase.get_profile(profile_id)

            profile = CompanyProfile(
                id=data["id"],
                name=data.get("name") or data.get("company_name", ""),
                brand_colors=data.get("brand_colors"),
                brand_personality=data.get("brand_personality"),
                style_guide=data.get("style_guide"),
                logo_url=data.get("logo_url"),
                typography_style=data.get("typography_style"),
                reference_images=data.get("reference_image_urls"),
                industry_category=data.get("industry_category"),
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", ""),
            )

            logger.info("Successfully fetched profile: %s", profile.name)
            return profile

        except NotFoundError as e:
            logger.warning("Profile not found: %s", profile_id)
            raise CompanyProfileNotFoundError(profile_id) from e
        except SupabaseServiceError as e:
            logger.error("Supabase error fetching profile %s: %s", profile_id, e)
            raise CompanyProfileServiceError(
                error_code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to fetch company profile: {e}",
                details={"profile_id": profile_id},
            ) from e

    async def list_profiles(self) -> list[CompanyProfile]:
        """Fetch all company profiles."""
        try:
            logger.info("Listing all company profiles")
            rows = self._supabase.list_profiles()

            profiles = [
                CompanyProfile(
                    id=row["id"],
                    name=row.get("company_name", ""),
                    brand_colors=row.get("brand_colors"),
                    brand_personality=row.get("brand_personality"),
                    style_guide=row.get("style_guide"),
                    logo_url=row.get("logo_url"),
                    typography_style=row.get("typography_style"),
                    reference_images=row.get("reference_image_urls"),
                    industry_category=row.get("industry_category"),
                    created_at=row.get("created_at", ""),
                    updated_at=row.get("updated_at", ""),
                )
                for row in rows
            ]

            logger.info("Found %d profiles", len(profiles))
            return profiles

        except SupabaseServiceError as e:
            logger.error("Supabase error listing profiles: %s", e)
            raise CompanyProfileServiceError(
                error_code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to list company profiles: {e}",
            ) from e
