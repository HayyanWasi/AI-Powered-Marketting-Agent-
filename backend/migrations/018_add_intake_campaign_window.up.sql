-- Add the campaign validity window to intake_checklists so the confirmed
-- scheduling bounds survive persistence. Distinct from event_date (an actual
-- event/webinar date). Both nullable so existing rows remain valid.

ALTER TABLE public.intake_checklists
    ADD COLUMN IF NOT EXISTS campaign_start_date text,
    ADD COLUMN IF NOT EXISTS campaign_end_date text;
