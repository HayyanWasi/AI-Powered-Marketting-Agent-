-- Migration 007: Research Engine Tables
-- Apply this in the Supabase SQL editor or PostgreSQL database.

-- ── Research Sessions ────────────────────────────────────────────────────────
-- Stores execution metadata, tier parameters, status, total cost, and latency.

CREATE TABLE IF NOT EXISTS research_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id         UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    tier                TEXT NOT NULL CHECK (tier IN ('Quick', 'Standard', 'Deep')),
    status              TEXT NOT NULL DEFAULT 'running',
    total_searches      INTEGER NOT NULL DEFAULT 0,
    total_llm_calls     INTEGER NOT NULL DEFAULT 0,
    total_latency_ms    INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd  NUMERIC(10, 6) NOT NULL DEFAULT 0.000000,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_research_sessions_campaign_id
    ON research_sessions (campaign_id);

-- ── Search Audit Log ─────────────────────────────────────────────────────────
-- Logs every single web query, search provider, hit count, latency, and tokens.

CREATE TABLE IF NOT EXISTS search_audit_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    dimension           TEXT NOT NULL,
    query               TEXT NOT NULL,
    provider            TEXT NOT NULL,
    results_count       INTEGER NOT NULL DEFAULT 0,
    latency_ms          INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_search_audit_log_session_id
    ON search_audit_log (session_id);

-- ── Dimension Confidence & Abandonment Metrics ────────────────────────────────

CREATE TABLE IF NOT EXISTS dimension_confidence (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    dimension           TEXT NOT NULL,
    confidence_score    NUMERIC(3, 2) NOT NULL DEFAULT 0.00,
    iterations_run      INTEGER NOT NULL DEFAULT 1,
    sources_abandoned   INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dimension_confidence_session_id
    ON dimension_confidence (session_id);

-- ── Research Evidence Graphs (JSONB Fallback for Neo4j) ─────────────────────
-- Persistent fallback storage for the Evidence Graph (Nodes + Edges).
-- Survives server restarts even if Neo4j graph database is offline.

CREATE TABLE IF NOT EXISTS research_evidence_graphs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    document            JSONB NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT research_evidence_graphs_session_unique UNIQUE (session_id)
);

CREATE INDEX IF NOT EXISTS idx_research_evidence_graphs_session_id
    ON research_evidence_graphs (session_id);
