import logging

from src.validators.company_validator import CompanyValidationError, CompanyValidator

logger = logging.getLogger(__name__)


class CompanyValidationService:
    """Service-level validation for company profile operations."""

    def __init__(self):
        self._validator = CompanyValidator()

    def validate_create(self, company_name: str, brand_guidelines: str) -> list[str]:
        errors: list[str] = []
        if not company_name or not company_name.strip():
            errors.append(
                "Please provide a company name in the 'company_name' field. "
                "This field is required and cannot be left blank."
            )
        if not brand_guidelines or not brand_guidelines.strip():
            errors.append(
                "Please provide brand guidelines in the 'brand_guidelines' field. "
                "This field tells the AI how to match your brand's style and voice."
            )
        return errors

    def validate_update(self, data: dict) -> list[str]:
        errors: list[str] = []
        if "company_name" in data:
            val = data["company_name"]
            if val is not None and (not isinstance(val, str) or not val.strip()):
                errors.append(
                    "The 'company_name' field cannot be empty. "
                    "If you want to keep the current name, remove it from the update request."
                )
        if "brand_guidelines" in data:
            val = data["brand_guidelines"]
            if val is not None and (not isinstance(val, str) or not val.strip()):
                errors.append(
                    "The 'brand_guidelines' field cannot be empty. "
                    "Brand guidelines tell the AI campaign generator about your brand's style and cannot be cleared."
                )
        return errors
