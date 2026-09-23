-- Harden authenticated access to the user-owned production campaign flow.
-- This is a forward-only replacement for the broad FOR ALL policies in 010.

CREATE SCHEMA IF NOT EXISTS private;

-- Security-definer ownership helpers deliberately live outside the exposed
-- public schema. They read ownership metadata without being affected by the
-- caller's RLS visibility, which prevents a foreign campaign from looking like
-- a nonexistent temporary intake session.
CREATE OR REPLACE FUNCTION private.user_owns_company_profile(p_profile_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.company_profiles AS profile
    WHERE profile.id = p_profile_id
      AND profile.user_id = (SELECT auth.uid())
  );
$$;

CREATE OR REPLACE FUNCTION private.user_owns_campaign(p_campaign_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.campaigns AS campaign
    WHERE campaign.id = p_campaign_id
      AND campaign.organization_id = (SELECT auth.uid())
  );
$$;

CREATE OR REPLACE FUNCTION private.intake_campaign_is_allowed(p_campaign_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT
    NOT EXISTS (
      SELECT 1 FROM public.campaigns AS campaign
      WHERE campaign.id = p_campaign_id
    )
    OR private.user_owns_campaign(p_campaign_id);
$$;

CREATE OR REPLACE FUNCTION private.user_owns_plan(p_plan_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.campaign_plans AS plan
    JOIN public.campaigns AS campaign ON campaign.id = plan.campaign_id
    WHERE plan.id = p_plan_id
      AND campaign.organization_id = (SELECT auth.uid())
  );
$$;

REVOKE ALL ON FUNCTION private.user_owns_company_profile(UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION private.user_owns_campaign(UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION private.intake_campaign_is_allowed(UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION private.user_owns_plan(UUID) FROM PUBLIC;
GRANT USAGE ON SCHEMA private TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION private.user_owns_company_profile(UUID) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION private.user_owns_campaign(UUID) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION private.intake_campaign_is_allowed(UUID) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION private.user_owns_plan(UUID) TO authenticated, service_role;

ALTER TABLE public.company_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.intake_checklists ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.intake_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_plan_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_plan_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.linkedin_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outreach_sequences ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can access their own company profiles" ON public.company_profiles;
DROP POLICY IF EXISTS "Users can access their own campaigns" ON public.campaigns;
DROP POLICY IF EXISTS "Users can access their own intake checklists" ON public.intake_checklists;
DROP POLICY IF EXISTS "Users can access their own intake messages" ON public.intake_messages;
DROP POLICY IF EXISTS "Users can access their own campaign plans" ON public.campaign_plans;
DROP POLICY IF EXISTS "Users can access their own campaign plan versions" ON public.campaign_plan_versions;
DROP POLICY IF EXISTS "Users can access their own campaign plan messages" ON public.campaign_plan_messages;
DROP POLICY IF EXISTS "Users can access their own linkedin posts" ON public.linkedin_posts;
DROP POLICY IF EXISTS "Users can access their own outreach sequences" ON public.outreach_sequences;

CREATE POLICY company_profiles_select_own
ON public.company_profiles FOR SELECT TO authenticated
USING (user_id = (SELECT auth.uid()));
CREATE POLICY company_profiles_insert_own
ON public.company_profiles FOR INSERT TO authenticated
WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY company_profiles_update_own
ON public.company_profiles FOR UPDATE TO authenticated
USING (user_id = (SELECT auth.uid()))
WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY company_profiles_delete_own
ON public.company_profiles FOR DELETE TO authenticated
USING (user_id = (SELECT auth.uid()));

CREATE POLICY campaigns_select_own
ON public.campaigns FOR SELECT TO authenticated
USING (organization_id = (SELECT auth.uid()));
CREATE POLICY campaigns_insert_own
ON public.campaigns FOR INSERT TO authenticated
WITH CHECK (
  organization_id = (SELECT auth.uid())
  AND (
    company_profile_id IS NULL
    OR private.user_owns_company_profile(company_profile_id)
  )
);
CREATE POLICY campaigns_update_own
ON public.campaigns FOR UPDATE TO authenticated
USING (organization_id = (SELECT auth.uid()))
WITH CHECK (
  organization_id = (SELECT auth.uid())
  AND (
    company_profile_id IS NULL
    OR private.user_owns_company_profile(company_profile_id)
  )
);
CREATE POLICY campaigns_delete_own
ON public.campaigns FOR DELETE TO authenticated
USING (organization_id = (SELECT auth.uid()));

CREATE POLICY intake_checklists_select_own
ON public.intake_checklists FOR SELECT TO authenticated
USING (
  owner_id = (SELECT auth.uid())
  AND private.intake_campaign_is_allowed(campaign_id)
);
CREATE POLICY intake_checklists_insert_own
ON public.intake_checklists FOR INSERT TO authenticated
WITH CHECK (
  owner_id = (SELECT auth.uid())
  AND private.intake_campaign_is_allowed(campaign_id)
);
CREATE POLICY intake_checklists_update_own
ON public.intake_checklists FOR UPDATE TO authenticated
USING (
  owner_id = (SELECT auth.uid())
  AND private.intake_campaign_is_allowed(campaign_id)
)
WITH CHECK (
  owner_id = (SELECT auth.uid())
  AND private.intake_campaign_is_allowed(campaign_id)
);
CREATE POLICY intake_checklists_delete_own
ON public.intake_checklists FOR DELETE TO authenticated
USING (
  owner_id = (SELECT auth.uid())
  AND private.intake_campaign_is_allowed(campaign_id)
);

CREATE POLICY intake_messages_select_own
ON public.intake_messages FOR SELECT TO authenticated
USING (
  owner_id = (SELECT auth.uid())
  AND private.intake_campaign_is_allowed(campaign_id)
);
CREATE POLICY intake_messages_insert_own
ON public.intake_messages FOR INSERT TO authenticated
WITH CHECK (
  owner_id = (SELECT auth.uid())
  AND private.intake_campaign_is_allowed(campaign_id)
);
CREATE POLICY intake_messages_update_own
ON public.intake_messages FOR UPDATE TO authenticated
USING (
  owner_id = (SELECT auth.uid())
  AND private.intake_campaign_is_allowed(campaign_id)
)
WITH CHECK (
  owner_id = (SELECT auth.uid())
  AND private.intake_campaign_is_allowed(campaign_id)
);
CREATE POLICY intake_messages_delete_own
ON public.intake_messages FOR DELETE TO authenticated
USING (
  owner_id = (SELECT auth.uid())
  AND private.intake_campaign_is_allowed(campaign_id)
);

CREATE POLICY campaign_plans_select_own
ON public.campaign_plans FOR SELECT TO authenticated
USING (private.user_owns_campaign(campaign_id));
CREATE POLICY campaign_plans_insert_own
ON public.campaign_plans FOR INSERT TO authenticated
WITH CHECK (private.user_owns_campaign(campaign_id));
CREATE POLICY campaign_plans_update_own
ON public.campaign_plans FOR UPDATE TO authenticated
USING (private.user_owns_campaign(campaign_id))
WITH CHECK (private.user_owns_campaign(campaign_id));
CREATE POLICY campaign_plans_delete_own
ON public.campaign_plans FOR DELETE TO authenticated
USING (private.user_owns_campaign(campaign_id));

CREATE POLICY campaign_plan_versions_select_own
ON public.campaign_plan_versions FOR SELECT TO authenticated
USING (private.user_owns_plan(plan_id));
CREATE POLICY campaign_plan_versions_insert_own
ON public.campaign_plan_versions FOR INSERT TO authenticated
WITH CHECK (private.user_owns_plan(plan_id));

CREATE POLICY campaign_plan_messages_select_own
ON public.campaign_plan_messages FOR SELECT TO authenticated
USING (private.user_owns_plan(plan_id));
CREATE POLICY campaign_plan_messages_insert_own
ON public.campaign_plan_messages FOR INSERT TO authenticated
WITH CHECK (private.user_owns_plan(plan_id));
CREATE POLICY campaign_plan_messages_update_own
ON public.campaign_plan_messages FOR UPDATE TO authenticated
USING (private.user_owns_plan(plan_id))
WITH CHECK (private.user_owns_plan(plan_id));
CREATE POLICY campaign_plan_messages_delete_own
ON public.campaign_plan_messages FOR DELETE TO authenticated
USING (private.user_owns_plan(plan_id));

CREATE POLICY linkedin_posts_select_own
ON public.linkedin_posts FOR SELECT TO authenticated
USING (private.user_owns_campaign(campaign_id));
CREATE POLICY linkedin_posts_insert_own
ON public.linkedin_posts FOR INSERT TO authenticated
WITH CHECK (private.user_owns_campaign(campaign_id));
CREATE POLICY linkedin_posts_update_own
ON public.linkedin_posts FOR UPDATE TO authenticated
USING (private.user_owns_campaign(campaign_id))
WITH CHECK (private.user_owns_campaign(campaign_id));
CREATE POLICY linkedin_posts_delete_own
ON public.linkedin_posts FOR DELETE TO authenticated
USING (private.user_owns_campaign(campaign_id));

CREATE POLICY outreach_sequences_select_own
ON public.outreach_sequences FOR SELECT TO authenticated
USING (private.user_owns_campaign(campaign_id));
CREATE POLICY outreach_sequences_insert_own
ON public.outreach_sequences FOR INSERT TO authenticated
WITH CHECK (private.user_owns_campaign(campaign_id));
CREATE POLICY outreach_sequences_update_own
ON public.outreach_sequences FOR UPDATE TO authenticated
USING (private.user_owns_campaign(campaign_id))
WITH CHECK (private.user_owns_campaign(campaign_id));
CREATE POLICY outreach_sequences_delete_own
ON public.outreach_sequences FOR DELETE TO authenticated
USING (private.user_owns_campaign(campaign_id));
