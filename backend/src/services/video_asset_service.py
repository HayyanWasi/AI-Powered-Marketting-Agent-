"""Atomic persistence for generated campaign videos and scheduler drafts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from src.models.campaign import Campaign
from src.repositories.base import BaseRepository


class VideoAssetPersistenceError(RuntimeError):
    pass


class VideoAssetService:
    def __init__(self, repository: BaseRepository | None = None) -> None:
        self._repository = repository or BaseRepository("campaign_assets")

    @staticmethod
    def initial_schedule(campaign: Campaign) -> tuple[datetime, str]:
        timezone_name = campaign.schedule.timezone if campaign.schedule else "UTC"
        try:
            timezone = ZoneInfo(timezone_name)
        except Exception as exc:
            raise ValueError(f"Invalid campaign timezone: {timezone_name}") from exc

        now_local = datetime.now(UTC).astimezone(timezone)
        campaign_start = campaign.schedule.start_date if campaign.schedule else None
        if campaign_start and campaign_start.tzinfo is None:
            campaign_start = campaign_start.replace(tzinfo=timezone)
        initial = max(now_local + timedelta(hours=1), campaign_start or now_local)
        return initial.astimezone(UTC), timezone_name

    def persist(
        self,
        *,
        campaign: Campaign,
        user_id: UUID,
        media_url: str,
        storage_path: str,
        prompt: str,
        scenes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        scheduled_at, timezone_name = self.initial_schedule(campaign)
        caption = prompt.strip() or f"{campaign.name} video"
        content = {
            "media_url": media_url,
            "mime_type": "video/mp4",
            "prompt": prompt,
            "scenes": scenes,
        }
        try:
            result = self._repository.client.rpc(
                "create_campaign_video_draft",
                {
                    "p_campaign_id": str(campaign.id),
                    "p_user_id": str(user_id),
                    "p_content": content,
                    "p_storage_path": storage_path,
                    "p_media_url": media_url,
                    "p_scheduled_at": scheduled_at.isoformat(),
                    "p_timezone": timezone_name,
                    "p_caption": caption,
                },
            ).execute()
        except Exception as exc:
            raise VideoAssetPersistenceError(
                "The video was rendered but could not be attached to the campaign scheduler."
            ) from exc
        if not result.data or not result.data.get("asset") or not result.data.get("post"):
            raise VideoAssetPersistenceError(
                "The video was rendered but campaign asset persistence was incomplete."
            )
        return result.data
