-- Campaign Management Tables
-- Run this in your Supabase Dashboard SQL Editor

-- 1. Campaign state enum (capitalized to match Python enum)
DROP TYPE IF EXISTS campaign_state;
CREATE TYPE campaign_state AS ENUM (
  'Draft', 'Ready', 'Review', 'Approved', 'Published', 'Archived'
);

-- 2. Campaigns table
CREATE TABLE IF NOT EXISTS public.campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL,
  company_profile_id UUID REFERENCES public.company_profiles(id),
  name TEXT NOT NULL,
  goals JSONB NOT NULL DEFAULT '{}',
  target_audience JSONB NOT NULL DEFAULT '{}',
  platforms TEXT[] NOT NULL DEFAULT '{}',
  schedule JSONB NOT NULL DEFAULT '{}',
  metadata JSONB DEFAULT '{}',
  state campaign_state NOT NULL DEFAULT 'Draft',
  version INT NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  published_at TIMESTAMPTZ,
  archived_at TIMESTAMPTZ,
  created_by UUID NOT NULL,
  updated_by UUID NOT NULL,
  UNIQUE(organization_id, name)
);
-- 3. Campaign history (append-only audit log)
CREATE TABLE IF NOT EXISTS public.campaign_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES public.campaigns(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT now(),
  actor_id UUID NOT NULL,
  from_state campaign_state,
  to_state campaign_state,
  changed_fields JSONB,
  snapshot JSONB,
  metadata JSONB
);

-- 4. Campaign assets (copy, images, hashtags)
CREATE TABLE IF NOT EXISTS public.campaign_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES public.campaigns(id) ON DELETE CASCADE,
  asset_type TEXT NOT NULL,
  content JSONB DEFAULT '{}',
  storage_path TEXT,
  source TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  created_by UUID NOT NULL
);

-- 5. Indexes
CREATE INDEX idx_campaigns_org_state ON campaigns(organization_id, state);
CREATE INDEX idx_campaigns_org_updated ON campaigns(organization_id, updated_at DESC);
CREATE INDEX idx_campaigns_company_profile ON campaigns(company_profile_id);
CREATE INDEX idx_history_campaign_time ON campaign_history(campaign_id, timestamp DESC);
CREATE INDEX idx_assets_campaign ON campaign_assets(campaign_id);

-- 6. Auto-update updated_at trigger
CREATE TRIGGER update_campaigns_updated_at
  BEFORE UPDATE ON public.campaigns
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
