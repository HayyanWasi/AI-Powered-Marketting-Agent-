-- Reverse 018: drop the campaign validity window columns.

ALTER TABLE public.intake_checklists
    DROP COLUMN IF EXISTS campaign_start_date,
    DROP COLUMN IF EXISTS campaign_end_date;
