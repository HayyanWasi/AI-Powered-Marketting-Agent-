-- ═══════════════════════════════════════════════════════════════
-- LinkedIn Scheduler & Anti-Detection Engine Tables
-- Run this in Supabase Dashboard > SQL Editor
-- ═══════════════════════════════════════════════════════════════

-- 1. Warm-Up State (persisted, survives restarts)
CREATE TABLE IF NOT EXISTS public.linkedin_warmup_state (
    id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id                  text NOT NULL UNIQUE,
    activation_date             date NOT NULL DEFAULT CURRENT_DATE,
    days_active                 integer NOT NULL DEFAULT 0,
    current_daily_invite_limit  integer NOT NULL DEFAULT 10,
    current_daily_engage_limit  integer NOT NULL DEFAULT 15,
    phase                       text NOT NULL DEFAULT 'ramp_up'
                                CHECK (phase IN ('baseline', 'ramp_up', 'operating')),
    last_limit_increase_date    date,
    updated_at                  timestamptz DEFAULT now()
);

-- 2. Review Queue (mandatory human approval — PostgreSQL backed)
CREATE TABLE IF NOT EXISTS public.linkedin_review_queue (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    target_post_id      text NOT NULL,
    target_post_snippet text NOT NULL DEFAULT '',
    target_author_name  text NOT NULL DEFAULT '',
    persona_label       text NOT NULL DEFAULT '',
    generated_text      text NOT NULL,
    status              text NOT NULL DEFAULT 'pending_review'
                        CHECK (status IN (
                            'pending_review', 'approved', 'rejected',
                            'published', 'expired'
                        )),
    reject_reason       text DEFAULT '',
    unipile_id          text,
    generated_at        timestamptz NOT NULL DEFAULT now(),
    reviewed_at         timestamptz,
    published_at        timestamptz,
    expires_at          timestamptz DEFAULT (now() + interval '48 hours')
);
CREATE INDEX IF NOT EXISTS idx_review_queue_status
    ON public.linkedin_review_queue (status);

-- 3. Daily Action Log (timezone-aware, atomic upsert)
--    action_date stores the LOCAL date in the account's timezone
--    Set by the application using AT TIME ZONE, NOT by CURRENT_DATE
CREATE TABLE IF NOT EXISTS public.linkedin_daily_actions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id      text NOT NULL,
    action_date     date NOT NULL,
    action_type     text NOT NULL,
    action_count    integer NOT NULL DEFAULT 0,
    UNIQUE(account_id, action_date, action_type)
);
CREATE INDEX IF NOT EXISTS idx_daily_actions_account_date
    ON public.linkedin_daily_actions (account_id, action_date);

-- 4. Circuit Breaker State (persisted across restarts)
CREATE TABLE IF NOT EXISTS public.linkedin_circuit_breaker (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id      text NOT NULL UNIQUE,
    state           text NOT NULL DEFAULT 'closed'
                    CHECK (state IN ('closed', 'open', 'half_open')),
    tripped_at      timestamptz,
    trip_reason     text,
    cooldown_hours  float DEFAULT 4.0,
    updated_at      timestamptz DEFAULT now()
);

-- 5. Target Personas (dynamic — managed via DB, not config)
CREATE TABLE IF NOT EXISTS public.linkedin_target_personas (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id      text NOT NULL,
    label           text NOT NULL,
    search_keywords text NOT NULL,
    max_profiles    integer NOT NULL DEFAULT 150,
    is_active       boolean NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz DEFAULT now(),
    UNIQUE(account_id, label)
);
CREATE INDEX IF NOT EXISTS idx_target_personas_account
    ON public.linkedin_target_personas (account_id, is_active);

-- 6. Resolved Targets Cache (refreshed weekly)
CREATE TABLE IF NOT EXISTS public.linkedin_resolved_targets (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id      text NOT NULL,
    persona_label   text NOT NULL,
    profile_id      text NOT NULL,
    display_name    text NOT NULL DEFAULT '',
    headline        text NOT NULL DEFAULT '',
    resolved_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE(account_id, persona_label, profile_id)
);
CREATE INDEX IF NOT EXISTS idx_resolved_targets_account
    ON public.linkedin_resolved_targets (account_id, persona_label);

-- 7. Engaged Posts Dedup (never re-engage same post)
CREATE TABLE IF NOT EXISTS public.linkedin_engaged_posts (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id      text NOT NULL,
    post_id         text NOT NULL,
    action_type     text NOT NULL,
    engaged_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE(account_id, post_id, action_type)
);
CREATE INDEX IF NOT EXISTS idx_engaged_posts_account
    ON public.linkedin_engaged_posts (account_id);
