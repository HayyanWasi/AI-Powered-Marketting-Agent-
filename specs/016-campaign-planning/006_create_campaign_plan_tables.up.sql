-- Migration 006: Campaign Plan Tables
-- Apply this in the Supabase SQL editor.
-- Style matches 002_create_campaign_tables.up.sql.

-- ── Status enum ──────────────────────────────────────────────────────────────

DO $$ BEGIN
    CREATE TYPE campaign_plan_status AS ENUM (
        'Drafting',
        'Draft',
        'Refining',
        'Approved',
        'Superseded'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ── campaign_plans ───────────────────────────────────────────────────────────
-- One row per campaign. Tracks the lifecycle and points at the current version.

CREATE TABLE IF NOT EXISTS campaign_plans (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id         UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    status              campaign_plan_status NOT NULL DEFAULT 'Drafting',
    current_version     INTEGER NOT NULL DEFAULT 0,
    language            TEXT NOT NULL DEFAULT 'en',
    approved_at         TIMESTAMPTZ,
    approved_by         UUID,
    created_by          UUID NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT campaign_plans_campaign_id_unique UNIQUE (campaign_id)
);

CREATE INDEX IF NOT EXISTS idx_campaign_plans_campaign_id
    ON campaign_plans (campaign_id);

-- ── campaign_plan_versions ────────────────────────────────────────────────────
-- Append-only version ledger. Every revision is kept so a marketer can
-- ask to see an earlier draft.

CREATE TABLE IF NOT EXISTS campaign_plan_versions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id             UUID NOT NULL REFERENCES campaign_plans(id) ON DELETE CASCADE,
    version             INTEGER NOT NULL,
    document            JSONB NOT NULL,
    parent_version      INTEGER,
    change_summary      TEXT NOT NULL DEFAULT '',
    sections_changed    TEXT[] NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT campaign_plan_versions_plan_version_unique UNIQUE (plan_id, version)
);

CREATE INDEX IF NOT EXISTS idx_campaign_plan_versions_plan_id
    ON campaign_plan_versions (plan_id);

-- ── campaign_plan_messages ────────────────────────────────────────────────────
-- Refinement conversation thread. Each marketer message and the agent's reply
-- is stored here in chronological order.

CREATE TABLE IF NOT EXISTS campaign_plan_messages (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id             UUID NOT NULL REFERENCES campaign_plans(id) ON DELETE CASCADE,
    role                TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content             TEXT NOT NULL,
    language            TEXT NOT NULL DEFAULT 'en',
    sections_targeted   TEXT[] NOT NULL DEFAULT '{}',
    resulting_version   INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_campaign_plan_messages_plan_id
    ON campaign_plan_messages (plan_id);

-- ── updated_at trigger (reuse existing helper if present) ────────────────────

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS campaign_plans_updated_at ON campaign_plans;
CREATE TRIGGER campaign_plans_updated_at
    BEFORE UPDATE ON campaign_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
