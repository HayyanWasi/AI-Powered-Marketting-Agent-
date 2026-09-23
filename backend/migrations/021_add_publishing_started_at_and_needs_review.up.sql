-- Fail-closed stale-claim recovery for the LinkedIn publisher.
--
-- 1) publishing_started_at records when a post was atomically claimed
--    (scheduled -> publishing), so the publisher can detect claims that crashed
--    mid-publish (stuck in 'publishing' past LINKEDIN_PUBLISH_STALE_MINUTES).
-- 2) 'needs_review' is the fail-closed parking state for such stale claims.
--    Because this Unipile deployment cannot reconcile whether the remote post
--    was actually created, stale claims are NEVER auto-republished — they are
--    parked here for manual inspection.

ALTER TABLE public.linkedin_posts
    ADD COLUMN IF NOT EXISTS publishing_started_at timestamptz;

ALTER TABLE public.linkedin_posts
    DROP CONSTRAINT IF EXISTS linkedin_posts_status_check;

ALTER TABLE public.linkedin_posts
    ADD CONSTRAINT linkedin_posts_status_check
    CHECK (status IN ('draft', 'scheduled', 'publishing', 'published', 'failed', 'needs_review'));
