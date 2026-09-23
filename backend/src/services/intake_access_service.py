"""Ownership checks for campaign-bound and pre-campaign intake resources."""

from __future__ import annotations

from uuid import UUID

from src.repositories.base import BaseRepository
from src.repositories.campaign_repository import CampaignRepository


class IntakeAccessDenied(Exception):
    """Raised when an intake resource is missing or not owned by the caller."""


class IntakeAccessService:
    """Authorize an intake UUID without reading its protected contents."""

    async def require_campaign(self, campaign_id: UUID, user_id: UUID) -> None:
        campaign = await CampaignRepository().get_by_id(campaign_id, organization_id=user_id)
        if campaign is None:
            raise IntakeAccessDenied

    async def authorize(
        self,
        resource_id: UUID,
        user_id: UUID,
        *,
        claim_if_missing: bool = False,
    ) -> None:
        campaign_repo = CampaignRepository()
        owned_campaign = await campaign_repo.get_by_id(resource_id, organization_id=user_id)
        if owned_campaign is not None:
            return

        # Prevent a foreign campaign UUID from being treated as a new temporary
        # intake session. Only existence metadata is read here.
        campaign_exists = (
            BaseRepository("campaigns")
            .client.table("campaigns")
            .select("id")
            .eq("id", str(resource_id))
            .limit(1)
            .execute()
        )
        if campaign_exists.data:
            raise IntakeAccessDenied

        owner_ids = self._session_owner_ids(resource_id)
        if owner_ids:
            if owner_ids == {str(user_id)}:
                return
            raise IntakeAccessDenied

        if not claim_if_missing:
            raise IntakeAccessDenied

        try:
            repo = BaseRepository("intake_checklists")
            repo.client.table(repo.table_name).insert(
                {
                    "campaign_id": str(resource_id),
                    "owner_id": str(user_id),
                    "is_complete": False,
                }
            ).execute()
        except Exception:
            # A concurrent claim can win the unique campaign_id race. Re-read
            # only ownership metadata and authorize solely when it is ours.
            if self._session_owner_ids(resource_id) == {str(user_id)}:
                return
            raise IntakeAccessDenied from None

    @staticmethod
    def _session_owner_ids(resource_id: UUID) -> set[str | None]:
        owners: set[str | None] = set()
        for table_name in ("intake_checklists", "intake_messages"):
            result = (
                BaseRepository(table_name)
                .client.table(table_name)
                .select("owner_id")
                .eq("campaign_id", str(resource_id))
                .limit(2)
                .execute()
            )
            owners.update(row.get("owner_id") for row in (result.data or []))
        return owners
