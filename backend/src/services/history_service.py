"""Campaign history service."""

from uuid import UUID

from src.models.campaign import Campaign, CampaignState
from src.models.history import CampaignHistoryEntry, EventType
from src.repositories.history_repository import HistoryRepository


class HistoryService:
    """Service for managing immutable campaign history."""

    def __init__(self, history_repository: HistoryRepository | None = None):
        self.history_repository = history_repository or HistoryRepository()

    async def log_creation(self, campaign: Campaign, actor_id: UUID) -> CampaignHistoryEntry:
        """Log campaign creation."""
        entry = CampaignHistoryEntry(
            campaign_id=campaign.id,
            event_type=EventType.CREATED,
            actor_id=actor_id,
            from_state=None,
            to_state=CampaignState.DRAFT,
            snapshot=campaign.to_dict(),
        )
        return await self.history_repository.create(entry)

    async def log_configuration_change(
        self,
        campaign: Campaign,
        actor_id: UUID,
        changed_fields: dict,
    ) -> CampaignHistoryEntry:
        """Log configuration change with field-level diff."""
        entry = CampaignHistoryEntry(
            campaign_id=campaign.id,
            event_type=EventType.CONFIGURATION_CHANGED,
            actor_id=actor_id,
            changed_fields=changed_fields,
            snapshot=campaign.to_dict(),
        )
        return await self.history_repository.create(entry)

    async def log_state_transition(
        self,
        campaign: Campaign,
        actor_id: UUID,
        from_state: CampaignState,
        to_state: CampaignState,
        reason: str | None = None,
    ) -> CampaignHistoryEntry:
        """Log state transition."""
        metadata = {"reason": reason} if reason else None
        entry = CampaignHistoryEntry(
            campaign_id=campaign.id,
            event_type=EventType.STATE_TRANSITIONED,
            actor_id=actor_id,
            from_state=from_state,
            to_state=to_state,
            metadata=metadata,
            snapshot=campaign.to_dict(),
        )
        return await self.history_repository.create(entry)

    async def log_publication(
        self,
        campaign: Campaign,
        actor_id: UUID,
    ) -> CampaignHistoryEntry:
        """Log publication event with full snapshot."""
        entry = CampaignHistoryEntry(
            campaign_id=campaign.id,
            event_type=EventType.PUBLISHED,
            actor_id=actor_id,
            from_state=CampaignState.APPROVED,
            to_state=CampaignState.PUBLISHED,
            snapshot=campaign.to_dict(),
        )
        return await self.history_repository.create(entry)

    async def log_archive(
        self,
        campaign: Campaign,
        actor_id: UUID,
        reason: str | None = None,
    ) -> CampaignHistoryEntry:
        """Log archive event."""
        metadata = {"reason": reason} if reason else None
        entry = CampaignHistoryEntry(
            campaign_id=campaign.id,
            event_type=EventType.ARCHIVED,
            actor_id=actor_id,
            from_state=campaign.state,
            to_state=CampaignState.ARCHIVED,
            metadata=metadata,
            snapshot=campaign.to_dict(),
        )
        return await self.history_repository.create(entry)

    async def log_restore(
        self,
        campaign: Campaign,
        actor_id: UUID,
    ) -> CampaignHistoryEntry:
        """Log restore event."""
        entry = CampaignHistoryEntry(
            campaign_id=campaign.id,
            event_type=EventType.RESTORED,
            actor_id=actor_id,
            from_state=CampaignState.ARCHIVED,
            to_state=campaign.state,
            snapshot=campaign.to_dict(),
        )
        return await self.history_repository.create(entry)

    async def log_asset_association(
        self,
        campaign_id: UUID,
        actor_id: UUID,
        asset_type: str,
        asset_id: UUID,
    ) -> CampaignHistoryEntry:
        """Log asset association."""
        entry = CampaignHistoryEntry(
            campaign_id=campaign_id,
            event_type=EventType.ASSET_ASSOCIATED,
            actor_id=actor_id,
            metadata={"asset_type": asset_type, "asset_id": str(asset_id)},
        )
        return await self.history_repository.create(entry)

    async def get_history(
        self,
        campaign_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> list[CampaignHistoryEntry]:
        """Get paginated history for a campaign."""
        return await self.history_repository.get_by_campaign(campaign_id, page, page_size)

    async def get_total_history_count(self, campaign_id: UUID) -> int:
        """Get total history count for a campaign."""
        return await self.history_repository.count_by_campaign(campaign_id)
