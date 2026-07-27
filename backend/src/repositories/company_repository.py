import logging
from typing import Any

from src.models.company import CompanyProfile
from src.services.supabase import (
    DuplicateCompanyError,
    NotFoundError,
    SupabaseService,
    SupabaseServiceError,
)

logger = logging.getLogger(__name__)


class CompanyRepositoryError(Exception):
    pass


class CompanyNotFoundError(CompanyRepositoryError):
    pass


class CompanyDuplicateError(CompanyRepositoryError):
    pass


class CompanyRepository:
    """Data access for CompanyProfile entities."""

    def __init__(self, supabase: SupabaseService | None = None):
        self._supabase = supabase or SupabaseService()

    def create(
        self, company_name: str, brand_guidelines: str, brand_tone: str | None = None
    ) -> CompanyProfile:
        try:
            data = self._supabase.create_profile(company_name, brand_guidelines, brand_tone)
            return self._row_to_profile(data)
        except DuplicateCompanyError as e:
            raise CompanyDuplicateError(str(e)) from e
        except SupabaseServiceError as e:
            raise CompanyRepositoryError(str(e)) from e

    def get_by_id(self, profile_id: str) -> CompanyProfile:
        try:
            data = self._supabase.get_profile(profile_id)
            return self._row_to_profile(data)
        except NotFoundError as e:
            raise CompanyNotFoundError(str(e)) from e
        except SupabaseServiceError as e:
            raise CompanyRepositoryError(str(e)) from e

    def update(self, profile_id: str, data: dict[str, Any]) -> CompanyProfile:
        try:
            result = self._supabase.update_profile(profile_id, data)
            return self._row_to_profile(result)
        except NotFoundError as e:
            raise CompanyNotFoundError(str(e)) from e
        except DuplicateCompanyError as e:
            raise CompanyDuplicateError(str(e)) from e
        except SupabaseServiceError as e:
            raise CompanyRepositoryError(str(e)) from e

    def delete(self, profile_id: str) -> None:
        try:
            self._supabase.delete_profile(profile_id)
        except NotFoundError as e:
            raise CompanyNotFoundError(str(e)) from e
        except SupabaseServiceError as e:
            raise CompanyRepositoryError(str(e)) from e

    def list_all(self) -> list[CompanyProfile]:
        try:
            rows = self._supabase.list_profiles()
            return [self._row_to_profile(row) for row in rows]
        except SupabaseServiceError as e:
            raise CompanyRepositoryError(str(e)) from e

    def _row_to_profile(self, row: dict[str, Any]) -> CompanyProfile:
        return CompanyProfile(
            id=row.get("id", ""),
            company_name=row.get("company_name", ""),
            brand_guidelines=row.get("brand_guidelines", ""),
            brand_tone=row.get("brand_tone"),
            reference_image_urls=row.get("reference_image_urls", []),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )
