"""Unit tests for PromptVersionRegistry."""

from uuid import UUID

import pytest

from src.modules.operations.errors import RegistryError
from src.modules.operations.services.prompt_registry import (
    PromptVersionRegistry,
)


class TestPromptVersionRegistry:
    def test_register_returns_uuid(self):
        registry = PromptVersionRegistry()
        version_id = registry.register("test-prompt", "Hello {name}")
        assert isinstance(version_id, UUID)

    def test_get_returns_registered_prompt(self):
        registry = PromptVersionRegistry()
        vid = registry.register("test", "template {x}")
        result = registry.get(vid)
        assert result is not None
        assert result["name"] == "test"
        assert result["template"] == "template {x}"

    def test_get_returns_none_for_missing(self):
        registry = PromptVersionRegistry()
        assert registry.get(UUID(int=0)) is None

    def test_get_active_returns_active_version(self):
        registry = PromptVersionRegistry()
        v1 = registry.register("test", "v1")
        registry.register("test", "v2")
        active = registry.get_active("test")
        assert active is not None
        assert active["version_id"] == v1

    def test_deactivate_and_activate(self):
        registry = PromptVersionRegistry()
        vid = registry.register("test", "content")
        registry.deactivate(vid)
        assert registry.get_active("test") is None
        registry.activate(vid)
        assert registry.get_active("test") is not None

    def test_deactivate_raises_for_missing(self):
        registry = PromptVersionRegistry()
        with pytest.raises(RegistryError):
            registry.deactivate(UUID(int=0))

    def test_list_versions_returns_all(self):
        registry = PromptVersionRegistry()
        registry.register("test", "v1")
        registry.register("test", "v2")
        versions = registry.list_versions("test")
        assert len(versions) == 2

    def test_count(self):
        registry = PromptVersionRegistry()
        assert registry.count() == 0
        registry.register("a", "x")
        registry.register("b", "y")
        assert registry.count() == 2

    def test_template_hash_is_sha256(self):
        registry = PromptVersionRegistry()
        vid = registry.register("test", "content")
        result = registry.get(vid)
        assert len(result["template_hash"]) == 64
        assert all(c in "0123456789abcdef" for c in result["template_hash"])
