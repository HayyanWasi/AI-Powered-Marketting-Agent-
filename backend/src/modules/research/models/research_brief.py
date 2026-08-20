"""Structured Research Brief combining 6 worker dimensions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.modules.research.models.evidence import EvidenceItem


class DimensionSummary(BaseModel):
    """Unified summary for one research dimension."""

    model_config = ConfigDict(frozen=True)

    dimension: str
    key_findings: tuple[str, ...] = ()
    evidence_items: tuple[EvidenceItem, ...] = ()
    confidence_score: float = 4.0
    sources_count: int = 0
    abandoned_sources_count: int = 0


class ResearchBrief(BaseModel):
    """The master Research Brief passed to Strategy Reasoner."""

    model_config = ConfigDict(frozen=True)

    brief_id: UUID = Field(default_factory=uuid4)
    session_id: UUID | None = None
    user_goal: str = ""
    company_name: str = ""

    market: DimensionSummary = Field(
        default_factory=lambda: DimensionSummary(dimension="market")
    )
    competitor: DimensionSummary = Field(
        default_factory=lambda: DimensionSummary(dimension="competitor")
    )
    audience: DimensionSummary = Field(
        default_factory=lambda: DimensionSummary(dimension="audience")
    )
    content: DimensionSummary = Field(
        default_factory=lambda: DimensionSummary(dimension="content")
    )
    channel: DimensionSummary = Field(
        default_factory=lambda: DimensionSummary(dimension="channel")
    )
    trend: DimensionSummary = Field(
        default_factory=lambda: DimensionSummary(dimension="trend")
    )

    overall_confidence_score: float = 4.0
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
