-- Dedicated persistence for in-app LinkedIn account connections (Unipile Hosted Auth).
-- Maps a verified Unipile account to the internal user who connected it.
-- No LinkedIn credentials/passwords/cookies are stored here — only the Unipile
-- account identifier and its verified status.

CREATE TABLE IF NOT EXISTS public.linkedin_accounts (
    id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             uuid        NOT NULL,
    unipile_account_id  text        NOT NULL,
    provider            text        NOT NULL DEFAULT 'LINKEDIN',
    status              text        NOT NULL DEFAULT 'connected'
                                    CHECK (status IN ('connected','disconnected','failed')),
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    last_verified_at    timestamptz,
    -- One row per Unipile account; a reconnect/duplicate callback upserts it.
    CONSTRAINT uq_linkedin_accounts_unipile_account_id UNIQUE (unipile_account_id)
);

CREATE INDEX IF NOT EXISTS idx_linkedin_accounts_user_id
    ON public.linkedin_accounts (user_id);

-- Row Level Security: a user may only see/manage their own connected accounts.
-- (The backend uses the service key and additionally filters by user_id in code;
-- this policy is defense-in-depth, matching the project's RLS conventions.)
ALTER TABLE public.linkedin_accounts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access their own linkedin accounts"
ON public.linkedin_accounts FOR ALL
USING (user_id = auth.uid());
