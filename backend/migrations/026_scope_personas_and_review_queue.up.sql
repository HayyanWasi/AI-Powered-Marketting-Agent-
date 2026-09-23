-- ═══════════════════════════════════════════════════════════════
-- Migration 026: Scope Personas, Review Queue & Normalize Accounts
-- ═══════════════════════════════════════════════════════════════

-- 1. Scope linkedin_target_personas
-- Clear legacy/unmapped rows if any
DELETE FROM public.linkedin_target_personas WHERE account_id IS NOT NULL;

ALTER TABLE public.linkedin_target_personas
    ADD COLUMN IF NOT EXISTS user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS company_profile_id UUID NOT NULL REFERENCES public.company_profiles(id) ON DELETE CASCADE;

-- Drop legacy unique constraint on (account_id, label) if exists
ALTER TABLE public.linkedin_target_personas
    DROP CONSTRAINT IF EXISTS linkedin_target_personas_account_id_label_key;

-- Brand-scoped persona label uniqueness
ALTER TABLE public.linkedin_target_personas
    ADD CONSTRAINT uq_target_personas_brand_label UNIQUE (company_profile_id, label);

CREATE INDEX IF NOT EXISTS idx_target_personas_brand_active
    ON public.linkedin_target_personas (company_profile_id, is_active);

ALTER TABLE public.linkedin_target_personas ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their own target personas" ON public.linkedin_target_personas;
CREATE POLICY "Users can manage their own target personas"
    ON public.linkedin_target_personas
    FOR ALL
    USING (user_id = auth.uid());

-- 2. Scope linkedin_review_queue
-- Clear legacy dummy queue items if any
DELETE FROM public.linkedin_review_queue;

ALTER TABLE public.linkedin_review_queue
    ADD COLUMN IF NOT EXISTS user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS company_profile_id UUID NOT NULL REFERENCES public.company_profiles(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS linkedin_account_id UUID NOT NULL REFERENCES public.linkedin_accounts(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS action_log_id UUID REFERENCES public.linkedin_engagement_log(id) ON DELETE SET NULL;

-- Update status check constraint
ALTER TABLE public.linkedin_review_queue
    DROP CONSTRAINT IF EXISTS linkedin_review_queue_status_check;

ALTER TABLE public.linkedin_review_queue
    ADD CONSTRAINT linkedin_review_queue_status_check
    CHECK (status IN (
        'pending_review', 'approved', 'rejected',
        'published', 'failed', 'needs_review', 'expired'
    ));

-- Permanent Comment Queue Dedupe: Unconditional (no status filter)
CREATE UNIQUE INDEX IF NOT EXISTS uq_review_queue_account_post 
    ON public.linkedin_review_queue (linkedin_account_id, target_post_id);

CREATE INDEX IF NOT EXISTS idx_review_queue_brand_status
    ON public.linkedin_review_queue (company_profile_id, status);

ALTER TABLE public.linkedin_review_queue ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their own review queue" ON public.linkedin_review_queue;
CREATE POLICY "Users can manage their own review queue"
    ON public.linkedin_review_queue
    FOR ALL
    USING (user_id = auth.uid());

-- 3. Normalize legacy account-keyed tables to canonical linkedin_accounts.id (UUID)

-- 3a. linkedin_daily_actions
DELETE FROM public.linkedin_daily_actions;
ALTER TABLE public.linkedin_daily_actions
    DROP CONSTRAINT IF EXISTS linkedin_daily_actions_account_id_action_date_action_type_key;
ALTER TABLE public.linkedin_daily_actions
    DROP COLUMN IF EXISTS account_id CASCADE;
ALTER TABLE public.linkedin_daily_actions
    ADD COLUMN IF NOT EXISTS linkedin_account_id UUID NOT NULL REFERENCES public.linkedin_accounts(id) ON DELETE CASCADE;
ALTER TABLE public.linkedin_daily_actions
    ADD CONSTRAINT uq_daily_actions_account_date_type UNIQUE (linkedin_account_id, action_date, action_type);
CREATE INDEX IF NOT EXISTS idx_daily_actions_account_date
    ON public.linkedin_daily_actions (linkedin_account_id, action_date);

-- 3b. linkedin_engaged_posts
DELETE FROM public.linkedin_engaged_posts;
ALTER TABLE public.linkedin_engaged_posts
    DROP CONSTRAINT IF EXISTS linkedin_engaged_posts_account_id_post_id_action_type_key;
ALTER TABLE public.linkedin_engaged_posts
    DROP COLUMN IF EXISTS account_id CASCADE;
ALTER TABLE public.linkedin_engaged_posts
    ADD COLUMN IF NOT EXISTS linkedin_account_id UUID NOT NULL REFERENCES public.linkedin_accounts(id) ON DELETE CASCADE;
ALTER TABLE public.linkedin_engaged_posts
    ADD CONSTRAINT uq_engaged_posts_account_post_action UNIQUE (linkedin_account_id, post_id, action_type);
CREATE INDEX IF NOT EXISTS idx_engaged_posts_account
    ON public.linkedin_engaged_posts (linkedin_account_id);

-- 3c. linkedin_warmup_state
DELETE FROM public.linkedin_warmup_state;
ALTER TABLE public.linkedin_warmup_state
    DROP CONSTRAINT IF EXISTS linkedin_warmup_state_account_id_key;
ALTER TABLE public.linkedin_warmup_state
    DROP COLUMN IF EXISTS account_id CASCADE;
ALTER TABLE public.linkedin_warmup_state
    ADD COLUMN IF NOT EXISTS linkedin_account_id UUID NOT NULL REFERENCES public.linkedin_accounts(id) ON DELETE CASCADE;
ALTER TABLE public.linkedin_warmup_state
    ADD CONSTRAINT uq_warmup_state_account UNIQUE (linkedin_account_id);
CREATE INDEX IF NOT EXISTS idx_warmup_state_account
    ON public.linkedin_warmup_state (linkedin_account_id);

-- 3d. linkedin_circuit_breaker
DELETE FROM public.linkedin_circuit_breaker;
ALTER TABLE public.linkedin_circuit_breaker
    DROP CONSTRAINT IF EXISTS linkedin_circuit_breaker_account_id_key;
ALTER TABLE public.linkedin_circuit_breaker
    DROP COLUMN IF EXISTS account_id CASCADE;
ALTER TABLE public.linkedin_circuit_breaker
    ADD COLUMN IF NOT EXISTS linkedin_account_id UUID NOT NULL REFERENCES public.linkedin_accounts(id) ON DELETE CASCADE;
ALTER TABLE public.linkedin_circuit_breaker
    ADD CONSTRAINT uq_circuit_breaker_account UNIQUE (linkedin_account_id);
CREATE INDEX IF NOT EXISTS idx_circuit_breaker_account
    ON public.linkedin_circuit_breaker (linkedin_account_id);
0    