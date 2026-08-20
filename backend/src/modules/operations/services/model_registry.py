"""Model version registry — model metadata, pricing, and deprecation tracking."""

from datetime import datetime
from typing import Any, cast


class ModelVersionRegistry:
    """In-memory registry for AI model metadata.

    Stores model name, version, provider, cost per token, deprecation
    status, and supported capabilities for cost estimation and guardrails.
    """

    def __init__(self) -> None:
        self._models: dict[str, list[dict[str, Any]]] = {}

    def register(
        self,
        model_name: str,
        model_version: str,
        provider: str,
        cost_per_input_token: float,
        cost_per_output_token: float,
        supported_capabilities: list[str] | None = None,
        is_deprecated: bool = False,
        deprecation_date: datetime | None = None,
    ) -> None:
        """Register or update a model version.

        Args:
            model_name: Model identifier (e.g., 'gpt-4').
            model_version: Version string (e.g., 'gpt-4-0613').
            provider: Provider name ('openai', 'google', 'anthropic').
            cost_per_input_token: USD per input token.
            cost_per_output_token: USD per output token.
            supported_capabilities: Optional list of capabilities.
            is_deprecated: Whether this model version is deprecated.
            deprecation_date: Expected deprecation date.
        """
        entry = {
            "model_name": model_name,
            "model_version": model_version,
            "provider": provider,
            "cost_per_input_token": cost_per_input_token,
            "cost_per_output_token": cost_per_output_token,
            "supported_capabilities": supported_capabilities or [],
            "is_deprecated": is_deprecated,
            "deprecation_date": deprecation_date,
        }
        if model_name not in self._models:
            self._models[model_name] = []
        self._models[model_name].append(entry)

    def get(self, model_name: str, model_version: str | None = None) -> dict[str, Any] | None:
        """Get model metadata.

        Args:
            model_name: Model identifier.
            model_version: Optional version filter. Returns the latest
                version if omitted.

        Returns:
            Model metadata dict or None if not found.
        """
        versions = self._models.get(model_name)
        if not versions:
            return None
        if model_version:
            for v in versions:
                if v["model_version"] == model_version:
                    return v
            return None
        return versions[-1]

    def estimate_cost(
        self, model_name: str, model_version: str, input_tokens: int, output_tokens: int
    ) -> float | None:
        """Estimate the cost in USD for an AI request.

        Args:
            model_name: Model identifier.
            model_version: Version string.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD, or None if model not found.
        """
        model = self.get(model_name, model_version)
        if not model:
            return None
        cost = (
            input_tokens * model["cost_per_input_token"]
            + output_tokens * model["cost_per_output_token"]
        )
        return cast(float, round(cost, 6))

    def is_deprecated(self, model_name: str, model_version: str) -> bool:
        """Check if a model version is deprecated.

        Args:
            model_name: Model identifier.
            model_version: Version string.

        Returns:
            True if deprecated or not found.
        """
        model = self.get(model_name, model_version)
        if not model:
            return True
        return cast(bool, model["is_deprecated"])

    def list_models(self) -> list[str]:
        """List all registered model names."""
        return list(self._models.keys())

    def list_versions(self, model_name: str) -> list[dict[str, Any]]:
        """List all versions of a model.

        Args:
            model_name: Model identifier.

        Returns:
            List of version dicts.
        """
        return self._models.get(model_name, [])

    def mark_deprecated(self, model_name: str, model_version: str) -> None:
        """Mark a model version as deprecated.

        Args:
            model_name: Model identifier.
            model_version: Version string.
        """
        model = self.get(model_name, model_version)
        if model:
            model["is_deprecated"] = True
