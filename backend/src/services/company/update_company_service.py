import logging
from typing import Any

from src.models.company import CompanyProfile
from src.repositories.company_repository import (
    CompanyDuplicateError,
    CompanyNotFoundError,
    CompanyRepository,
    CompanyRepositoryError,
)
from src.services.company.company_validation_service import CompanyValidationService

logger = logging.getLogger(__name__)


class UpdateCompanyService:
    """Service for updating existing company profiles.

    Uses optimistic concurrency via updated_at to prevent lost updates.
    """

    def __init__(
        self,
        repository: CompanyRepository | None = None,
        validation: CompanyValidationService | None = None,
    ):
        self._repository = repository or CompanyRepository()
        self._validation = validation or CompanyValidationService()

    def execute(
        self, profile_id: str, data: dict[str, Any], expected_version: str | None = None
    ) -> CompanyProfile:
        if not data:
            raise ValueError("No fields to update")

        errors = self._validation.validate_update(data)
        if errors:
            raise ValueError("; ".join(errors))

        if expected_version:
            try:
                current = self._repository.get_by_id(profile_id)
                if current.updated_at != expected_version:
                    raise ValueError(
                        "This profile was modified by another user since you loaded it. "
                        "Please refresh and try your update again."
                    )
            except CompanyNotFoundError:
                raise ValueError("Company profile not found. It may have been deleted.")

        try:
            profile = self._repository.update(profile_id, data)
            logger.info("Updated company profile: %s", profile_id)
            return profile
        except CompanyNotFoundError as e:
            raise ValueError(str(e)) from e
        except CompanyDuplicateError as e:
            raise ValueError(
                f"Company name '{data.get('company_name', '')}' is already in use. "
                "Please choose a different name."
            ) from e
        except CompanyRepositoryError as e:
            logger.error("Failed to update profile %s: %s", profile_id, e)
            raise
