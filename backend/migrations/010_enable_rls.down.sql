-- Revert Row Level Security

-- 1. Drop policies
DROP POLICY IF EXISTS "Users can access their own company profiles" ON public.company_profiles;
DROP POLICY IF EXISTS "Users can access their own campaigns" ON public.campaigns;
DROP POLICY IF EXISTS "Users can access their own intake checklists" ON public.intake_checklists;
DROP POLICY IF EXISTS "Users can access their own intake messages" ON public.intake_messages;
DROP POLICY IF EXISTS "Users can access their own campaign plans" ON public.campaign_plans;
DROP POLICY IF EXISTS "Users can access their own campaign plan versions" ON public.campaign_plan_versions;
DROP POLICY IF EXISTS "Users can access their own campaign plan messages" ON public.campaign_plan_messages;
DROP POLICY IF EXISTS "Users can access their own linkedin posts" ON public.linkedin_posts;
DROP POLICY IF EXISTS "Users can access their own outreach sequences" ON public.outreach_sequences;
DROP POLICY IF EXISTS "Users can access their own campaign assets" ON public.campaign_assets;
DROP POLICY IF EXISTS "Users can access their own campaign history" ON public.campaign_history;
DROP POLICY IF EXISTS "Authenticated users can access guest profiles" ON public.guest_profiles;
DROP POLICY IF EXISTS "Authenticated users can access execution history" ON public.execution_history;

-- 2. Disable RLS
ALTER TABLE public.company_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaigns DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.intake_checklists DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.intake_messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_plans DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_plan_versions DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_plan_messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.linkedin_posts DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.outreach_sequences DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_assets DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.guest_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.execution_history DISABLE ROW LEVEL SECURITY;
