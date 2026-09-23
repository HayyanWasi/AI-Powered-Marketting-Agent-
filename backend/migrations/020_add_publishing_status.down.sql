-- Revert the 'publishing' status. Any post mid-claim is returned to 'scheduled'
-- so it remains eligible for the publisher and does not violate the constraint.

UPDATE public.linkedin_posts SET status = 'scheduled' WHERE status = 'publishing';

ALTER TABLE public.linkedin_posts
    DROP CONSTRAINT IF EXISTS linkedin_posts_status_check;

ALTER TABLE public.linkedin_posts
    ADD CONSTRAINT linkedin_posts_status_check
    CHECK (status IN ('draft', 'scheduled', 'published', 'failed'));
