-- Roll back the per-brand default LinkedIn account binding.

DROP INDEX IF EXISTS public.idx_company_profiles_default_linkedin_account_id;

ALTER TABLE public.company_profiles
  DROP COLUMN IF EXISTS default_linkedin_account_id;
