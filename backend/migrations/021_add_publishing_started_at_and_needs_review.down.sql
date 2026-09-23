-- Revert fail-closed stale-claim recovery.
-- Any parked 'needs_review' rows are moved to 'failed' (a truthful terminal
-- state) so they neither violate the reverted constraint nor get republished.

UPDATE public.linkedin_posts SET status = 'failed' WHERE status = 'needs_review';

ALTER TABLE public.linkedin_posts
    DROP CONSTRAINT IF EXISTS linkedin_posts_status_check;

ALTER TABLE public.linkedin_posts
    ADD CONSTRAINT linkedin_posts_status_check
    CHECK (status IN ('draft', 'scheduled', 'publishing', 'published', 'failed'));

ALTER TABLE public.linkedin_posts
    DROP COLUMN IF EXISTS publishing_started_at;
