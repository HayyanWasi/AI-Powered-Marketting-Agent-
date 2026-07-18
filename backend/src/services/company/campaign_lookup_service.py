import logging
from typing import Any

from src.repositories.company_repository import (
    CompanyNotFoundError,
    CompanyRepository,
    CompanyRepositoryError,
)

logger = logging.getLogger(__name__)


class CampaignLookupService:
    """Provides company brand information for Campaign Generation.

    Validates that the profile is complete before returning brand data.
    """

    def __init__(self, repository: CompanyRepository | None = None):
        self._repository = repository or CompanyRepository()

    def execute(self, profile_id: str) -> dict[str, Any]:
        try:
            profile = self._repository.get_by_id(profile_id)
        except CompanyNotFoundError as e:
            raise ValueError(str(e)) from e
        except CompanyRepositoryError as e:
            logger.error("Failed to fetch profile %s: %s", profile_id, e)
            raise

        if not profile.is_complete:
            raise ValueError(
                "Company profile is incomplete — brand guidelines are required "
                "before this profile can be used for campaign generation."
            )

        return {
            "id": profile.id,
            "company_name": profile.company_name,
            "brand_guidelines": profile.brand_guidelines,
            "brand_tone": profile.brand_tone,
            "reference_image_urls": profile.reference_image_urls,
            "is_complete": True,
        }
