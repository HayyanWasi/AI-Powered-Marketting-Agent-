"""Tests for Campaign model and related dataclasses."""

from datetime import datetime
from uuid import uuid4

from src.models.campaign import (
    AssetSource,
    AssetType,
    Campaign,
    CampaignAsset,
    CampaignState,
    Goals,
    Schedule,
    TargetAudience,
)


class TestCampaignState:
    def test_valid_states_exist(self) -> None:
        assert CampaignState.DRAFT.value == "Draft"
        assert CampaignState.READY.value == "Ready"
        assert CampaignState.REVIEW.value == "Review"
        assert CampaignState.APPROVED.value == "Approved"
        assert CampaignState.PUBLISHED.value == "Published"
        assert CampaignState.ARCHIVED.value == "Archived"

    def test_all_six_states(self) -> None:
        assert len(CampaignState) == 6


class TestCampaign:
    def test_create_campaign_with_defaults(self) -> None:
        campaign = Campaign()
        assert campaign.id is not None
        assert campaign.name == ""
        assert campaign.state == CampaignState.DRAFT
        assert campaign.version == 1

    def test_create_campaign_with_fields(self) -> None:
        org_id = uuid4()
        campaign = Campaign(
            organization_id=org_id,
            name="Test Campaign",
            goals=Goals(primary="Increase sales"),
            target_audience=TargetAudience(segments=["customers"]),
            platforms=["linkedin", "instagram"],
            schedule=Schedule(
                start_date=datetime(2026, 1, 1),
                end_date=datetime(2026, 12, 31),
                timezone="UTC",
            ),
        )
        assert campaign.organization_id == org_id
        assert campaign.name == "Test Campaign"
        assert campaign.state == CampaignState.DRAFT
        assert campaign.version == 1
        assert "linkedin" in campaign.platforms

    def test_campaign_to_dict(self) -> None:
        campaign = Campaign(name="Test", organization_id=uuid4())
        data = campaign.to_dict()
        assert data["name"] == "Test"
        assert data["state"] == "Draft"


class TestCampaignAsset:
    def test_create_asset(self) -> None:
        asset = CampaignAsset(
            campaign_id=uuid4(),
            asset_type=AssetType.COPY,
            content={"text": "Hello world"},
            source=AssetSource.AI,
        )
        assert asset.asset_type == AssetType.COPY
        assert asset.source == AssetSource.AI
        assert asset.content["text"] == "Hello world"

    def test_asset_types(self) -> None:
        assert AssetType.COPY.value == "copy"
        assert AssetType.IMAGE.value == "image"
        assert AssetType.HASHTAG_SET.value == "hashtag_set"
        assert AssetType.METADATA.value == "metadata"
        assert AssetType.OTHER.value == "other"

    def test_asset_sources(self) -> None:
        assert AssetSource.AI.value == "ai"
        assert AssetSource.MANUAL.value == "manual"
        assert AssetSource.IMPORTED.value == "imported"


class TestGoals:
    def test_goals_with_primary(self) -> None:
        goals = Goals(primary="Increase brand awareness")
        assert goals.primary == "Increase brand awareness"
        assert goals.metrics == []
        assert goals.targets == {}

    def test_goals_with_values(self) -> None:
        goals = Goals(
            primary="Increase brand awareness",
            metrics=["impressions", "clicks"],
            targets={"impressions": 10000},
        )
        assert goals.primary == "Increase brand awareness"
        assert len(goals.metrics) == 2


class TestTargetAudience:
    def test_audience_with_segments(self) -> None:
        audience = TargetAudience(segments=["tech professionals"])
        assert "tech professionals" in audience.segments

    def test_audience_with_values(self) -> None:
        audience = TargetAudience(
            segments=["tech professionals"],
            demographics={"age": "25-45"},
            interests=["AI", "marketing"],
        )
        assert "tech professionals" in audience.segments
        assert audience.demographics["age"] == "25-45"


class TestSchedule:
    def test_schedule_with_dates(self) -> None:
        schedule = Schedule(
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 12, 31),
            timezone="America/New_York",
        )
        assert schedule.start_date.year == 2026
        assert schedule.timezone == "America/New_York"
