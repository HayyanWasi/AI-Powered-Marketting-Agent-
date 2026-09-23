"""Regression coverage for AudienceProfile tolerating explicit JSON null.

Reproduced live against the configured local model: it intermittently emits
JSON null (rather than [] or omitting the key) for AudienceProfile's tuple
and scalar fields. Pydantic only applies a field default when the key is
absent, so an explicit null previously raised a full ValidationError and
crashed the intake turn with a 502.
"""

from __future__ import annotations

from src.models.audience import AudienceProfile


def test_null_tuple_fields_fall_back_to_empty_tuple() -> None:
    profile = AudienceProfile.model_validate(
        {
            "summary": "Renters seeking discounted rates",
            "occupation_groups": None,
            "industries": None,
            "seniority_levels": None,
            "work_environments": None,
            "schedule_patterns": None,
            "attention_patterns": None,
            "locations": None,
            "timezones": None,
            "evidence": None,
            "source": "explicit",
            "confidence": "low",
        }
    )

    assert profile.occupation_groups == ()
    assert profile.evidence == ()


def test_null_scalar_fields_fall_back_to_declared_default() -> None:
    profile = AudienceProfile.model_validate(
        {
            "summary": None,
            "source": None,
            "confidence": None,
            "inference_version": None,
        }
    )

    assert profile.summary == ""
    assert profile.source == "fallback"
    assert profile.confidence == "low"
    assert profile.inference_version == "audience-v1"


def test_non_null_values_are_unaffected() -> None:
    profile = AudienceProfile.model_validate(
        {
            "summary": "Families and young professionals",
            "occupation_groups": ["renter"],
            "source": "explicit",
            "confidence": "high",
        }
    )

    assert profile.summary == "Families and young professionals"
    assert profile.occupation_groups == ("renter",)
    assert profile.confidence == "high"
