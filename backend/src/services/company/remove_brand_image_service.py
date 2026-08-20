import logging

from src.repositories.company_repository import CompanyRepository
from src.services.supabase import SupabaseService

logger = logging.getLogger(__name__)


class RemoveBrandImageService:
    """Service for removing a brand reference image from a company profile."""

    def __init__(
        self,
        supabase: SupabaseService | None = None,
        repository: CompanyRepository | None = None,
    ):
        self._supabase = supabase or SupabaseService()
        self._repository = repository or CompanyRepository()

    def execute(self, profile_id: str, url: str) -> int:
        """Remove an image URL from the profile's reference_image_urls array.

        Returns the new count of images after removal.
        """
        profile = self._repository.get_by_id(profile_id)
        urls = profile.reference_image_urls

        if url not in urls:
            raise ValueError(f"Image URL not found in profile {profile_id}")

        urls.remove(url)
        self._repository.update(profile_id, {"reference_image_urls": urls})

        logger.info("Removed brand image from profile %s (remaining: %d)", profile_id, len(urls))
        return len(urls)
