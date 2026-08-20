"""PostgreSQL repository for audit logs, research sessions, and persistent JSONB evidence graph fallback."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.config.supabase import get_supabase_client

logger = logging.getLogger(__name__)


class PostgresService:
    """Postgres repository service via Supabase SDK."""

    def __init__(self) -> None:
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    async def create_session(
        self,
        campaign_id: UUID | None,
        tier: str,
    ) -> dict[str, Any]:
        """Create a new research session row."""
        try:
            data = {
                "campaign_id": str(campaign_id) if campaign_id else None,
                "tier": tier,
                "status": "running",
            }
            res = self.client.table("research_sessions").insert(data).execute()
            return res.data[0] if res.data else data
        except Exception as e:
            logger.warning("Failed to log research session to Postgres: %s", e)
            return {"id": "00000000-0000-0000-0000-000000000000", "tier": tier, "status": "running"}

    async def complete_session(
        self,
        session_id: UUID | str,
        total_searches: int,
        total_llm_calls: int,
        total_latency_ms: int,
        estimated_cost_usd: float,
    ) -> None:
        """Update session status and metrics."""
        try:
            self.client.table("research_sessions").update(
                {
                    "status": "completed",
                    "total_searches": total_searches,
                    "total_llm_calls": total_llm_calls,
                    "total_latency_ms": total_latency_ms,
                    "estimated_cost_usd": estimated_cost_usd,
                }
            ).eq("id", str(session_id)).execute()
        except Exception as e:
            logger.warning("Failed to update research session in Postgres: %s", e)

    async def log_search(
        self,
        session_id: UUID | str,
        dimension: str,
        query: str,
        provider: str,
        results_count: int,
        latency_ms: int,
    ) -> None:
        """Log search query audit record."""
        try:
            data = {
                "session_id": str(session_id),
                "dimension": dimension,
                "query": query,
                "provider": provider,
                "results_count": results_count,
                "latency_ms": latency_ms,
            }
            self.client.table("search_audit_log").insert(data).execute()
        except Exception as e:
            logger.warning("Failed to log search audit record: %s", e)

    async def save_evidence_graph_fallback(
        self,
        session_id: UUID | str,
        graph_document: dict[str, Any],
    ) -> None:
        """Persist Evidence Graph as JSONB (survives restarts if Neo4j is offline)."""
        try:
            data = {
                "session_id": str(session_id),
                "document": graph_document,
            }
            self.client.table("research_evidence_graphs").upsert(
                data, on_conflict="session_id"
            ).execute()
            logger.info("Persisted Evidence Graph JSONB fallback to Postgres for session %s", session_id)
        except Exception as e:
            logger.warning("Failed to save evidence graph fallback to Postgres: %s", e)

    async def get_evidence_graph_fallback(
        self, session_id: UUID | str
    ) -> dict[str, Any] | None:
        """Retrieve persistent Evidence Graph JSONB fallback."""
        try:
            res = (
                self.client.table("research_evidence_graphs")
                .select("document")
                .eq("session_id", str(session_id))
                .execute()
            )
            if res.data and len(res.data) > 0:
                return res.data[0]["document"]
        except Exception as e:
            logger.warning("Failed to fetch evidence graph fallback from Postgres: %s", e)
        return None
