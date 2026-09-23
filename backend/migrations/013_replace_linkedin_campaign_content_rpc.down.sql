REVOKE EXECUTE ON FUNCTION public.replace_linkedin_campaign_content(
    UUID, UUID, JSONB, JSONB
) FROM service_role;

DROP FUNCTION IF EXISTS public.replace_linkedin_campaign_content(
    UUID, UUID, JSONB, JSONB
);
    