import pytest
from pydantic import ValidationError

from src.models.company import (
    CompanyProfile,
    CompanyProfileCreate,
    CompanyProfileResponse,
    CompanyProfileUpdate,
)


class TestCompanyProfileDataclass:
    def test_default_values(self) -> None:
        profile = CompanyProfile(
            company_name="Acme Corp", brand_guidelines="guidelines", brand_tone="Professional"
        )
        assert profile.company_name == "Acme Corp"
        assert profile.brand_guidelines == "guidelines"
        assert profile.brand_tone == "Professional"
        assert profile.reference_image_urls == []
        assert profile.id is not None

    def test_to_response(self) -> None:
        profile = CompanyProfile(
            company_name="Acme Corp", brand_guidelines="guidelines", brand_tone="Professional"
        )
        response = profile.to_response()
        assert isinstance(response, CompanyProfileResponse)
        assert response.company_name == "Acme Corp"
        assert response.brand_guidelines == "guidelines"
        assert response.brand_tone == "Professional"
        assert response.reference_image_urls == []

    def test_reference_image_urls_list(self) -> None:
        urls = ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
        profile = CompanyProfile(
            company_name="Acme Corp",
            brand_guidelines="guidelines",
            brand_tone="Professional",
            reference_image_urls=urls,
        )
        assert len(profile.reference_image_urls) == 2
        response = profile.to_response()
        assert response.reference_image_urls == urls


class TestCompanyProfileCreate:
    def test_valid_create(self) -> None:
        data = CompanyProfileCreate(
            company_name="Acme Corp", brand_guidelines="Use blue", brand_tone="Professional"
        )
        assert data.company_name == "Acme Corp"
        assert data.brand_guidelines == "Use blue"
        assert data.brand_tone == "Professional"

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            CompanyProfileCreate(
                company_name="", brand_guidelines="guidelines", brand_tone="Professional"
            )
        assert "company_name" in str(exc.value)

    def test_whitespace_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileCreate(
                company_name="   ", brand_guidelines="guidelines", brand_tone="Professional"
            )

    def test_empty_tone_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileCreate(
                company_name="Acme Corp", brand_guidelines="guidelines", brand_tone=""
            )

    def test_empty_guidelines_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileCreate(
                company_name="Acme Corp", brand_guidelines="", brand_tone="Professional"
            )


class TestCompanyProfileUpdate:
    def test_all_fields_optional(self) -> None:
        data = CompanyProfileUpdate()
        assert data.company_name is None
        assert data.brand_tone is None


class TestCompanyProfileResponse:
    def test_serialization_round_trip(self) -> None:
        original = CompanyProfileResponse(
            id="abc-123",
            company_name="Acme Corp",
            brand_guidelines="Use blue tones",
            brand_tone="Professional",
            reference_image_urls=["https://example.com/img.jpg"],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        json_str = original.model_dump_json()
        restored = CompanyProfileResponse.model_validate_json(json_str)
        assert restored.id == original.id
        assert restored.company_name == original.company_name
        assert restored.brand_tone == original.brand_tone
        assert restored.reference_image_urls == original.reference_image_urls
