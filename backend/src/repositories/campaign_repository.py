"""Campaign repository - data access for campaigns."""

from typing import List, Optional, Tuple
from uuid import UUID
from datetime import datetime
from src.repositories.base import BaseRepository
from src.models.campaign import Campaign, CampaignState, Goals, TargetAudience, Schedule
from src.models.campaign import CampaignAsset, AssetType, AssetSource


class CampaignRepository(BaseRepository):
    """Data access for campaigns."""

    def __init__(self):
        super().__init__("campaigns")

    async def create(self, campaign: Campaign) -> Campaign:
        """Create a new campaign."""
        data = campaign.to_dict()
        # Remove None values for insert
        data = {k: v for k, v in data.items() if v is not None}

        result = await self.client.table(self.table_name).insert(data).execute()
        if result.data:
            return self._to_model(result.data[0], Campaign)
        raise Exception("Failed to create campaign")

    async def get_by_id(
        self, campaign_id: UUID, organization_id: UUID | None = None
    ) -> Optional[Campaign]:
        """Get campaign by ID, optionally filtered by organization."""
        query = self.client.table(self.table_name).select("*").eq("id", str(campaign_id))
        if organization_id:
            query = query.eq("organization_id", str(organization_id))
        result = await query.execute()

        if result.data:
            return self._to_model(result.data[0], Campaign)
        return None

    async def get_by_name(self, name: str, organization_id: UUID) -> Optional[Campaign]:
        """Check if campaign name exists in organization."""
        result = (
            await self.client.table(self.table_name)
            .select("*")
            .eq("name", name)
            .eq("organization_id", str(organization_id))
            .execute()
        )

        if result.data:
            return self._to_model(result.data[0], Campaign)
        return None

    async def get_with_assets(
        self, campaign_id: UUID, organization_id: UUID | None = None
    ) -> Optional[Campaign]:
        """Get campaign with associated assets."""
        campaign = await self.get_by_id(campaign_id, organization_id)
        if campaign:
            # Assets are loaded separately via asset repository
            pass
        return campaign

    async def update(self, campaign: Campaign, expected_version: int) -> Campaign:
        """Update campaign with optimistic locking."""
        data = campaign.to_dict()
        data = {k: v for k, v in data.items() if v is not None}

        result = (
            await self.client.table(self.table_name)
            .update(data)
            .eq("id", str(campaign.id))
            .eq("version", expected_version)
            .execute()
        )

        if result.data:
            return self._to_model(result.data[0], Campaign)
        raise Exception("Version conflict or campaign not found")

    async def delete(self, campaign_id: UUID, organization_id: UUID) -> bool:
        """Delete campaign (Draft only)."""
        result = (
            await self.client.table(self.table_name)
            .delete()
            .eq("id", str(campaign_id))
            .eq("organization_id", str(organization_id))
            .execute()
        )

        return len(result.data) > 0

    async def list(
        self,
        organization_id: UUID,
        state: Optional[CampaignState] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        owner_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Campaign], int]:
        """List campaigns with filters and pagination."""
        query = (
            self.client.table(self.table_name)
            .select("*", count="exact")
            .eq("organization_id", str(organization_id))
        )

        if state:
            query = query.eq("state", state.value)
        if start_date:
            query = query.gte("created_at", start_date.isoformat())
        if end_date:
            query = query.lte("created_at", end_date.isoformat())
        if owner_id:
            query = query.eq("created_by", str(owner_id))

        # Default ordering
        query = query.order("updated_at", desc=True)

        # Pagination
        offset = (page - 1) * page_size
        query = query.range(offset, offset + page_size - 1)

        result = await query.execute()

        campaigns = [self._to_model(item, Campaign) for item in result.data]
        total = result.count or 0

        return campaigns, total

    async def archive(
        self, campaign_id: UUID, organization_id: UUID, previous_state: CampaignState
    ) -> Optional[Campaign]:
        """Archive a campaign, storing previous state."""
        data = {
            "state": "Archived",
            "previous_state": previous_state.value,
            "archived_at": datetime.utcnow().isoformat(),
            "version": CampaignRepository._get_next_version(),  # Will be incremented by DB
        }

        result = (
            await self.client.table(self.table_name)
            .update(data)
            .eq("id", str(campaign_id))
            .eq("organization_id", str(organization_id))
            .execute()
        )

        if result.data:
            return self._to_model(result.data[0], Campaign)
        return None

    async def restore(self, campaign_id: UUID, organization_id: UUID) -> Optional[Campaign]:
        """Restore archived campaign to previous state."""
        # First get the campaign to find previous_state
        campaign = await self.get_by_id(campaign_id, organization_id)
        if not campaign or campaign.state != CampaignState.ARCHIVED:
            return None

        previous_state = campaign.previous_state or CampaignState.DRAFT

        data = {
            "state": previous_state.value,
            "previous_state": None,
            "archived_at": None,
            "version": CampaignRepository._get_next_version(),
        }

        result = (
            await self.client.table(self.table_name)
            .update(data)
            .eq("id", str(campaign_id))
            .eq("organization_id", str(organization_id))
            .execute()
        )

        if result.data:
            return self._to_model(result.data[0], Campaign)
        return None

    @staticmethod
    def _get_next_version() -> int:
        """Get next version - actual increment handled by database."""
        return 1  # Placeholder - actual version handled by DB trigger

    def _to_model(self, data: dict, model_class: type) -> Campaign:
        """Convert database dict to Campaign model."""
        if model_class == Campaign:
            return Campaign.from_dict(data)
        return super()._to_model(data, model_class)


