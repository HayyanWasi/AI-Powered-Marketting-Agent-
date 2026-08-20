import logging
from urllib.parse import unquote, urlparse

from supabase import create_client

from src.config.settings import settings
from src.models.company import CompanyProfile
from src.repositories.company_repository import (
    CompanyNotFoundError,
    CompanyRepository,
    CompanyRepositoryError,
)
from src.services.supabase import STORAGE_BUCKET, SupabaseService

logger = logging.getLogger(__name__)


class DeleteCompanyService:
    """Service for deleting a company profile and its associated brand images.

    Prevents deletion if the profile is referenced by active campaigns (FR-016).
    """

    def __init__(
        self,
        repository: CompanyRepository | None = None,
        supabase: SupabaseService | None = None,
    ):
        self._repository = repository or CompanyRepository()
        self._supabase = supabase or SupabaseService()

    def execute(self, profile_id: str) -> None:
        try:
            profile = self._repository.get_by_id(profile_id)
        except CompanyNotFoundError as e:
            raise ValueError(str(e)) from e
        except CompanyRepositoryError as e:
            logger.error("Failed to fetch profile %s: %s", profile_id, e)
            raise

        self._assert_no_active_campaigns(profile_id)

        self._remove_storage_images(profile)
        self._repository.delete(profile_id)
        logger.info("Deleted company profile %s (%s)", profile_id, profile.company_name)

    def _assert_no_active_campaigns(self, profile_id: str) -> None:
        try:
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            result = (
                client.table("campaigns")
                .select("id")
                .eq("company_profile_id", profile_id)
                .limit(1)
                .execute()
            )
            if result.data:
                raise ValueError(
                    "This company profile cannot be deleted because it is referenced by "
                    "active campaigns. Please archive or complete those campaigns first."
                )
        except ValueError:
            raise
        except Exception:
            logger.info("No campaigns table found — skipping campaign reference check")

    def _remove_storage_images(self, profile: CompanyProfile) -> None:
        for url in profile.reference_image_urls:
            storage_path = self._extract_storage_path(url)
            if storage_path:
                self._supabase.remove_storage_file(storage_path)

    def _remove_storage_images(self, profile: CompanyProfile) -> None:
        for url in profile.reference_image_urls:
            storage_path = self._extract_storage_path(url)
            if storage_path:
                self._supabase.remove_storage_file(storage_path)

    @staticmethod
    def _extract_storage_path(url: str) -> str | None:
        try:
            parsed = urlparse(url)
            prefix = f"/storage/v1/object/public/{STORAGE_BUCKET}/"
            if prefix in parsed.path:
                return unquote(parsed.path.split(prefix, 1)[1])
            return None
        except Exception:
            logger.warning("Failed to parse storage URL: %s", url)
            return None
