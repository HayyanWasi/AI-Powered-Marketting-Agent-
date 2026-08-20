import logging
from pathlib import Path
from typing import Any

from src.repositories.company_repository import CompanyRepository
from src.services.company.image_validation_service import ImageValidationService
from src.services.supabase import SupabaseService

logger = logging.getLogger(__name__)


class UploadBrandImageService:
    """Service for uploading brand reference images."""

    def __init__(
        self,
        supabase: SupabaseService | None = None,
        repository: CompanyRepository | None = None,
        validation: ImageValidationService | None = None,
    ):
        self._supabase = supabase or SupabaseService()
        self._repository = repository or CompanyRepository()
        self._validation = validation or ImageValidationService()

    def execute(
        self,
        profile_id: str,
        file_path: Path,
        content_type: str,
        filename: str,
        file_size: int,
    ) -> dict[str, Any]:
        self._validation.validate_image_file(content_type, file_size)

        profile = self._repository.get_by_id(profile_id)
        current_urls = profile.reference_image_urls
        self._validation.validate_image_count(len(current_urls))

        url = self._supabase.upload_image(file_path, content_type, profile_id)
        all_urls = current_urls + [url]
        self._repository.update(profile_id, {"reference_image_urls": all_urls})

        logger.info(
            "Uploaded brand image %s for profile %s (total: %d)",
            filename,
            profile_id,
            len(all_urls),
        )
        return {"url": url, "total": len(all_urls)}