class AssetRepository(BaseRepository):
    """Data access for campaign assets."""

    def __init__(self):
        super().__init__("campaign_assets")

    async def create(self, asset: CampaignAsset) -> CampaignAsset:
        """Create a new asset."""
        data = asset.to_dict()
        data = {k: v for k, v in data.items() if v is not None}

        result = await self.client.table(self.table_name).insert(data).execute()
        if result.data:
            return self._to_model(result.data[0], CampaignAsset)
        raise Exception("Failed to create asset")

    async def get_by_campaign(self, campaign_id: UUID) -> List[CampaignAsset]:
        """Get all assets for a campaign."""
        result = (
            await self.client.table(self.table_name)
            .select("*")
            .eq("campaign_id", str(campaign_id))
            .order("created_at")
            .execute()
        )

        return [self._to_model(item, CampaignAsset) for item in result.data]

    async def delete(self, asset_id: UUID) -> bool:
        """Delete an asset."""
        result = await self.client.table(self.table_name).delete().eq("id", str(asset_id)).execute()

        return len(result.data) > 0

    def _to_model(self, data: dict, model_class: type) -> CampaignAsset:
        """Convert database dict to CampaignAsset model."""
        if model_class == CampaignAsset:
            return CampaignAsset(
                id=UUID(data["id"]),
                campaign_id=UUID(data["campaign_id"]),
                asset_type=AssetType(data["asset_type"]),
                content=data.get("content", {}),
                storage_path=data.get("storage_path"),
                source=AssetSource(data["source"]),
                created_at=(
                    datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
                ),
                created_by=UUID(data["created_by"]),
            )
        return super()._to_model(data, model_class)


class HistoryRepository(BaseRepository):
    """Data access for campaign history."""

    def __init__(self):
        super().__init__("campaign_history")

    async def create(self, entry) -> any:
        """Create a history entry."""
        data = entry.to_dict()
        data = {k: v for k, v in data.items() if v is not None}

        result = await self.client.table(self.table_name).insert(data).execute()
        if result.data:
            return self._to_model(result.data[0])
        raise Exception("Failed to create history entry")

    async def get_by_campaign(
        self,
        campaign_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[any], int]:
        """Get paginated history for a campaign."""
        query = (
            self.client.table(self.table_name)
            .select("*", count="exact")
            .eq("campaign_id", str(campaign_id))
            .order("timestamp", desc=True)
        )

        offset = (page - 1) * page_size
        query = query.range(offset, offset + page_size - 1)

        result = await query.execute()

        entries = [self._to_model(item) for item in result.data]
        total = result.count or 0

        return entries, total

    async def count_by_campaign(self, campaign_id: UUID) -> int:
        """Get total history count for a campaign."""
        result = (
            await self.client.table(self.table_name)
            .select("id", count="exact")
            .eq("campaign_id", str(campaign_id))
            .execute()
        )

        return result.count or 0

    def _to_model(self, data: dict, model_class: type = None):
        """Convert database dict to History model."""
        # Import here to avoid circular import
        from src.models.history import CampaignHistoryEntry, EventType

        if "event_type" in data:
            data["event_type"] = EventType(data["event_type"])
        if "from_state" in data and data["from_state"]:
            data["from_state"] = CampaignState(data["from_state"])
        if "to_state" in data and data["to_state"]:
            data["to_state"] = CampaignState(data["to_state"])
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        return CampaignHistoryEntry.from_dict(data)
