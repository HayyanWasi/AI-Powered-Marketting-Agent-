"""History repository - data access for campaign history."""

from uuid import UUID

from src.models.history import CampaignHistoryEntry
from src.repositories.base import BaseRepository


class HistoryRepository(BaseRepository):
    """Data access for campaign history entries."""

    def __init__(self):
        super().__init__("campaign_history")

    async def create(self, entry: CampaignHistoryEntry) -> CampaignHistoryEntry:
        """Create a new history entry (append-only)."""
        data = entry.to_dict()
        data = {k: v for k, v in data.items() if v is not None}

        result = self.client.table(self.table_name).insert(data).execute()
        if result.data:
            return self._to_model(result.data[0], CampaignHistoryEntry)
        raise Exception("Failed to create history entry")

    async def get_by_campaign(
        self,
        campaign_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[CampaignHistoryEntry], int]:
        """Get paginated history for a campaign."""
        # Get total count
        count_result = (
            self.client.table(self.table_name)
            .select("id", count="exact")
            .eq("campaign_id", str(campaign_id))
            .execute()
        )
        total = count_result.count or 0

        # Get paginated entries
        result = (
            self.client.table(self.table_name)
            .select("*")
            .eq("campaign_id", str(campaign_id))
            .order("timestamp", desc=True)
            .range((page - 1) * page_size, page * page_size - 1)
            .execute()
        )

        entries = [self._to_model(row, CampaignHistoryEntry) for row in (result.data or [])]
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
