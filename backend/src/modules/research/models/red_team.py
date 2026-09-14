"""Red Team counter-evidence models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class CounterEvidenceClaim(BaseModel):
    """A claim challenged by counter-evidence search."""

    model_config = ConfigDict(frozen=True)

    claim_id: str = Field(default_factory=lambda: f"claim_{uuid4().hex[:8]}")
    target_dimension: str
    original_claim: str
    counter_evidence_quote: str
    counter_source_url: str
    risk_level: str = "Medium"  # Low, Medium, High
    explanation: str = ""


class RedTeamReport(BaseModel):
    """Complete adversarial evaluation report."""

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(default_factory=lambda: f"red_{uuid4().hex[:8]}")
    counter_claims: tuple[CounterEvidenceClaim, ...] = ()
    weak_assumptions_flagged: tuple[str, ...] = ()
    overall_risk_score: float = Field(default=0.2, ge=0.0, le=1.0)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "counter_claims": [c.model_dump() for c in self.counter_claims],
            "weak_assumptions_flagged": list(self.weak_assumptions_flagged),
            "overall_risk_score": self.overall_risk_score,
            "generated_at": self.generated_at.isoformat(),
        }
