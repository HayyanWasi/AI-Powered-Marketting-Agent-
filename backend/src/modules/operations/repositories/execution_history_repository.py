"""Execution history repository — Supabase-backed persistence."""

from datetime import datetime
from typing import Any
from uuid import UUID

from supabase import Client as SupabaseClient

from ..errors import HistoryQueryError
from ..models.execution_history import ExecutionHistoryRecord


class ExecutionHistoryRepository:
    """Repository for persisting and querying execution history records.

    Uses Supabase PostgreSQL for storage with indexes on workflow_id,
    status, start_time, and tags for search performance.
    """

    TABLE_NAME = "execution_history"

    def __init__(self, supabase: SupabaseClient | None = None) -> None:
        self._supabase = supabase

    async def insert(self, record: ExecutionHistoryRecord) -> None:
        """Insert a new execution history record.

        Args:
            record: The execution history record to persist.

        Raises:
            HistoryQueryError: If the insert fails.
        """
        if not self._supabase:
            raise HistoryQueryError("Supabase client not configured")

        try:
            data = record.to_dict()
            data["id"] = str(record.id)
            if record.trace_id:
                data["trace_id"] = str(record.trace_id)
            self._supabase.table(self.TABLE_NAME).insert(data).execute()
        except Exception as e:
            raise HistoryQueryError(f"Failed to insert execution history: {e}") from e

    async def query(
        self,
        workflow_id: str | None = None,
        status: str | None = None,
        time_range_start: datetime | None = None,
        time_range_end: datetime | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query execution history records with filters.

        Args:
            workflow_id: Filter by workflow ID (exact match).
            status: Filter by status (exact match).
            time_range_start: Start of time range filter.
            time_range_end: End of time range filter.
            tags: Filter by tags (AND logic).
            limit: Maximum records to return (default 100).
            offset: Pagination offset.

        Returns:
            List of execution history record dicts.

        Raises:
            HistoryQueryError: If the query fails.
        """
        if not self._supabase:
            raise HistoryQueryError("Supabase client not configured")

        try:
            query = self._supabase.table(self.TABLE_NAME).select("*")

            if workflow_id:
                query = query.eq("workflow_id", workflow_id)
            if status:
                query = query.eq("status", status)
            if time_range_start:
                query = query.gte("start_time", time_range_start.isoformat())
            if time_range_end:
                query = query.lte("start_time", time_range_end.isoformat())
            if tags:
                query = query.contains("tags", tags)

            query = query.order("start_time", desc=True).range(offset, offset + limit - 1)

            result = query.execute()
            return result.data if result.data else []  # type: ignore[return-value]
        except Exception as e:
            raise HistoryQueryError(f"Failed to query execution history: {e}") from e

    async def count(
        self,
        workflow_id: str | None = None,
        status: str | None = None,
        time_range_start: datetime | None = None,
        time_range_end: datetime | None = None,
    ) -> int:
        """Count execution history records matching filters.

        Args:
            workflow_id: Filter by workflow ID.
            status: Filter by status.
            time_range_start: Start of time range.
            time_range_end: End of time range.

        Returns:
            Record count.

        Raises:
            HistoryQueryError: If the count query fails.
        """
        if not self._supabase:
            raise HistoryQueryError("Supabase client not configured")

        try:
            query = self._supabase.table(self.TABLE_NAME).select("id", count="exact")  # type: ignore[arg-type]
            if workflow_id:
                query = query.eq("workflow_id", workflow_id)
            if status:
                query = query.eq("status", status)
            if time_range_start:
                query = query.gte("start_time", time_range_start.isoformat())
            if time_range_end:
                query = query.lte("start_time", time_range_end.isoformat())
            result = query.execute()
            return result.count or 0
        except Exception as e:
            raise HistoryQueryError(f"Failed to count execution history: {e}") from e

    async def get_by_id(self, record_id: UUID) -> dict[str, Any] | None:
        """Get a single execution history record by ID.

        Args:
            record_id: Record UUID.

        Returns:
            Record dict or None if not found.
        """
        if not self._supabase:
            raise HistoryQueryError("Supabase client not configured")

        try:
            result = (
                self._supabase.table(self.TABLE_NAME).select("*").eq("id", str(record_id)).execute()
            )
            return result.data[0] if result.data else None  # type: ignore[return-value]
        except Exception as e:
            raise HistoryQueryError(f"Failed to get execution history {record_id}: {e}") from e

    async def export_range(
        self,
        time_range_start: datetime,
        time_range_end: datetime,
    ) -> list[dict[str, Any]]:
        """Export all records in a date range for offline evaluation.

        Args:
            time_range_start: Start of export range.
            time_range_end: End of export range.

        Returns:
            List of all matching records (no pagination).
        """
        if not self._supabase:
            raise HistoryQueryError("Supabase client not configured")

        try:
            result = (
                self._supabase.table(self.TABLE_NAME)
                .select("*")
                .gte("start_time", time_range_start.isoformat())
                .lte("start_time", time_range_end.isoformat())
                .order("start_time", desc=True)
                .execute()
            )
            return result.data if result.data else []  # type: ignore[return-value]
        except Exception as e:
            raise HistoryQueryError(f"Failed to export execution history: {e}") from e
