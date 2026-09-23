-- Bind campaign and temporary intake rows to an authenticated owner.

ALTER TABLE public.intake_checklists
ADD COLUMN IF NOT EXISTS owner_id UUID;

ALTER TABLE public.intake_messages
ADD COLUMN IF NOT EXISTS owner_id UUID;

-- Campaign-bound intake has an authoritative owner relationship already.
-- Temporary legacy UUIDs cannot be safely inferred and intentionally remain NULL.
UPDATE public.intake_checklists AS checklist
SET owner_id = campaign.organization_id
FROM public.campaigns AS campaign
WHERE checklist.campaign_id = campaign.id
  AND checklist.owner_id IS NULL;

UPDATE public.intake_messages AS message
SET owner_id = campaign.organization_id
FROM public.campaigns AS campaign
WHERE message.campaign_id = campaign.id
  AND message.owner_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_intake_checklists_owner_campaign
ON public.intake_checklists (owner_id, campaign_id);

CREATE INDEX IF NOT EXISTS idx_intake_messages_owner_campaign
ON public.intake_messages (owner_id, campaign_id);
