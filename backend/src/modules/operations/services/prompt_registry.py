"""Prompt version registry — immutable prompt template tracking."""

import hashlib
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from ..errors import RegistryError


class PromptVersionRegistry:
    """In-memory registry for immutable prompt template versions.

    Each prompt version is identified by a UUID and stores a SHA256 hash
    of the template content for integrity verification.
    """

    def __init__(self) -> None:
        self._versions: dict[UUID, dict[str, Any]] = {}

    def register(self, name: str, template: str) -> UUID:
        """Register a new immutable prompt version.

        Args:
            name: Human-readable prompt name.
            template: Prompt template content.

        Returns:
            UUID version_id for the registered prompt.

        Raises:
            RegistryError: If registration fails.
        """
        version_id = uuid4()
        template_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()
        self._versions[version_id] = {
            "version_id": version_id,
            "name": name,
            "template": template,
            "template_hash": template_hash,
            "created_at": datetime.now(UTC),
            "is_active": True,
        }
        return version_id

    def register_or_get(self, name: str, template: str) -> UUID:
        """Return the existing version_id for this name+content, else register it.

        Makes prompt_version_id stable across calls so telemetry from repeated
        runs of the same prompt correlates.
        """
        template_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()
        for v in self._versions.values():
            if v["name"] == name and v["template_hash"] == template_hash:
                return cast(UUID, v["version_id"])
        return self.register(name, template)

    def get(self, version_id: UUID) -> dict[str, Any] | None:
        """Look up a prompt version by its immutable ID.

        Args:
            version_id: Immutable prompt version UUID.

        Returns:
            Prompt version dict or None if not found.
        """
        return self._versions.get(version_id)

    def get_active(self, name: str) -> dict[str, Any] | None:
        """Get the active version of a prompt by name.

        Args:
            name: Prompt name.

        Returns:
            Active prompt version dict or None.
        """
        for v in self._versions.values():
            if v["name"] == name and v["is_active"]:
                return v
        return None

    def deactivate(self, version_id: UUID) -> None:
        """Deactivate a prompt version.

        Args:
            version_id: Prompt version UUID.

        Raises:
            RegistryError: If version_id not found.
        """
        if version_id not in self._versions:
            raise RegistryError(f"Prompt version {version_id} not found")
        self._versions[version_id]["is_active"] = False

    def activate(self, version_id: UUID) -> None:
        """Activate a prompt version.

        Args:
            version_id: Prompt version UUID.

        Raises:
            RegistryError: If version_id not found.
        """
        if version_id not in self._versions:
            raise RegistryError(f"Prompt version {version_id} not found")
        self._versions[version_id]["is_active"] = True

    def list_versions(self, name: str) -> list[dict[str, Any]]:
        """List all versions of a prompt by name.

        Args:
            name: Prompt name.

        Returns:
            List of version dicts sorted by creation date (newest first).
        """
        matches = [v for v in self._versions.values() if v["name"] == name]
        matches.sort(key=lambda v: v["created_at"], reverse=True)
        return matches

    def count(self) -> int:
        """Return the total number of registered prompt versions."""
        return len(self._versions)
