-- ═══════════════════════════════════════════════════════════════
-- Campaign Intake Messages & Sessions SQL Migration
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.intake_messages (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id   uuid        NOT NULL,
    role          text        NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content       text        NOT NULL DEFAULT '',
    language      text        NOT NULL DEFAULT 'en',
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_intake_messages_campaign_id
    ON public.intake_messages (campaign_id);

CREATE TABLE IF NOT EXISTS public.intake_checklists (
    id                      uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id             uuid        UNIQUE NOT NULL,
    event_name              text,
    event_date              text,
    venue                   text,
    has_guest               boolean     DEFAULT NULL,
    guest_name              text,
    guest_title             text,
    guest_confirmed         boolean     DEFAULT false,
    curriculum_breakdown    text,
    outcome_deliverable     text,
    is_free_or_paid         text,
    registration_link       text,
    target_audience         text,
    is_complete             boolean     DEFAULT false,
    updated_at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_intake_checklists_campaign_id
    ON public.intake_checklists (campaign_id);
