"""Neo4j Graph Database Driver with PostgreSQL JSONB Fallback.

Manages Cypher graph queries for the Evidence Graph:
(:Decision)-[:SUPPORTED_BY]->(:Evidence)-[:CITED_FROM]->(:Source)

If Neo4j is offline or unconfigured, gracefully falls back to PostgresService JSONB
so the "Why?" engine and conversation layer stay 100% operational.
"""

from __future__ import annotations

import logging
import os
from typing import Any
from uuid import UUID

from src.modules.research.services.postgres_service import PostgresService

logger = logging.getLogger(__name__)


class Neo4jService:
    """Neo4j Graph Driver with Postgres JSONB fallback."""

    def __init__(self, postgres: PostgresService | None = None) -> None:
        self.postgres = postgres or PostgresService()
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self._driver = None

    @property
    def is_connected(self) -> bool:
        """Check if Neo4j is configured and active."""
        return self._driver is not None

    async def save_evidence_nodes(
        self,
        session_id: UUID | str,
        evidence_items: list[dict[str, Any]],
    ) -> None:
        """Save Evidence and Source nodes and CITED_FROM relationships."""
        # Always persist JSONB fallback first
        graph_doc = await self.postgres.get_evidence_graph_fallback(session_id) or {
            "evidence_nodes": [],
            "edges": [],
        }
        graph_doc["evidence_nodes"] = evidence_items
        await self.postgres.save_evidence_graph_fallback(session_id, graph_doc)

        if not self.is_connected:
            logger.info("Neo4j offline; saved evidence nodes to Postgres JSONB fallback")
            return

        # Execute Cypher query if Neo4j driver is active
        try:
            query = """
            UNWIND $items AS item
            MERGE (s:Source {source_id: item.source.source_id})
            SET s.url = item.source.url, s.title = item.source.title, s.domain = item.source.domain
            MERGE (e:Evidence {evidence_id: item.evidence_id})
            SET e.claim = item.claim, e.quote = item.quote, e.confidence = item.confidence_score
            MERGE (e)-[:CITED_FROM]->(s)
            """
            with self._driver.session() as session:
                session.run(query, items=evidence_items)
            logger.info("Saved %d evidence nodes to Neo4j", len(evidence_items))
        except Exception as e:
            logger.warning("Neo4j Cypher write failed (%s); falling back to Postgres", e)

    async def link_decisions(
        self,
        session_id: UUID | str,
        decisions: list[dict[str, Any]],
    ) -> None:
        """Link Decision nodes to Evidence nodes with SUPPORTED_BY relationship."""
        graph_doc = await self.postgres.get_evidence_graph_fallback(session_id) or {}
        graph_doc["decisions"] = decisions
        await self.postgres.save_evidence_graph_fallback(session_id, graph_doc)

        if not self.is_connected:
            logger.info("Neo4j offline; saved decision links to Postgres JSONB fallback")
            return

        try:
            query = """
            UNWIND $decisions AS d
            MERGE (dec:Decision {decision_id: d.decision_id})
            SET dec.title = d.title, dec.dimension = d.dimension, dec.rationale = d.rationale
            WITH dec, d
            UNWIND d.evidence_ids AS e_id
            MATCH (e:Evidence {evidence_id: e_id})
            MERGE (dec)-[:SUPPORTED_BY]->(e)
            """
            with self._driver.session() as session:
                session.run(query, decisions=decisions)
            logger.info("Linked decisions in Neo4j")
        except Exception as e:
            logger.warning("Neo4j link_decisions failed (%s); fallback active", e)

    async def query_why_trace(self, session_id: UUID | str, decision_id: str) -> dict[str, Any]:
        """Execute Cypher query for "Why?" explainability.

        Query: (Decision)-[:SUPPORTED_BY]->(Evidence)-[:CITED_FROM]->(Source)
        Falls back to traversing Postgres JSONB document if Neo4j is offline.
        """
        if self.is_connected:
            try:
                query = """
                MATCH (d:Decision {decision_id: $dec_id})-[:SUPPORTED_BY]->(e:Evidence)-[:CITED_FROM]->(s:Source)
                RETURN d, collect(e) AS evidences, collect(s) AS sources
                """
                with self._driver.session() as session:
                    res = session.run(query, dec_id=decision_id)
                    record = res.single()
                    if record:
                        return {
                            "decision": dict(record["d"]),
                            "evidences": [dict(e) for e in record["evidences"]],
                            "sources": [dict(s) for s in record["sources"]],
                        }
            except Exception as e:
                logger.warning("Neo4j query_why_trace failed (%s); using Postgres fallback", e)

        # Postgres JSONB Traversal Fallback
        doc = await self.postgres.get_evidence_graph_fallback(session_id)
        if not doc:
            return {"decision": {}, "evidences": [], "sources": []}

        # Filter decision & linked evidences from JSONB doc
        decisions = doc.get("decisions", [])
        evidences = doc.get("evidence_nodes", [])
        matched_dec = next((d for d in decisions if d.get("decision_id") == decision_id), {})
        return {
            "decision": matched_dec,
            "evidences": evidences,
            "sources": [e.get("source") for e in evidences if "source" in e],
        }
