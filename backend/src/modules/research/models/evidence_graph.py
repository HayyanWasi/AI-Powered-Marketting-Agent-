"""Evidence Graph schema (Decision -> Evidence -> Source) for Neo4j and Postgres JSONB."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class DecisionNode(BaseModel):
    """A strategic decision node in the graph."""

    model_config = ConfigDict(frozen=True)

    decision_id: str = Field(default_factory=lambda: f"dec_{uuid4().hex[:8]}")
    title: str
    dimension: str
    rationale: str
    confidence_score: float = 4.0


class EvidenceNode(BaseModel):
    """An evidence node in the graph."""

    model_config = ConfigDict(frozen=True)

    evidence_id: str
    claim: str
    quote: str
    confidence_score: float


class SourceNode(BaseModel):
    """A source node in the graph."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    url: str
    title: str
    domain: str


class EvidenceGraph(BaseModel):
    """Complete graph representation with nodes and edges."""

    model_config = ConfigDict(frozen=True)

    decisions: tuple[DecisionNode, ...] = ()
    evidence_nodes: tuple[EvidenceNode, ...] = ()
    source_nodes: tuple[SourceNode, ...] = ()
    # Edges: (from_id, to_id, relationship_type)
    edges: tuple[tuple[str, str, str], ...] = ()

    @classmethod
    def create_empty(cls) -> EvidenceGraph:
        return cls()

    def to_dict(self) -> dict[str, Any]:
        return {
            "decisions": [d.model_dump() for d in self.decisions],
            "evidence_nodes": [e.model_dump() for e in self.evidence_nodes],
            "source_nodes": [s.model_dump() for s in self.source_nodes],
            "edges": [
                {"from_id": e[0], "to_id": e[1], "relationship": e[2]}
                for e in self.edges
            ],
        }
