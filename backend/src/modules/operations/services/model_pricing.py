"""Seed data for the model version registry.

Per-token USD rates for the models this project actually calls. Kept separate
from service logic so price updates are a single-file change.
"""

from typing import Any

from .model_registry import ModelVersionRegistry

# (model_name, model_version, provider, cost_per_input_token, cost_per_output_token)
SUPPORTED_MODELS: list[dict[str, Any]] = [
    {
        "model_name": "groq",
        "model_version": "llama-3.3-70b-versatile",
        "provider": "groq",
        "cost_per_input_token": 5.9e-7,
        "cost_per_output_token": 7.9e-7,
        "supported_capabilities": ["chat", "json"],
    },
    {
        "model_name": "groq",
        "model_version": "llama-3.1-8b-instant",
        "provider": "groq",
        "cost_per_input_token": 5.0e-8,
        "cost_per_output_token": 8.0e-8,
        "supported_capabilities": ["chat", "json"],
    },
    {
        "model_name": "gemini",
        "model_version": "models/gemini-3.5-flash",
        "provider": "google",
        "cost_per_input_token": 3.0e-7,
        "cost_per_output_token": 2.5e-6,
        "supported_capabilities": ["chat", "json", "vision"],
    },
]


def seed_model_registry(registry: ModelVersionRegistry) -> None:
    """Register every supported model version, skipping any already present."""
    for entry in SUPPORTED_MODELS:
        if registry.get(entry["model_name"], entry["model_version"]):
            continue
        registry.register(**entry)
