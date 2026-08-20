"""Evidence and Source models with explicit confidence scoring."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class SourceItem(BaseModel):
    """Source provenance model."""

    model_config = ConfigDict(frozen=True)

    source_id: str = Field(default_factory=lambda: f"src_{uuid4().hex[:8]}")
    url: str
    title: str = ""
    domain: str = ""
    published_date: str = ""
    credibility_score: float = Field(default=0.8, ge=0.0, le=1.0)


class ConfidenceScore(BaseModel):
    """Explicit confidence formula breakdown.

    Score = (Corroboration * 0.35) + (Freshness * 0.25) + (Relevance * 0.25) + (Credibility * 0.15)
    Values normalized to 1.0 - 5.0 rating scale.
    """

    model_config = ConfigDict(frozen=True)

    corroboration: float = Field(default=3.0, ge=1.0, le=5.0)
    freshness: float = Field(default=4.0, ge=1.0, le=5.0)
    relevance: float = Field(default=4.0, ge=1.0, le=5.0)
    credibility: float = Field(default=4.0, ge=1.0, le=5.0)

    @property
    def composite_score(self) -> float:
        """Calculates final composite confidence score (1.0 to 5.0)."""
        score = (
            (self.corroboration * 0.35)
            + (self.freshness * 0.25)
            + (self.relevance * 0.25)
            + (self.credibility * 0.15)
        )
        return round(score, 2)


class EvidenceItem(BaseModel):
    """A single piece of validated web evidence."""

    model_config = ConfigDict(frozen=True)

    evidence_id: str = Field(default_factory=lambda: f"evi_{uuid4().hex[:8]}")
    dimension: str  # market, competitor, audience, content, channel, trend
    claim: str
    quote: str
    source: SourceItem
    confidence: ConfidenceScore = Field(default_factory=ConfidenceScore)
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON representation."""
        return {
            "evidence_id": self.evidence_id,
            "dimension": self.dimension,
            "claim": self.claim,
            "quote": self.quote,
            "source": self.source.model_dump(),
            "confidence_score": self.confidence.composite_score,
            "confidence_breakdown": self.confidence.model_dump(),
            "extracted_at": self.extracted_at.isoformat(),
        }
