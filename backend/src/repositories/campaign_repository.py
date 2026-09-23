"""Campaign repository - data access for campaigns."""

from datetime import datetime
from uuid import UUID

from src.models.campaign import (
    AssetSource,
    AssetType,
    Campaign,
    CampaignAsset,
    CampaignState,
)
from src.repositories.base import BaseRepository


class CampaignRepository(BaseRepository):
    """Data access for campaigns."""

    def __init__(self):
        super().__init__("campaigns")

    async def create(self, campaign: Campaign) -> Campaign:
        """Create a new campaign."""
        data = campaign.to_dict()
        # Remove None values for insert
        data = {k: v for k, v in data.items() if v is not None}

        result = self.client.table(self.table_name).insert(data).execute()
        if result.data:
            return self._to_model(result.data[0], Campaign)
        raise Exception("Failed to create campaign")

    async def get_by_id(
        self, campaign_id: UUID, organization_id: UUID | None = None
    ) -> Campaign | None:
        """Get campaign by ID, optionally filtered by organization."""
        query = self.client.table(self.table_name).select("*").eq("id", str(campaign_id))
        if organization_id:
            query = query.eq("organization_id", str(organization_id))
        result = query.execute()

        if result.data:
            return self._to_model(result.data[0], Campaign)
        return None

    async def get_by_name(self, name: str, organization_id: UUID) -> Campaign | None:
        """Check if campaign name exists in organization."""
        result = (
            self.client.table(self.table_name)
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
    ) -> Campaign | None:
        """Get campaign with associated assets."""
        campaign = await self.get_by_id(campaign_id, organization_id)
        if campaign:
            # Assets are loaded separately via asset repository
            pass
        return campaign

    async def update(self, campaign: Campaign, expected_version: int) -> Campaign:
        """Update campaign with optimistic locking.

        None values ARE sent to the database so nullable columns
        (previous_state, archived_at, published_at) can be cleared.
        """
        data = campaign.to_dict()

        result = (
            self.client.table(self.table_name)
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
            self.client.table(self.table_name)
            .delete()
            .eq("id", str(campaign_id))
            .eq("organization_id", str(organization_id))
            .execute()
        )

        return len(result.data) > 0

    import httpx
    from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

    @retry(
        retry=retry_if_exception_type(httpx.RequestError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, max=1),
        reraise=True,
    )
    async def list(
        self,
        organization_id: UUID,
        state: CampaignState | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        owner_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        company_profile_id: UUID | None = None,
    ) -> tuple[list[Campaign], int]:
        """List campaigns with filters and pagination."""
        query = (
            self.client.table(self.table_name)
            .select("*", count="exact")
            .eq("organization_id", str(organization_id))
        )

        if company_profile_id:
            query = query.eq("company_profile_id", str(company_profile_id))
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

        result = query.execute()

        campaigns = [self._to_model(item, Campaign) for item in result.data]
        total = result.count or 0

        return campaigns, total

    async def archive(
        self, campaign_id: UUID, organization_id: UUID, previous_state: CampaignState
    ) -> Campaign | None:
        """Archive a campaign, storing previous state."""
        data = {
            "state": "Archived",
            "previous_state": previous_state.value,
            "archived_at": datetime.utcnow().isoformat(),
            "version": CampaignRepository._get_next_version(),  # Will be incremented by DB
        }

        result = (
            self.client.table(self.table_name)
            .update(data)
            .eq("id", str(campaign_id))
            .eq("organization_id", str(organization_id))
            .execute()
        )

        if result.data:
            return self._to_model(result.data[0], Campaign)
        return None

    async def restore(self, campaign_id: UUID, organization_id: UUID) -> Campaign | None:
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
            self.client.table(self.table_name)
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

        result = self.client.table(self.table_name).insert(data).execute()
        if result.data:
            return self._to_model(result.data[0], CampaignAsset)
        raise Exception("Failed to create asset")

    async def get_by_campaign(self, campaign_id: UUID) -> list[CampaignAsset]:
        """Get all assets for a campaign."""
        result = (
            self.client.table(self.table_name)
            .select("*")
            .eq("campaign_id", str(campaign_id))
            .order("created_at")
            .execute()
        )

        return [self._to_model(item, CampaignAsset) for item in result.data]

    async def delete(self, asset_id: UUID) -> bool:
        """Delete an asset."""
        result = self.client.table(self.table_name).delete().eq("id", str(asset_id)).execute()

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

        result = self.client.table(self.table_name).insert(data).execute()
        if result.data:
            return self._to_model(result.data[0])
        raise Exception("Failed to create history entry")

    async def get_by_campaign(
        self,
        campaign_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[any], int]:
        """Get paginated history for a campaign."""
        query = (
            self.client.table(self.table_name)
            .select("*", count="exact")
            .eq("campaign_id", str(campaign_id))
            .order("timestamp", desc=True)
        )

        offset = (page - 1) * page_size
        query = query.range(offset, offset + page_size - 1)

        result = query.execute()

        entries = [self._to_model(item) for item in result.data]
        total = result.count or 0

        return entries, total

    async def count_by_campaign(self, campaign_id: UUID) -> int:
        """Get total history count for a campaign."""
        result = (
            self.client.table(self.table_name)
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
