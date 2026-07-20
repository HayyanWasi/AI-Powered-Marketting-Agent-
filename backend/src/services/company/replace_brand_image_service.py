import logging
from pathlib import Path
from typing import Any

from src.repositories.company_repository import CompanyRepository
from src.services.company.image_validation_service import ImageValidationService
from src.services.supabase import SupabaseService

logger = logging.getLogger(__name__)


class ReplaceBrandImageService:
    """Service for replacing a brand reference image at a specific index."""

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
        index: int,
        file_path: Path,
        content_type: str,
        filename: str,
        file_size: int,
    ) -> dict[str, Any]:
        self._validation.validate_image_file(content_type, file_size)

        profile = self._repository.get_by_id(profile_id)
        urls = profile.reference_image_urls

        if index < 0 or index >= len(urls):
            raise ValueError(
                f"Invalid image index {index}. Profile has {len(urls)} images (valid: 0-{len(urls) - 1})"
            )

        new_url = self._supabase.upload_image(file_path, content_type, profile_id)
        urls[index] = new_url
        self._repository.update(profile_id, {"reference_image_urls": urls})

        logger.info("Replaced brand image at index %d for profile %s", index, profile_id)
        return {"url": new_url, "index": index, "total": len(urls)}
