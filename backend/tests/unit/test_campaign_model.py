from pydantic import HttpUrl, ValidationError

import pytest

from src.models.campaign import Campaign, CampaignCreate, CampaignResponse, CampaignUpdate


class TestCampaignDataclass:
    def test_default_values(self) -> None:
        campaign = Campaign(type="speaker_promo", caption="Check this out")
        assert campaign.type == "speaker_promo"
        assert campaign.caption == "Check this out"
        assert campaign.image_url == ""
        assert campaign.status == "draft"

    def test_to_response(self) -> None:
        campaign = Campaign(type="speaker_promo", caption="Caption")
        response = campaign.to_response()
        assert isinstance(response, CampaignResponse)
        assert response.type == "speaker_promo"
        assert response.caption == "Caption"
        assert response.status == "draft"


class TestCampaignCreate:
    def test_valid_create(self) -> None:
        data = CampaignCreate(type="speaker_promo", caption="Great event!")
        assert data.type == "speaker_promo"
        assert data.caption == "Great event!"
        assert data.status == "draft"

    def test_empty_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CampaignCreate(type="", caption="Caption")

    def test_empty_caption_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CampaignCreate(type="speaker_promo", caption="")

    def test_whitespace_caption_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CampaignCreate(type="speaker_promo", caption="   ")

    def test_status_defaults_to_draft(self) -> None:
        data = CampaignCreate(type="speaker_promo", caption="Caption")
        assert data.status == "draft"

    def test_valid_status_accepted(self) -> None:
        for status in ("draft", "published", "archived"):
            data = CampaignCreate(type="speaker_promo", caption="Caption", status=status)
            assert data.status == status

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CampaignCreate(type="speaker_promo", caption="Caption", status="deleted")

    def test_valid_url_accepted(self) -> None:
        url = HttpUrl("https://example.com/image.jpg")
        data = CampaignCreate(
            type="speaker_promo",
            caption="Caption",
            image_url=url,
        )
        assert data.image_url is not None

    def test_invalid_url_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CampaignCreate(
                type="speaker_promo",
                caption="Caption",
                image_url="not-a-url",  # type: ignore[arg-type]
            )


class TestCampaignUpdate:
    def test_all_fields_optional(self) -> None:
        data = CampaignUpdate()
        assert data.type is None
        assert data.caption is None
        assert data.image_url is None
        assert data.status is None


class TestCampaignResponse:
    def test_serialization_round_trip(self) -> None:
        original = CampaignResponse(
            id="abc-123",
            type="speaker_promo",
            caption="Great event!",
            image_url="https://example.com/img.jpg",
            status="published",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        json_str = original.model_dump_json()
        restored = CampaignResponse.model_validate_json(json_str)
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.caption == original.caption
        assert restored.image_url == original.image_url
        assert restored.status == original.status

    def test_optional_image_url_none(self) -> None:
        response = CampaignResponse(
            id="abc",
            type="speaker_promo",
            caption="Caption",
            status="draft",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        assert response.image_url is None
