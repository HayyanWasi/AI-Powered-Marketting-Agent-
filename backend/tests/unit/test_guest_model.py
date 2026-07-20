import pytest
from pydantic import ValidationError

from src.models.guest import Guest, GuestCreate, GuestResponse, GuestUpdate


class TestGuestDataclass:
    def test_default_values(self) -> None:
        guest = Guest(name="Jane Doe")
        assert guest.name == "Jane Doe"
        assert guest.title == ""
        assert guest.company == ""
        assert guest.bio == ""
        assert guest.id is not None

    def test_all_fields_populated(self) -> None:
        guest = Guest(name="Jane Doe", title="Speaker", company="Acme Inc", bio="Expert")
        assert guest.name == "Jane Doe"
        assert guest.title == "Speaker"
        assert guest.company == "Acme Inc"
        assert guest.bio == "Expert"

    def test_to_response(self) -> None:
        guest = Guest(name="Jane Doe", title="Speaker")
        response = guest.to_response()
        assert isinstance(response, GuestResponse)
        assert response.name == "Jane Doe"
        assert response.title == "Speaker"


class TestGuestCreate:
    def test_valid_create(self) -> None:
        data = GuestCreate(name="Jane Doe", title="Speaker", company="Acme", bio="Bio text")
        assert data.name == "Jane Doe"
        assert data.title == "Speaker"
        assert data.company == "Acme"
        assert data.bio == "Bio text"

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            GuestCreate(name="")
        assert "name" in str(exc.value)

    def test_whitespace_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GuestCreate(name="   ")

    def test_optional_fields_omitted(self) -> None:
        data = GuestCreate(name="Jane Doe")
        assert data.title is None
        assert data.company is None
        assert data.bio is None

    def test_name_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GuestCreate(name="x" * 256)


class TestGuestUpdate:
    def test_all_fields_optional(self) -> None:
        data = GuestUpdate()
        assert data.name is None
        assert data.title is None
        assert data.company is None
        assert data.bio is None

    def test_partial_update(self) -> None:
        data = GuestUpdate(title="New Title")
        assert data.title == "New Title"
        assert data.name is None


class TestGuestResponse:
    def test_serialization_round_trip(self) -> None:
        original = GuestResponse(
            id="abc-123",
            name="Jane",
            title="Speaker",
            company="Acme",
            bio="Bio",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        json_str = original.model_dump_json()
        restored = GuestResponse.model_validate_json(json_str)
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.title == original.title
        assert restored.company == original.company
        assert restored.bio == original.bio

    def test_optional_fields_none(self) -> None:
        response = GuestResponse(
            id="abc",
            name="Jane",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        assert response.title is None
        assert response.company is None
        assert response.bio is None
