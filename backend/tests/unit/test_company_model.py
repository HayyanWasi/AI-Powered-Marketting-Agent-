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
        profile = CompanyProfile(name="Acme Corp", tone="Professional")
        assert profile.name == "Acme Corp"
        assert profile.tone == "Professional"
        assert profile.reference_image_urls == []
        assert profile.id is not None

    def test_to_response(self) -> None:
        profile = CompanyProfile(name="Acme Corp", tone="Professional")
        response = profile.to_response()
        assert isinstance(response, CompanyProfileResponse)
        assert response.name == "Acme Corp"
        assert response.tone == "Professional"
        assert response.reference_image_urls == []

    def test_reference_image_urls_list(self) -> None:
        urls = ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
        profile = CompanyProfile(name="Acme Corp", tone="Professional", reference_image_urls=urls)
        assert len(profile.reference_image_urls) == 2
        response = profile.to_response()
        assert response.reference_image_urls == urls


class TestCompanyProfileCreate:
    def test_valid_create(self) -> None:
        data = CompanyProfileCreate(name="Acme Corp", tone="Professional")
        assert data.name == "Acme Corp"
        assert data.tone == "Professional"

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            CompanyProfileCreate(name="", tone="Professional")
        assert "name" in str(exc.value)

    def test_whitespace_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileCreate(name="   ", tone="Professional")

    def test_empty_tone_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompanyProfileCreate(name="Acme Corp", tone="")


class TestCompanyProfileUpdate:
    def test_all_fields_optional(self) -> None:
        data = CompanyProfileUpdate()
        assert data.name is None
        assert data.tone is None


class TestCompanyProfileResponse:
    def test_serialization_round_trip(self) -> None:
        original = CompanyProfileResponse(
            id="abc-123",
            name="Acme Corp",
            tone="Professional",
            reference_image_urls=["https://example.com/img.jpg"],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        json_str = original.model_dump_json()
        restored = CompanyProfileResponse.model_validate_json(json_str)
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.tone == original.tone
        assert restored.reference_image_urls == original.reference_image_urls
