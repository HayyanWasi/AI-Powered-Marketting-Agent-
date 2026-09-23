-- Migration: Fix company_profiles schema to match application field names.
-- Run this in your Supabase Dashboard SQL Editor.
-- This migration is idempotent: safe to run even if columns already exist.

-- 1. Add user_id for per-user ownership (RLS-ready).
ALTER TABLE public.company_profiles
  ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

-- 2. Rename legacy "name" → "company_name" if the old column still exists
--    and "company_name" does not yet exist.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'company_profiles' AND column_name = 'name'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'company_profiles' AND column_name = 'company_name'
  ) THEN
    ALTER TABLE public.company_profiles RENAME COLUMN name TO company_name;
  END IF;
END $$;

-- 3. If "company_name" still doesn't exist (table never had "name" either),
--    create it.
ALTER TABLE public.company_profiles
  ADD COLUMN IF NOT EXISTS company_name TEXT NOT NULL DEFAULT '';

-- 4. Rename legacy "tone" → "brand_tone" if the old column still exists
--    and "brand_tone" does not yet exist.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'company_profiles' AND column_name = 'tone'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'company_profiles' AND column_name = 'brand_tone'
  ) THEN
    ALTER TABLE public.company_profiles RENAME COLUMN tone TO brand_tone;
  END IF;
END $$;

-- 5. Ensure brand_tone column exists.
ALTER TABLE public.company_profiles
  ADD COLUMN IF NOT EXISTS brand_tone TEXT;

-- 6. Ensure brand_guidelines column exists (stores JSON-serialised BrandProfileData).
ALTER TABLE public.company_profiles
  ADD COLUMN IF NOT EXISTS brand_guidelines TEXT NOT NULL DEFAULT '';

-- 7. Drop the old name uniqueness index (if it references the old "name" column).
DROP INDEX IF EXISTS idx_company_profiles_name;

-- 8. Recreate uniqueness index per user (a user can't have two brands with
--    the same name, but different users can share a name).
CREATE UNIQUE INDEX IF NOT EXISTS idx_company_profiles_user_name
  ON public.company_profiles (user_id, company_name)
  WHERE user_id IS NOT NULL;

-- 9. Index for listing all profiles owned by a specific user efficiently.
CREATE INDEX IF NOT EXISTS idx_company_profiles_user_id
  ON public.company_profiles (user_id);

-- 10. Ensure the updated_at trigger function exists and the trigger is wired up.
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.triggers
    WHERE trigger_name = 'update_company_profiles_updated_at'
    AND event_object_table = 'company_profiles'
  ) THEN
    CREATE TRIGGER update_company_profiles_updated_at
      BEFORE UPDATE ON public.company_profiles
      FOR EACH ROW
      EXECUTE FUNCTION update_updated_at_column();
  END IF;
END $$;

