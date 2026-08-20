"""Export service for offline evaluation of workflow executions."""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from ..errors import ExportError
from ..repositories.execution_history_repository import ExecutionHistoryRepository

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting execution history for offline evaluation.

    Queries execution history by date range, converts to JSONL format,
    and uploads to Supabase Storage for download.
    """

    def __init__(
        self,
        repository: ExecutionHistoryRepository,
        storage_bucket: str = "execution-exports",
    ) -> None:
        self._repository = repository
        self._storage_bucket = storage_bucket
        self._supabase_storage: Any = None

    def _init_storage(self) -> None:
        """Lazy-init Supabase Storage client."""
        if self._supabase_storage is None:
            try:
                from src.config.supabase import get_supabase_client

                self._supabase_storage = get_supabase_client().storage
            except Exception as e:
                logger.warning("Supabase Storage unavailable, exports stay local: %s", e)
                self._supabase_storage = None

    async def export(
        self,
        time_range_start: datetime,
        time_range_end: datetime,
        format: str = "jsonl",
    ) -> str:
        """Export execution history for offline evaluation.

        Args:
            time_range_start: Start of export range.
            time_range_end: End of export range.
            format: Export format ('jsonl').

        Returns:
            Download URL or path to the exported dataset.

        Raises:
            ExportError: If export fails.
        """
        try:
            records = await self._repository.export_range(time_range_start, time_range_end)
        except Exception as e:
            raise ExportError(f"Failed to query execution history: {e}") from e

        if not records:
            raise ExportError("No execution records found in the specified date range")

        if format == "jsonl":
            export_data = self._to_jsonl(records)
        else:
            raise ExportError(f"Unsupported export format: {format}")

        return await self._upload(export_data, format, time_range_start, time_range_end)

    @staticmethod
    def _to_jsonl(records: list[dict[str, Any]]) -> str:
        """Convert records to JSONL format.

        Args:
            records: List of execution history record dicts.

        Returns:
            JSONL string with one JSON object per line.
        """
        lines = [json.dumps(r, default=str) for r in records]
        return "\n".join(lines)

    async def _upload(
        self,
        data: str,
        format: str,
        time_range_start: datetime,
        time_range_end: datetime,
    ) -> str:
        """Upload export data to Supabase Storage.

        Falls back to local path if Supabase Storage is not configured.

        Args:
            data: Export data content.
            format: File format extension.
            time_range_start: Start of export range.
            time_range_end: End of export range.

        Returns:
            Download URL or path.
        """
        self._init_storage()
        export_id = uuid4()
        filename = (
            f"executions_{time_range_start.date()}_{time_range_end.date()}_{export_id}.{format}"
        )

        if self._supabase_storage is not None:
            try:
                bucket = self._supabase_storage.from_(self._storage_bucket)
                bucket.upload(filename, data.encode("utf-8"))
                public_url = bucket.get_public_url(filename)
                return str(public_url)
            except Exception:
                return f"file://exports/{filename}"
        else:
            return f"file://exports/{filename}"
