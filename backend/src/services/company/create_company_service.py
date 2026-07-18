import logging

from src.models.company import CompanyProfile
from src.repositories.company_repository import (
    CompanyDuplicateError,
    CompanyNotFoundError,
    CompanyRepository,
    CompanyRepositoryError,
)
from src.services.company.company_validation_service import CompanyValidationService

logger = logging.getLogger(__name__)


class CreateCompanyService:
    """Service for creating new company profiles."""

    def __init__(
        self,
        repository: CompanyRepository | None = None,
        validation: CompanyValidationService | None = None,
    ):
        self._repository = repository or CompanyRepository()
        self._validation = validation or CompanyValidationService()

    def execute(
        self, company_name: str, brand_guidelines: str, brand_tone: str | None = None
    ) -> CompanyProfile:
        errors = self._validation.validate_create(company_name, brand_guidelines)
        if errors:
            raise ValueError("; ".join(errors))

        try:
            profile = self._repository.create(company_name, brand_guidelines, brand_tone)
            logger.info("Created company profile: %s (%s)", profile.company_name, profile.id)
            return profile
        except CompanyDuplicateError as e:
            raise ValueError(str(e)) from e
        except CompanyRepositoryError as e:
            logger.error("Failed to create profile: %s", e)
            raise
