-- Phase C: deterministic LinkedIn publishing account per Brand.
--
-- A brand (company_profiles row) may have ONE optional default LinkedIn account.
-- The account is one the SAME user connected (linkedin_accounts.id). This is the
-- account per-post scheduling binds to; ownership is still enforced in code.
--
-- Nullable: existing brands keep default_linkedin_account_id = NULL until the
-- owner chooses one. ON DELETE SET NULL means disconnecting/removing the account
-- row simply clears the brand default (never orphans a dangling id).
-- This migration is idempotent: safe to run more than once.

ALTER TABLE public.company_profiles
  ADD COLUMN IF NOT EXISTS default_linkedin_account_id uuid
    REFERENCES public.linkedin_accounts(id) ON DELETE SET NULL;

-- Index for the (rare) reverse lookup "which brands point at this account",
-- which the account-removal path may use.
CREATE INDEX IF NOT EXISTS idx_company_profiles_default_linkedin_account_id
  ON public.company_profiles (default_linkedin_account_id)
  WHERE default_linkedin_account_id IS NOT NULL;
