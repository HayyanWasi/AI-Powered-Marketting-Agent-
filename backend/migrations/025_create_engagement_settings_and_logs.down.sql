-- Migration 025: Drop engagement settings and log tables

DROP TABLE IF EXISTS public.linkedin_engagement_log CASCADE;
DROP TABLE IF EXISTS public.linkedin_engagement_settings CASCADE;
