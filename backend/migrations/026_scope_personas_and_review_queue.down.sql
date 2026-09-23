-- Migration 026: Revert scoping of personas and review queue

ALTER TABLE public.linkedin_target_personas
    DROP CONSTRAINT IF EXISTS uq_target_personas_brand_label,
    DROP COLUMN IF EXISTS company_profile_id CASCADE,
    DROP COLUMN IF EXISTS user_id CASCADE;

ALTER TABLE public.linkedin_review_queue
    DROP CONSTRAINT IF EXISTS uq_review_queue_account_post,
    DROP COLUMN IF EXISTS action_log_id CASCADE,
    DROP COLUMN IF EXISTS linkedin_account_id CASCADE,
    DROP COLUMN IF EXISTS company_profile_id CASCADE,
    DROP COLUMN IF EXISTS user_id CASCADE;
