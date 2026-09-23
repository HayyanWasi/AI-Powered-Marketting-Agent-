-- Add a transient 'publishing' status to linkedin_posts.
--
-- The scheduled publisher atomically moves a post from 'scheduled' -> 'publishing'
-- before dispatching it to Unipile. Because that UPDATE is guarded by
-- WHERE status = 'scheduled', exactly one worker/process can claim a given post,
-- which prevents duplicate publishes (e.g. the startup job racing the interval
-- job, or multiple replicas).

ALTER TABLE public.linkedin_posts
    DROP CONSTRAINT IF EXISTS linkedin_posts_status_check;

ALTER TABLE public.linkedin_posts
    ADD CONSTRAINT linkedin_posts_status_check
    CHECK (status IN ('draft', 'scheduled', 'publishing', 'published', 'failed'));
