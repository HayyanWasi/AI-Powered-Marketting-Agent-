-- Roll back in-app LinkedIn account connection persistence.

DROP POLICY IF EXISTS "Users can access their own linkedin accounts" ON public.linkedin_accounts;

DROP INDEX IF EXISTS public.idx_linkedin_accounts_user_id;

DROP TABLE IF EXISTS public.linkedin_accounts;
