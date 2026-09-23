"""Resolved behavioral audience context used by planning and scheduling."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator


class AudienceProfile(BaseModel):
    """Open-ended audience traits; occupation names are never hard-coded."""

    model_config = ConfigDict(extra="ignore")

    summary: str = ""
    occupation_groups: tuple[str, ...] = ()
    industries: tuple[str, ...] = ()
    seniority_levels: tuple[str, ...] = ()
    work_environments: tuple[str, ...] = ()
    schedule_patterns: tuple[str, ...] = ()
    attention_patterns: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()
    timezones: tuple[str, ...] = ()
    source: Literal["explicit", "inferred", "mixed", "fallback"] = "fallback"
    confidence: Literal["low", "medium", "high"] = "low"
    evidence: tuple[str, ...] = ()
    inference_version: str = "audience-v1"

    @model_validator(mode="before")
    @classmethod
    def _drop_explicit_nulls(cls, data: Any) -> Any:
        # Providers (notably small local models) send explicit JSON null for
        # "nothing here" instead of omitting the key or sending a type-correct
        # empty value ([], ""). Pydantic only applies a field's default when
        # the key is absent, so an explicit null would otherwise fail
        # validation for a field that is, in meaning, simply unset. Dropping
        # the key lets the declared default take over, for every field
        # uniformly rather than one tuple field at a time.
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if v is not None}
        return data

    def is_usable(self) -> bool:
        return bool(self.summary.strip()) and self.confidence in {"medium", "high"}
