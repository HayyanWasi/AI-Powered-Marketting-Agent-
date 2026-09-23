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

        if expected_version or "brand_guidelines" in data:
            try:
                current = self._repository.get_by_id(profile_id)
                if expected_version and current.updated_at != expected_version:
                    raise ValueError(
                        "This profile was modified by another user since you loaded it. "
                        "Please refresh and try your update again."
                    )

                # Merge brand guidelines without destroying unknowns
                if "brand_guidelines" in data:
                    from src.models.brand_context import BrandGuidelinesSchema

                    current_schema = BrandGuidelinesSchema.parse_and_migrate(
                        current.brand_guidelines
                    )
                    data["brand_guidelines"] = current_schema.merge_update(data["brand_guidelines"])

            except CompanyNotFoundError:
                if expected_version:
                    raise ValueError("Company profile not found. It may have been deleted.")
                # If we were just fetching it for merge and it's not found (shouldn't happen on update, but just in case)
                if "brand_guidelines" in data:
                    from src.models.brand_context import BrandGuidelinesSchema

                    data["brand_guidelines"] = BrandGuidelinesSchema.parse_and_migrate(
                        data["brand_guidelines"]
                    ).model_dump_json()

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
