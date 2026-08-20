-- Campaign Planning Tables
-- Run this in your Supabase Dashboard SQL Editor

-- 1. Plan status enum (capitalized to match Python enum)
DROP TYPE IF EXISTS campaign_plan_status;
CREATE TYPE campaign_plan_status AS ENUM (
  'Drafting', 'Draft', 'Refining', 'Approved', 'Superseded'
);

-- 2. Campaign plans — one live plan per campaign
CREATE TABLE IF NOT EXISTS public.campaign_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES public.campaigns(id) ON DELETE CASCADE,
  status campaign_plan_status NOT NULL DEFAULT 'Drafting',
  current_version INT NOT NULL DEFAULT 0,
  language TEXT NOT NULL DEFAULT 'en',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  approved_at TIMESTAMPTZ,
  approved_by UUID,
  created_by UUID NOT NULL,
  UNIQUE(campaign_id)
);

-- 3. Plan versions (append-only; every revision is retained)
CREATE TABLE IF NOT EXISTS public.campaign_plan_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id UUID NOT NULL REFERENCES public.campaign_plans(id) ON DELETE CASCADE,
  version INT NOT NULL,
  document JSONB NOT NULL,
  parent_version INT,
  change_summary TEXT,
  sections_changed TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(plan_id, version)
);

-- 4. Plan conversation turns (user critiques and agent replies)
CREATE TABLE IF NOT EXISTS public.campaign_plan_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id UUID NOT NULL REFERENCES public.campaign_plans(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'agent')),
  content TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'en',
  sections_targeted TEXT[] DEFAULT '{}',
  resulting_version INT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. Indexes
CREATE INDEX idx_plans_campaign ON campaign_plans(campaign_id);
CREATE INDEX idx_plans_status ON campaign_plans(status);
CREATE INDEX idx_plan_versions_plan ON campaign_plan_versions(plan_id, version DESC);
CREATE INDEX idx_plan_messages_plan ON campaign_plan_messages(plan_id, created_at);

-- 6. Auto-update updated_at trigger
CREATE TRIGGER update_campaign_plans_updated_at
  BEFORE UPDATE ON public.campaign_plans
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
