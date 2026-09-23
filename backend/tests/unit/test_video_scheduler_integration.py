from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from src.models.campaign import Campaign, Schedule
from src.services.video_asset_service import VideoAssetPersistenceError, VideoAssetService


class _Result:
    def __init__(self, data):
        self.data = data


class _Rpc:
    def __init__(self, result):
        self.result = result

    def execute(self):
        if isinstance(self.result, Exception):
            raise self.result
        return _Result(self.result)


class _Client:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        return _Rpc(self.result)


class _Repository:
    def __init__(self, result):
        self.client = _Client(result)


def _campaign() -> Campaign:
    return Campaign(
        id=uuid4(),
        organization_id=uuid4(),
        name="Video Sentinel",
        schedule=Schedule(
            start_date=datetime.now(UTC) + timedelta(days=1),
            end_date=datetime.now(UTC) + timedelta(days=8),
            timezone="Asia/Karachi",
        ),
    )


def test_generated_video_is_persisted_as_asset_and_linked_draft():
    repository = _Repository({
        "asset": {"id": str(uuid4()), "asset_type": "video"},
        "post": {"id": str(uuid4()), "status": "draft", "media_type": "video"},
    })
    campaign = _campaign()
    user_id = campaign.organization_id

    result = VideoAssetService(repository).persist(
        campaign=campaign,
        user_id=user_id,
        media_url="https://assets.invalid/video.mp4",
        storage_path=f"{campaign.id}/video.mp4",
        prompt="Launch video caption",
        scenes=[{"narration": "Hello", "image_prompt": "Scene"}],
    )

    assert result["asset"]["asset_type"] == "video"
    assert result["post"]["status"] == "draft"
    name, params = repository.client.calls[0]
    assert name == "create_campaign_video_draft"
    assert params["p_campaign_id"] == str(campaign.id)
    assert params["p_user_id"] == str(user_id)
    assert params["p_media_url"] == "https://assets.invalid/video.mp4"
    assert params["p_caption"] == "Launch video caption"
    assert params["p_timezone"] == "Asia/Karachi"


def test_incomplete_atomic_result_is_truthful_failure():
    with pytest.raises(VideoAssetPersistenceError, match="persistence was incomplete"):
        VideoAssetService(_Repository({"asset": {"id": str(uuid4())}})).persist(
            campaign=_campaign(),
            user_id=uuid4(),
            media_url="https://assets.invalid/video.mp4",
            storage_path="campaign/video.mp4",
            prompt="Caption",
            scenes=[],
        )


def test_migration_preserves_media_drafts_during_copy_regeneration():
    migration = (
        Path(__file__).parents[2]
        / "migrations"
        / "017_attach_video_assets_to_linkedin_drafts.up.sql"
    ).read_text(encoding="utf-8")
    assert "campaign_asset_id IS NULL" in migration
    assert "create_campaign_video_draft" in migration
    assert "SECURITY INVOKER" in migration
