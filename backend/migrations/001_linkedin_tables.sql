-- ═══════════════════════════════════════════════════════════════
-- LinkedIn Module SQL Migration
-- Run this in Supabase Dashboard > SQL Editor
-- ═══════════════════════════════════════════════════════════════

-- 1. LinkedIn Feed Posts
CREATE TABLE IF NOT EXISTS public.linkedin_posts (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id       uuid        NOT NULL,
    slot_id           text        NOT NULL DEFAULT '',
    scheduled_at      timestamptz NOT NULL DEFAULT now(),
    hook              text        NOT NULL DEFAULT '',
    body              text        NOT NULL DEFAULT '',
    cta_text          text        NOT NULL DEFAULT '',
    full_content      text        NOT NULL DEFAULT '',
    evidence_ids      text[]      DEFAULT '{}',
    status            text        NOT NULL DEFAULT 'draft'
                                  CHECK (status IN ('draft','scheduled','published','failed')),
    unipile_post_id   text,
    published_at      timestamptz,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_linkedin_posts_campaign_id
    ON public.linkedin_posts (campaign_id);

CREATE INDEX IF NOT EXISTS idx_linkedin_posts_status
    ON public.linkedin_posts (status);

-- 2. Outreach Sequences
CREATE TABLE IF NOT EXISTS public.outreach_sequences (
    id                      uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id             uuid        NOT NULL,
    prospect_linkedin_id    text        NOT NULL DEFAULT '',
    current_step            integer     NOT NULL DEFAULT 0,
    status                  text        NOT NULL DEFAULT 'pending'
                                        CHECK (status IN (
                                            'pending','visiting','connecting','connected',
                                            'replied','withdrawn','completed','failed'
                                        )),
    invite_id               text,
    connection_accepted_at  timestamptz,
    step_invite_msg         text        NOT NULL DEFAULT '',
    step_value_msg          text        NOT NULL DEFAULT '',
    step_followup_msg       text        NOT NULL DEFAULT '',
    created_at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_outreach_sequences_campaign_id
    ON public.outreach_sequences (campaign_id);

CREATE INDEX IF NOT EXISTS idx_outreach_sequences_status
    ON public.outreach_sequences (status);
