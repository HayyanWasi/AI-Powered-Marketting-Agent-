import logging
from typing import Any

from src.repositories.company_repository import CompanyRepository, CompanyRepositoryError

logger = logging.getLogger(__name__)


class ListCompanyService:
    """Service for listing all company profiles."""

    def __init__(self, repository: CompanyRepository | None = None):
        self._repository = repository or CompanyRepository()

    def execute(self) -> list[dict[str, Any]]:
        try:
            profiles = self._repository.list_all()
            return [
                {
                    "id": p.id,
                    "company_name": p.company_name,
                    "is_complete": p.is_complete,
                    "image_count": len(p.reference_image_urls),
                    "updated_at": p.updated_at,
                }
                for p in profiles
            ]
        except CompanyRepositoryError as e:
            logger.error("Failed to list profiles: %s", e)
            raise
