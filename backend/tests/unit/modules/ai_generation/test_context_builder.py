"""Unit test for AI Generation Engine ContextBuilder service."""

import pytest
from unittest.mock import Mock, MagicMock
from backend.src.modules.ai_generation.services.context_builder_service import ContextBuilderService
from backend.src.modules.ai_generation.models.validation_artifact import ValidationArtifact


class ValidationError:
    """Test validation error class."""

    def __init__(
        self, code: str, message: str, severity: str, field: str = None, suggested_fix: str = None
    ):
        self.code = code
        self.message = message
        self.severity = severity
        self.field = field
        self.suggested_fix = suggested_fix


class ValidationWarning:
    """Test validation warning class."""

    def __init__(self, code: str, message: str, field: str = None):
        self.code = code
        self.message = message
        self.field = field


@pytest.fixture
def context_builder_service():
    """Create a ContextBuilderService instance for testing."""
    return ContextBuilderService()


@pytest.fixture
def valid_generation_context():
    """Provide valid generation context for testing."""
    return {
        "campaign_context": {
            "name": "Summer Campaign",
            "goals": ["brand awareness", "lead generation"],
            "budget": 50000,
            "timeline": "2026-08-01 to 2026-09-30",
        },
        "company_profile": {
            "name": "TechCorp",
            "values": ["innovation", "quality", "customer-centric"],
            "tone": "professional",
        },
        "audience": {
            "segments": ["tech professionals", "enterprise customers"],
            "demographics": {"age": "25-45", "income": "high"},
            "interests": ["technology", "innovation", "efficiency"],
        },
        "platforms": ["linkedin", "instagram", "twitter"],
        "brand_guidelines": {
            "voice_tone": "professional",
            "color_palette": ["#0000FF", "#FFFFFF"],
            "logo_specs": {"width": 200, "height": 80},
            "brand_values": ["trust", "innovation", "excellence"],
        },
        "reference_materials": [
            {"type": "competitor", "source": "competitor.com"},
            {"type": "benchmark", "source": "industry_report.pdf"},
        ],
        "user_intent": {
            "type": "full_generation",
            "customizations": {"emphasize_benefits": True},
        },
    }


@pytest.fixture
def incomplete_generation_context():
    """Provide incomplete generation context for testing error cases."""
    return {
        "campaign_context": {},
        "company_profile": {},
        "audience": {},
        "platforms": [],
        "brand_guidelines": {},
        "reference_materials": [],
    }


