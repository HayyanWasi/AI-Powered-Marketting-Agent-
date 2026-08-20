"""Asset service - manage campaign assets."""

from uuid import UUID

from src.models.campaign import AssetSource, AssetType, CampaignAsset
from src.repositories.asset_repository import AssetRepository
from src.services.history_service import HistoryService


class AssetService:
    """Service for managing campaign assets."""

    def __init__(self):
        self.repository = AssetRepository()
        self.history_service = HistoryService()

    async def create_asset(
        self,
        campaign_id: UUID,
        asset_type: AssetType,
        content: dict,
        source: AssetSource,
        actor_id: UUID,
        storage_path: str | None = None,
    ) -> CampaignAsset:
        """Create a new campaign asset."""
        asset = CampaignAsset(
            campaign_id=campaign_id,
            asset_type=asset_type,
            content=content,
            source=source,
            created_by=actor_id,
            storage_path=storage_path,
        )

        created = await self.repository.create_asset(asset)

        # Log asset association
        await self.history_service.log_asset_association(
            campaign_id=campaign_id,
            actor_id=actor_id,
            asset_type=asset_type.value,
            asset_id=created.id,
        )

        return created

    async def list_assets(self, campaign_id: UUID) -> list[CampaignAsset]:
        """List all assets for a campaign."""
        return await self.repository.get_by_campaign(campaign_id)

    async def delete_asset(self, asset_id: UUID, actor_id: UUID) -> bool:
        """Delete an asset."""
        return await self.repository.delete_asset(asset_id)
