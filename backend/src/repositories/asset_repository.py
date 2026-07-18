"""Asset repository - data access for campaign assets."""

from typing import List
from uuid import UUID
from src.config.supabase import get_supabase_client
from src.models.campaign import CampaignAsset, AssetType, AssetSource


class AssetRepository:
    """Data access for campaign assets."""

    def __init__(self):
        self.table_name = "campaign_assets"
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    async def create(self, asset: CampaignAsset) -> CampaignAsset:
        """Create a new campaign asset."""
        data = asset.to_dict()
        data = {k: v for k, v in data.items() if v is not None}

        result = await self.client.table(self.table_name).insert(data).execute()
        if result.data:
            return self._to_model(result.data[0])
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

        return [self._to_model(row) for row in (result.data or [])]

    async def delete(self, asset_id: UUID) -> bool:
        """Delete an asset by ID."""
        result = await self.client.table(self.table_name).delete().eq("id", str(asset_id)).execute()

        return len(result.data) > 0

    def _to_model(self, data: dict) -> CampaignAsset:
        """Convert database dict to CampaignAsset model."""
        return CampaignAsset(
            id=UUID(data["id"]),
            campaign_id=UUID(data["campaign_id"]),
            asset_type=AssetType(data["asset_type"]),
            content=data.get("content", {}),
            storage_path=data.get("storage_path"),
            source=AssetSource(data["source"]),
            created_at=(
                data["created_at"] if isinstance(data["created_at"], str) else data["created_at"]
            ),
            created_by=UUID(data["created_by"]),
        )
