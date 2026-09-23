-- ═══════════════════════════════════════════════════════════════
-- Migration 025: Engagement Settings and Durable Event Log
-- ═══════════════════════════════════════════════════════════════

-- 1. Brand-scoped Engagement Settings
CREATE TABLE IF NOT EXISTS public.linkedin_engagement_settings (
    id                                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                             UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    company_profile_id                  UUID NOT NULL REFERENCES public.company_profiles(id) ON DELETE CASCADE,
    linkedin_account_id                 UUID REFERENCES public.linkedin_accounts(id) ON DELETE SET NULL,
    engagement_enabled                  BOOLEAN NOT NULL DEFAULT false,
    auto_like_enabled                   BOOLEAN NOT NULL DEFAULT false,
    auto_comment_generation_enabled     BOOLEAN NOT NULL DEFAULT false,
    auto_connect_enabled                BOOLEAN NOT NULL DEFAULT false,
    likes_per_day                       INTEGER NOT NULL DEFAULT 15 CHECK (likes_per_day >= 0 AND likes_per_day <= 100),
    comments_per_day                    INTEGER NOT NULL DEFAULT 5 CHECK (comments_per_day >= 0 AND comments_per_day <= 50),
    invites_per_day                     INTEGER NOT NULL DEFAULT 10 CHECK (invites_per_day >= 0 AND invites_per_day <= 40),
    connection_note_template            TEXT NOT NULL DEFAULT '',
    timezone                            TEXT NOT NULL DEFAULT 'UTC',
    created_at                          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_engagement_settings_brand UNIQUE (company_profile_id)
);

CREATE INDEX IF NOT EXISTS idx_engagement_settings_user
    ON public.linkedin_engagement_settings (user_id);

CREATE INDEX IF NOT EXISTS idx_engagement_settings_account
    ON public.linkedin_engagement_settings (linkedin_account_id);

ALTER TABLE public.linkedin_engagement_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own engagement settings"
    ON public.linkedin_engagement_settings
    FOR ALL
    USING (user_id = auth.uid());

-- 2. Authoritative Durable Event Log & Pre-Dispatch Claim Anchor
CREATE TABLE IF NOT EXISTS public.linkedin_engagement_log (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    company_profile_id      UUID NOT NULL REFERENCES public.company_profiles(id) ON DELETE CASCADE,
    linkedin_account_id     UUID NOT NULL REFERENCES public.linkedin_accounts(id) ON DELETE CASCADE,
    action_type             TEXT NOT NULL CHECK (action_type IN ('like', 'comment', 'connection_request')),
    target_post_id          TEXT,
    target_profile_id       TEXT,
    review_queue_id         UUID REFERENCES public.linkedin_review_queue(id) ON DELETE SET NULL,
    comment_text            TEXT,
    status                  TEXT NOT NULL CHECK (status IN ('claimed', 'succeeded', 'failed', 'needs_review')),
    provider_result_id      TEXT,
    error_message           TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at            TIMESTAMPTZ
);

-- PERMANENT IDEMPOTENCY CONSTRAINTS (Regardless of status)
-- 1. Like permanence
CREATE UNIQUE INDEX IF NOT EXISTS uq_engagement_log_account_post_like 
    ON public.linkedin_engagement_log (linkedin_account_id, target_post_id) 
    WHERE action_type = 'like';

-- 2. Comment permanence
CREATE UNIQUE INDEX IF NOT EXISTS uq_engagement_log_account_post_comment 
    ON public.linkedin_engagement_log (linkedin_account_id, target_post_id) 
    WHERE action_type = 'comment';

-- 3. Connection request permanence
CREATE UNIQUE INDEX IF NOT EXISTS uq_engagement_log_account_profile_invite 
    ON public.linkedin_engagement_log (linkedin_account_id, target_profile_id) 
    WHERE action_type = 'connection_request';

CREATE INDEX IF NOT EXISTS idx_engagement_log_brand_time
    ON public.linkedin_engagement_log (company_profile_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_engagement_log_status
    ON public.linkedin_engagement_log (status);

ALTER TABLE public.linkedin_engagement_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own engagement logs"
    ON public.linkedin_engagement_log
    FOR ALL
    USING (user_id = auth.uid());
