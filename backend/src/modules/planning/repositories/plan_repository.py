"""Data access for campaign plans, their versions, and the refinement thread.

Plan versions are append-only: every revision is retained so a marketer can
ask to see an earlier draft.
"""

import logging
from typing import Any
from uuid import UUID

from src.modules.planning.models.campaign_plan import (
    CampaignPlan,
    PlanMessage,
    PlanStatus,
    PlanVersion,
)
from src.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

PLANS_TABLE = "campaign_plans"
VERSIONS_TABLE = "campaign_plan_versions"
MESSAGES_TABLE = "campaign_plan_messages"


class PlanNotFoundError(Exception):
    """Raised when no plan exists for the requested campaign."""


class PlanRepository(BaseRepository):
    """Reads and writes campaign plans and their revision history."""

    def __init__(self) -> None:
        super().__init__(PLANS_TABLE)

    # ── Plan rows ────────────────────────────────────────────────────────

    async def create_plan(
        self,
        campaign_id: UUID,
        created_by: UUID,
        language: str = "en",
    ) -> dict[str, Any]:
        """Create the plan row for a campaign (one per campaign)."""
        row = {
            "campaign_id": str(campaign_id),
            "status": PlanStatus.DRAFTING.value,
            "current_version": 0,
            "language": language,
            "created_by": str(created_by),
        }
        result = self.client.table(PLANS_TABLE).insert(row).execute()
        if not result.data:
            raise RuntimeError(f"Failed to create plan for campaign {campaign_id}")
        return result.data[0]

    async def get_plan_row(self, campaign_id: UUID) -> dict[str, Any] | None:
        """Return the raw plan row for a campaign, or None."""
        result = (
            self.client.table(PLANS_TABLE).select("*").eq("campaign_id", str(campaign_id)).execute()
        )
        return result.data[0] if result.data else None

    async def get_or_create_plan_row(
        self,
        campaign_id: UUID,
        created_by: UUID,
        language: str = "en",
    ) -> dict[str, Any]:
        """Return the existing plan row, creating it if absent."""
        existing = await self.get_plan_row(campaign_id)
        if existing:
            return existing
        return await self.create_plan(campaign_id, created_by, language)

    async def update_plan_row(self, plan_id: UUID, **fields: Any) -> dict[str, Any]:
        """Patch columns on the plan row."""
        result = self.client.table(PLANS_TABLE).update(fields).eq("id", str(plan_id)).execute()
        if not result.data:
            raise PlanNotFoundError(f"Plan {plan_id} not found")
        return result.data[0]

    # ── Versions ─────────────────────────────────────────────────────────

    async def add_version(
        self,
        plan_id: UUID,
        plan: CampaignPlan,
        *,
        change_summary: str = "",
        sections_changed: tuple[str, ...] = (),
        parent_version: int | None = None,
    ) -> PlanVersion:
        """Append a new version and point the plan row at it atomically using an RPC."""
        args = {
            "p_plan_id": str(plan_id),
            "p_version": plan.version,
            "p_document": plan.to_document(),
            "p_parent_version": parent_version,
            "p_change_summary": change_summary,
            "p_sections_changed": list(sections_changed),
            "p_status": plan.status.value,
            "p_language": plan.language,
        }

        result = self.client.rpc("add_plan_version", args).execute()
        if not result.data:
            raise RuntimeError(f"Failed to store version {plan.version} for plan {plan_id}")

        return self._to_version(result.data)

    async def get_version(self, plan_id: UUID, version: int) -> PlanVersion | None:
        """Return one specific version of a plan."""
        result = (
            self.client.table(VERSIONS_TABLE)
            .select("*")
            .eq("plan_id", str(plan_id))
            .eq("version", version)
            .execute()
        )
        return self._to_version(result.data[0]) if result.data else None

    async def get_latest_version(self, plan_id: UUID) -> PlanVersion | None:
        """Return the most recent version of a plan."""
        result = (
            self.client.table(VERSIONS_TABLE)
            .select("*")
            .eq("plan_id", str(plan_id))
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        return self._to_version(result.data[0]) if result.data else None

    async def list_versions(self, plan_id: UUID) -> list[PlanVersion]:
        """Return every version of a plan, newest first."""
        result = (
            self.client.table(VERSIONS_TABLE)
            .select("*")
            .eq("plan_id", str(plan_id))
            .order("version", desc=True)
            .execute()
        )
        return [self._to_version(r) for r in (result.data or [])]

    # ── Messages ─────────────────────────────────────────────────────────

    async def add_message(self, message: PlanMessage) -> PlanMessage:
        """Append one turn to the refinement conversation."""
        row = {
            "plan_id": str(message.plan_id),
            "role": message.role,
            "content": message.content,
            "language": message.language,
            "sections_targeted": list(message.sections_targeted),
            "resulting_version": message.resulting_version,
        }
        result = self.client.table(MESSAGES_TABLE).insert(row).execute()
        if not result.data:
            raise RuntimeError(f"Failed to store message for plan {message.plan_id}")
        return self._to_message(result.data[0])

    async def list_messages(self, plan_id: UUID) -> list[PlanMessage]:
        """Return the conversation for a plan in chronological order."""
        result = (
            self.client.table(MESSAGES_TABLE)
            .select("*")
            .eq("plan_id", str(plan_id))
            .order("created_at")
            .execute()
        )
        return [self._to_message(r) for r in (result.data or [])]

    # ── Row mapping ──────────────────────────────────────────────────────

    @staticmethod
    def _to_version(row: dict[str, Any]) -> PlanVersion:
        return PlanVersion(
            id=row["id"],
            plan_id=row["plan_id"],
            version=row["version"],
            document=row["document"],
            parent_version=row.get("parent_version"),
            change_summary=row.get("change_summary") or "",
            sections_changed=tuple(row.get("sections_changed") or ()),
            created_at=row["created_at"],
        )

    @staticmethod
    def _to_message(row: dict[str, Any]) -> PlanMessage:
        return PlanMessage(
            id=row["id"],
            plan_id=row["plan_id"],
            role=row["role"],
            content=row["content"],
            language=row.get("language") or "en",
            sections_targeted=tuple(row.get("sections_targeted") or ()),
            resulting_version=row.get("resulting_version"),
            created_at=row["created_at"],
        )
