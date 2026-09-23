-- Audience enrichment and exact LinkedIn execution metadata.

ALTER TABLE public.intake_checklists
    ADD COLUMN IF NOT EXISTS audience_profile JSONB,
    ADD COLUMN IF NOT EXISTS audience_profile_version TEXT;

ALTER TABLE public.linkedin_posts
    ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'UTC',
    ADD COLUMN IF NOT EXISTS schedule_reason TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS schedule_source TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS schedule_confidence TEXT NOT NULL DEFAULT 'medium'
        CHECK (schedule_confidence IN ('low', 'medium', 'high')),
    ADD COLUMN IF NOT EXISTS linkedin_account_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_linkedin_account_scheduled_at
    ON public.linkedin_posts (linkedin_account_id, scheduled_at)
    WHERE linkedin_account_id IS NOT NULL
      AND status IN ('scheduled', 'published');

CREATE OR REPLACE FUNCTION public.replace_linkedin_campaign_content(
    p_campaign_id UUID,
    p_user_id UUID,
    p_posts JSONB,
    p_sequence JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_posts JSONB;
    v_sequence JSONB;
BEGIN
    IF jsonb_typeof(p_posts) <> 'array' OR jsonb_array_length(p_posts) = 0 THEN
        RAISE EXCEPTION 'invalid_posts: replacement posts must be a non-empty JSON array';
    END IF;
    IF jsonb_typeof(p_sequence) <> 'object' THEN
        RAISE EXCEPTION 'invalid_sequence: outreach sequence must be a JSON object';
    END IF;
    PERFORM 1 FROM public.campaigns
    WHERE id = p_campaign_id AND organization_id = p_user_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'campaign_not_found_or_access_denied: %', p_campaign_id;
    END IF;

    DELETE FROM public.linkedin_posts WHERE campaign_id = p_campaign_id;
    DELETE FROM public.outreach_sequences WHERE campaign_id = p_campaign_id;

    INSERT INTO public.outreach_sequences (
        campaign_id, step_invite_msg, step_value_msg, step_followup_msg
    ) VALUES (
        p_campaign_id, p_sequence->>'step_invite_msg',
        p_sequence->>'step_value_msg', p_sequence->>'step_followup_msg'
    ) RETURNING to_jsonb(outreach_sequences.*) INTO v_sequence;

    WITH inserted AS (
        INSERT INTO public.linkedin_posts (
            campaign_id, slot_id, scheduled_at, timezone, schedule_reason,
            schedule_source, schedule_confidence, linkedin_account_id,
            hook, body, cta_text, full_content, evidence_ids, status,
            unipile_post_id, published_at
        )
        SELECT p_campaign_id, post->>'slot_id', (post->>'scheduled_at')::TIMESTAMPTZ,
            COALESCE(post->>'timezone', 'UTC'), COALESCE(post->>'schedule_reason', ''),
            COALESCE(post->>'schedule_source', ''), COALESCE(post->>'schedule_confidence', 'medium'),
            NULLIF(post->>'linkedin_account_id', ''), post->>'hook', post->>'body',
            post->>'cta_text', post->>'full_content',
            COALESCE(ARRAY(SELECT jsonb_array_elements_text(COALESCE(post->'evidence_ids', '[]'::JSONB))), ARRAY[]::TEXT[]),
            COALESCE(post->>'status', 'draft'), NULLIF(post->>'unipile_post_id', ''),
            NULLIF(post->>'published_at', '')::TIMESTAMPTZ
        FROM jsonb_array_elements(p_posts) AS post
        RETURNING *
    ) SELECT jsonb_agg(to_jsonb(inserted) ORDER BY inserted.created_at, inserted.id)
      INTO v_posts FROM inserted;

    IF jsonb_array_length(COALESCE(v_posts, '[]'::JSONB)) <> jsonb_array_length(p_posts) THEN
        RAISE EXCEPTION 'incomplete_replacement: not all LinkedIn posts were inserted';
    END IF;
    RETURN jsonb_build_object('posts', v_posts, 'sequence', v_sequence);
END;
$$;

REVOKE ALL ON FUNCTION public.replace_linkedin_campaign_content(UUID, UUID, JSONB, JSONB) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.replace_linkedin_campaign_content(UUID, UUID, JSONB, JSONB) TO service_role;
