-- Enable Row Level Security and add policies for all tables
-- Ensures data privacy across organizations/users

-- 1. Enable RLS
ALTER TABLE public.company_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.intake_checklists ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.intake_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_plan_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_plan_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.linkedin_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outreach_sequences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.guest_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.execution_history ENABLE ROW LEVEL SECURITY;

-- 2. company_profiles
CREATE POLICY "Users can access their own company profiles"
ON public.company_profiles FOR ALL
USING (user_id = auth.uid());

-- 3. campaigns
CREATE POLICY "Users can access their own campaigns"
ON public.campaigns FOR ALL
USING (organization_id = auth.uid());

-- 4. intake_checklists
CREATE POLICY "Users can access their own intake checklists"
ON public.intake_checklists FOR ALL
USING (EXISTS (
  SELECT 1 FROM public.campaigns c 
  WHERE c.id = intake_checklists.campaign_id AND c.organization_id = auth.uid()
));

-- 5. intake_messages
CREATE POLICY "Users can access their own intake messages"
ON public.intake_messages FOR ALL
USING (EXISTS (
  SELECT 1 FROM public.campaigns c 
  WHERE c.id = intake_messages.campaign_id AND c.organization_id = auth.uid()
));

-- 6. campaign_plans
CREATE POLICY "Users can access their own campaign plans"
ON public.campaign_plans FOR ALL
USING (EXISTS (
  SELECT 1 FROM public.campaigns c 
  WHERE c.id = campaign_plans.campaign_id AND c.organization_id = auth.uid()
));

-- 7. campaign_plan_versions
CREATE POLICY "Users can access their own campaign plan versions"
ON public.campaign_plan_versions FOR ALL
USING (EXISTS (
  SELECT 1 FROM public.campaign_plans cp 
  JOIN public.campaigns c ON c.id = cp.campaign_id 
  WHERE cp.id = campaign_plan_versions.plan_id AND c.organization_id = auth.uid()
));

-- 8. campaign_plan_messages
CREATE POLICY "Users can access their own campaign plan messages"
ON public.campaign_plan_messages FOR ALL
USING (EXISTS (
  SELECT 1 FROM public.campaign_plans cp 
  JOIN public.campaigns c ON c.id = cp.campaign_id 
  WHERE cp.id = campaign_plan_messages.plan_id AND c.organization_id = auth.uid()
));

-- 9. linkedin_posts
CREATE POLICY "Users can access their own linkedin posts"
ON public.linkedin_posts FOR ALL
USING (EXISTS (
  SELECT 1 FROM public.campaigns c 
  WHERE c.id = linkedin_posts.campaign_id AND c.organization_id = auth.uid()
));

-- 10. outreach_sequences
CREATE POLICY "Users can access their own outreach sequences"
ON public.outreach_sequences FOR ALL
USING (EXISTS (
  SELECT 1 FROM public.campaigns c 
  WHERE c.id = outreach_sequences.campaign_id AND c.organization_id = auth.uid()
));

-- 11. campaign_assets
CREATE POLICY "Users can access their own campaign assets"
ON public.campaign_assets FOR ALL
USING (EXISTS (
  SELECT 1 FROM public.campaigns c 
  WHERE c.id = campaign_assets.campaign_id AND c.organization_id = auth.uid()
));

-- 12. campaign_history
CREATE POLICY "Users can access their own campaign history"
ON public.campaign_history FOR ALL
USING (EXISTS (
  SELECT 1 FROM public.campaigns c 
  WHERE c.id = campaign_history.campaign_id AND c.organization_id = auth.uid()
));

-- 13. guest_profiles (Global, but only accessible to authenticated users)
CREATE POLICY "Authenticated users can access guest profiles"
ON public.guest_profiles FOR ALL
USING (auth.uid() IS NOT NULL);

-- 14. execution_history (Global audit log, only accessible to authenticated users)
CREATE POLICY "Authenticated users can access execution history"
ON public.execution_history FOR ALL
USING (auth.uid() IS NOT NULL);

