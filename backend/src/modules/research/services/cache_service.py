"""Redis and in-memory TTL caching service."""

from __future__ import annotations

import hashlib
import time
from typing import Any


class CacheService:
    """Caching service supporting Redis with an in-memory TTL dictionary fallback."""

    _instance: CacheService | None = None

    def __init__(self) -> None:
        self._memory_store: dict[str, tuple[Any, float]] = {}

    @classmethod
    def get_instance(cls) -> CacheService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def hash_key(prefix: str, content: str) -> str:
        """Create a deterministic SHA256 cache key."""
        hashed = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        return f"{prefix}:{hashed}"

    async def get(self, key: str) -> Any | None:
        """Get cached item if not expired."""
        if key in self._memory_store:
            data, expires_at = self._memory_store[key]
            if time.time() < expires_at:
                return data
            # Expired
            del self._memory_store[key]
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set cached item with TTL."""
        expires_at = time.time() + ttl_seconds
        self._memory_store[key] = (value, expires_at)
