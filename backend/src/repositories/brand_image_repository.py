import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.models.brand_reference_image import BrandReferenceImage
from src.services.supabase import NotFoundError, SupabaseService, SupabaseServiceError

logger = logging.getLogger(__name__)


class BrandImageRepositoryError(Exception):
    pass


class BrandImageNotFoundError(BrandImageRepositoryError):
    pass


class BrandImageRepository:
    """Data access for BrandReferenceImage entities."""

    def __init__(self, supabase: SupabaseService | None = None):
        self._supabase = supabase or SupabaseService()

    def upload(
        self,
        company_profile_id: str,
        file_path: Path,
        content_type: str,
        filename: str,
        file_size: int,
        sort_order: int,
    ) -> BrandReferenceImage:
        try:
            url = self._supabase.upload_image(file_path, content_type, company_profile_id)
            image = BrandReferenceImage(
                id=str(uuid4()),
                company_profile_id=company_profile_id,
                storage_path=url,
                filename=filename,
                content_type=content_type,
                file_size=file_size,
                sort_order=sort_order,
            )
            return image
        except SupabaseServiceError as e:
            raise BrandImageRepositoryError(str(e)) from e

    def remove(self, storage_path: str) -> None:
        try:
            self._supabase.remove_storage_file(storage_path)
        except Exception as e:
            logger.warning("Failed to remove image at %s: %s", storage_path, e)

    def build_image_record(
        self,
        company_profile_id: str,
        url: str,
        filename: str,
        content_type: str,
        file_size: int,
        sort_order: int,
    ) -> dict[str, Any]:
        return {
            "id": str(uuid4()),
            "company_profile_id": company_profile_id,
            "url": url,
            "filename": filename,
            "content_type": content_type,
            "file_size": file_size,
            "sort_order": sort_order,
        }
