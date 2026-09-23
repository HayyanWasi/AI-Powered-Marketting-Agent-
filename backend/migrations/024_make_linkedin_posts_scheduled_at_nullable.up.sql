-- Migration 024: Make linkedin_posts.scheduled_at nullable
--
-- Allows draft posts to have scheduled_at = NULL, which enables cancel-schedule
-- to clear the scheduled timestamp without deleting the post.
-- Idempotent: safe to run even if already nullable.

ALTER TABLE public.linkedin_posts
ALTER COLUMN scheduled_at DROP NOT NULL;
