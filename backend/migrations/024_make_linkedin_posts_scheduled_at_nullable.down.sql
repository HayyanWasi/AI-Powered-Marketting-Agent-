-- Migration 024 Down: Restore NOT NULL constraint on linkedin_posts.scheduled_at
--
-- CAUTION / NOTE:
-- This rollback requires all rows in public.linkedin_posts to have a non-null scheduled_at value.
-- If any rows have scheduled_at IS NULL (e.g. cancelled draft posts), this migration WILL FAIL.
-- Per policy, fake dates must NOT be auto-filled here; any NULL values must be resolved explicitly
-- prior to running this rollback.

ALTER TABLE public.linkedin_posts
ALTER COLUMN scheduled_at SET NOT NULL;
