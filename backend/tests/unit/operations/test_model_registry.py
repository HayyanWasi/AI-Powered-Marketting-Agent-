"""Unit tests for ModelVersionRegistry."""


from src.modules.operations.services.model_registry import (
    ModelVersionRegistry,
)


class TestModelVersionRegistry:
    def test_register_and_get(self):
        registry = ModelVersionRegistry()
        registry.register(
            model_name="gpt-4",
            model_version="gpt-4-0613",
            provider="openai",
            cost_per_input_token=0.00003,
            cost_per_output_token=0.00006,
        )
        model = registry.get("gpt-4", "gpt-4-0613")
        assert model is not None
        assert model["provider"] == "openai"

    def test_get_returns_latest_without_version(self):
        registry = ModelVersionRegistry()
        registry.register("gpt-4", "v1", "openai", 0.01, 0.02)
        registry.register("gpt-4", "v2", "openai", 0.02, 0.03)
        model = registry.get("gpt-4")
        assert model["model_version"] == "v2"

    def test_get_returns_none_for_missing_model(self):
        registry = ModelVersionRegistry()
        assert registry.get("nonexistent") is None

    def test_estimate_cost(self):
        registry = ModelVersionRegistry()
        registry.register("gpt-4", "v1", "openai", 0.00003, 0.00006)
        cost = registry.estimate_cost("gpt-4", "v1", 1000, 500)
        expected = 1000 * 0.00003 + 500 * 0.00006
        assert cost == round(expected, 6)

    def test_estimate_cost_returns_none_for_unknown_model(self):
        registry = ModelVersionRegistry()
        assert registry.estimate_cost("unknown", "v1", 10, 10) is None

    def test_is_deprecated(self):
        registry = ModelVersionRegistry()
        registry.register("gpt-4", "v1", "openai", 0.01, 0.02, is_deprecated=False)
        registry.register("gpt-4", "old", "openai", 0.01, 0.02, is_deprecated=True)
        assert not registry.is_deprecated("gpt-4", "v1")
        assert registry.is_deprecated("gpt-4", "old")

    def test_is_deprecated_returns_true_for_unknown(self):
        registry = ModelVersionRegistry()
        assert registry.is_deprecated("unknown", "v1")

    def test_mark_deprecated(self):
        registry = ModelVersionRegistry()
        registry.register("gpt-4", "v1", "openai", 0.01, 0.02)
        registry.mark_deprecated("gpt-4", "v1")
        assert registry.is_deprecated("gpt-4", "v1")

    def test_list_models(self):
        registry = ModelVersionRegistry()
        registry.register("a", "v1", "p1", 0.01, 0.02)
        registry.register("b", "v1", "p2", 0.01, 0.02)
        assert set(registry.list_models()) == {"a", "b"}
