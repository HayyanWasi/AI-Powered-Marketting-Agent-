import logging
from typing import Any

from src.models.company import CompanyProfile
from src.repositories.company_repository import (
    CompanyNotFoundError,
    CompanyRepository,
    CompanyRepositoryError,
)

logger = logging.getLogger(__name__)


class GetCompanyService:
    """Service for retrieving a single company profile by ID."""

    def __init__(self, repository: CompanyRepository | None = None):
        self._repository = repository or CompanyRepository()

    def execute(self, profile_id: str) -> dict[str, Any]:
        try:
            profile = self._repository.get_by_id(profile_id)
            return {
                "id": profile.id,
                "company_name": profile.company_name,
                "brand_guidelines": profile.brand_guidelines,
                "brand_tone": profile.brand_tone,
                "reference_image_urls": profile.reference_image_urls,
                "created_at": profile.created_at,
                "updated_at": profile.updated_at,
                "is_complete": profile.is_complete,
            }
        except CompanyNotFoundError as e:
            raise ValueError(str(e)) from e
        except CompanyRepositoryError as e:
            logger.error("Failed to get profile %s: %s", profile_id, e)
            raise
