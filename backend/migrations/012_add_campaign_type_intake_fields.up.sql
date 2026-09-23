-- Align intake_checklists with the active IntakeChecklist application model.
-- All additions are nullable so existing rows remain valid.

ALTER TABLE public.intake_checklists
    ADD COLUMN IF NOT EXISTS campaign_type text,
    ADD COLUMN IF NOT EXISTS campaign_name text,
    ADD COLUMN IF NOT EXISTS objective text,
    ADD COLUMN IF NOT EXISTS value_proposition text,
    ADD COLUMN IF NOT EXISTS cta_url text,
    ADD COLUMN IF NOT EXISTS category text,
    ADD COLUMN IF NOT EXISTS guest_profile jsonb,
    ADD COLUMN IF NOT EXISTS last_field_asked text;
