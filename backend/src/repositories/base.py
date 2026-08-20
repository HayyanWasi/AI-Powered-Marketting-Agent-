"""Base repository with transaction support."""

from typing import Any, Generic, TypeVar

from supabase import Client as SupabaseClient

from src.config.supabase import get_supabase_client

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository with Supabase client and transaction support."""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self._client: SupabaseClient | None = None

    @property
    def client(self) -> SupabaseClient:
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    async def _execute_in_transaction(self, operations: list[callable]) -> list[Any]:
        """Execute multiple operations in a transaction.

        Note: Supabase doesn't support explicit transactions via the Python SDK.
        This is a placeholder for future implementation with direct asyncpg.
        """
        results = []
        for op in operations:
            result = await op()
            results.append(result)
        return results

    def _to_model(self, data: dict[str, Any], model_class: type[T]) -> T:
        """Convert database dict to model instance."""
        if hasattr(model_class, "from_dict"):
            return model_class.from_dict(data)
        return model_class(**data)

    def _to_dict(self, model: Any) -> dict[str, Any]:
        """Convert model to dictionary for storage."""
        if hasattr(model, "to_dict"):
            return model.to_dict()
        # Handle Pydantic models
        if hasattr(model, "model_dump"):
            return model.model_dump()
        # Handle dataclasses
        if hasattr(model, "__dataclass_fields__"):
            from dataclasses import asdict

            return asdict(model)
        return model.__dict__