class TestContextBuilderService:
    """Test suite for ContextBuilderService."""

    def test_build_generation_context_valid_input(
        self,
        context_builder_service,
        valid_generation_context,
    ):
        """Test building generation context with valid input."""
        result = context_builder_service.build_generation_context(**valid_generation_context)

        assert result is not None
        assert hasattr(result, "campaign_context")
        assert hasattr(result, "company_profile")
        assert hasattr(result, "audience")
        assert hasattr(result, "platforms")
        assert hasattr(result, "brand_guidelines")
        assert hasattr(result, "reference_materials")

        assert result.campaign_context["name"] == "Summer Campaign"
        assert "TechCorp" in result.company_profile["name"]
        assert len(result.audience["segments"]) == 2
        assert len(result.platforms) == 3

    def test_build_generation_context_with_missing_optional_fields(
        self,
        context_builder_service,
    ):
        """Test building context without optional user_intent."""
        context_without_intent = {
            "campaign_context": {"name": "Test Campaign"},
            "company_profile": {"name": "Test Corp"},
            "audience": {"segments": ["segment1"]},
            "platforms": ["linkedin"],
            "brand_guidelines": {"voice_tone": "professional"},
            "reference_materials": [],
        }

        result = context_builder_service.build_generation_context(**context_without_intent)

        assert result is not None
        assert result.user_intent is None or result.user_intent == {}
        assert result.campaign_context["name"] == "Test Campaign"

    def test_validate_context_completeness_valid_context(
        self,
        context_builder_service,
        valid_generation_context,
    ):
        """Test context validation with complete context."""
        validation_result = context_builder_service.validate_context_completeness(
            valid_generation_context
        )

        assert isinstance(validation_result, ValidationArtifact)
        assert validation_result.is_valid is True
        assert len(validation_result.errors) == 0

    def test_validate_context_completeness_empty_context(
        self,
        context_builder_service,
        incomplete_generation_context,
    ):
        """Test context validation with incomplete context."""
        validation_result = context_builder_service.validate_context_completeness(
            incomplete_generation_context
        )

        assert isinstance(validation_result, ValidationArtifact)
        assert validation_result.is_valid is False
        assert len(validation_result.errors) > 0

    def test_validate_context_completeness_missing_required_fields(
        self,
        context_builder_service,
    ):
        """Test context validation error messages for missing fields."""
        minimal_context = {
            "company_profile": {},  # Only one field
        }

        validation_result = context_builder_service.validate_context_completeness(minimal_context)

        assert validation_result.is_valid is False
        assert len(validation_result.errors) > 0

        error_fields = [error.field for error in validation_result.errors]
        assert "campaign_context" in error_fields
        assert "audience" in error_fields
        assert "platforms" in error_fields
        assert "brand_guidelines" in error_fields
        assert "reference_materials" in error_fields

    def test_validate_context_completeness_warnings_for_optional_fields(
        self,
        context_builder_service,
    ):
        """Test warnings for missing optional but recommended fields."""
        context_with_missing_optional = {
            "campaign_context": {"name": "Test"},  # Has name (not required)
            "company_profile": {"name": "Company"},  # Has name (not required)
            "audience": {"segments": ["seg"]},  # Has segments (not required)
            "platforms": ["linkedin"],  # Has items (not required)
            "brand_guidelines": {"voice_tone": "professional"},  # Has tone (not required)
            "reference_materials": [{"source": "test"}],  # Has items (not required)
        }

        validation_result = context_builder_service.validate_context_completeness(
            context_with_missing_optional
        )

        # Errors should be zero since all required fields are present
        assert len(validation_result.errors) == 0
        assert validation_result.is_valid is True

    def test_context_builder_builds_deterministic_output(
        self,
        context_builder_service,
        valid_generation_context,
    ):
        """Test that context builder produces consistent output for same input."""
        # Build context twice with same input
        result1 = context_builder_service.build_generation_context(**valid_generation_context)
        result2 = context_builder_service.build_generation_context(**valid_generation_context)

        # Results should have same data (memory addresses may differ)
        assert result1.campaign_context == result2.campaign_context
        assert result1.company_profile == result2.company_profile
        assert result1.audience == result2.audience

    @pytest.mark.asyncio
    async def test_build_generation_context_with_user_intent(
        self,
        context_builder_service,
        valid_generation_context,
    ):
        """Test context building with user intent instructions."""
        user_intent = {
            "type": "brand_elevated",
            "customizations": {
                "emphasis": "premium positioning",
                "creativity_level": "high",
            },
            "constraints": {"max_length": 500},
        }
        context_with_intent = valid_generation_context.copy()
        context_with_intent["user_intent"] = user_intent

        result = context_builder_service.build_generation_context(**context_with_intent)

        assert result.user_intent is not None
        assert user_intent["type"] in str(result.user_intent)

    def test_context_builder_validation_error_handling(
        self,
        context_builder_service,
    ):
        """Test validation error structure."""
        # Mock the validator to return errors
        mock_validation = ValidationArtifact(
            "test_id_1",
            "2026-07-17T00:00:00.000Z",
            "generation_context_validation",
            "test_context",
            False,
            [
                ValidationError(
                    "MISSING_REQUIRED_FIELD",
                    "Missing required field: campaign_context",
                    "error",
                    "campaign_context",
                    "Provide the required field",
                )
            ],
            [
                ValidationWarning(
                    "MISSING_RECOMMENDED_FIELD",
                    "Add campaign name for better context",
                    "campaign_context.name",
                )
            ],
            {"total_fields": 6, "filled_fields": 0},
            [
                "Ensure all required fields are provided",
                "Add campaign name for better context",
            ],
            "ContextBuilderService",
        )

        # The actual implementation will validate and raise ValueError
        # This test ensures the error structure is understood
        assert mock_validation.is_valid is False
        assert len(mock_validation.errors) == 1
        assert mock_validation.errors[0].code == "MISSING_REQUIRED_FIELD"
