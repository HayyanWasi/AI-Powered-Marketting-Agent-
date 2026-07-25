-- Add previous_state column to campaigns table.
-- Required by archive/restore workflow: stores the state before archiving
-- so restore knows what state to revert to.

ALTER TABLE public.campaigns
  ADD COLUMN IF NOT EXISTS previous_state campaign_state;
