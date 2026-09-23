-- Persist a generated campaign video and its scheduler draft atomically.

ALTER TABLE public.linkedin_posts
    ADD COLUMN IF NOT EXISTS campaign_asset_id UUID
        REFERENCES public.campaign_assets(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS media_url TEXT,
    ADD COLUMN IF NOT EXISTS media_type TEXT
        CHECK (media_type IS NULL OR media_type IN ('video'));

CREATE INDEX IF NOT EXISTS idx_linkedin_posts_campaign_asset
    ON public.linkedin_posts (campaign_asset_id)
    WHERE campaign_asset_id IS NOT NULL;

CREATE OR REPLACE FUNCTION public.create_campaign_video_draft(
    p_campaign_id UUID,
    p_user_id UUID,
    p_content JSONB,
    p_storage_path TEXT,
    p_media_url TEXT,
    p_scheduled_at TIMESTAMPTZ,
    p_timezone TEXT,
    p_caption TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_asset public.campaign_assets;
    v_post public.linkedin_posts;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.campaigns
        WHERE id = p_campaign_id AND organization_id = p_user_id
    ) THEN
        RAISE EXCEPTION 'campaign_not_found_or_access_denied: %', p_campaign_id;
    END IF;

    INSERT INTO public.campaign_assets (
        campaign_id, asset_type, content, storage_path, source, created_by
    ) VALUES (
        p_campaign_id, 'video', p_content, p_storage_path, 'ai', p_user_id
    ) RETURNING * INTO v_asset;

    INSERT INTO public.linkedin_posts (
        campaign_id, slot_id, scheduled_at, timezone, schedule_reason,
        schedule_source, schedule_confidence, campaign_asset_id, media_url,
        media_type, hook, body, cta_text, full_content, status
    ) VALUES (
        p_campaign_id, 'video-' || v_asset.id::TEXT, p_scheduled_at, p_timezone,
        'Draft created automatically from Video Studio', 'video-studio', 'medium',
        v_asset.id, p_media_url, 'video', '', p_caption, '', p_caption, 'draft'
    ) RETURNING * INTO v_post;

    RETURN jsonb_build_object(
        'asset', to_jsonb(v_asset),
        'post', to_jsonb(v_post)
    );
END;
$$;

REVOKE ALL ON FUNCTION public.create_campaign_video_draft(
    UUID, UUID, JSONB, TEXT, TEXT, TIMESTAMPTZ, TEXT, TEXT
) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.create_campaign_video_draft(
    UUID, UUID, JSONB, TEXT, TEXT, TIMESTAMPTZ, TEXT, TEXT
) TO service_role;

-- Generated copy replacement must preserve independently-created media drafts.
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
        RAISE EXCEPTION 'invalid_sequence: outreach sequence must be an object';
    END IF;
    PERFORM 1 FROM public.campaigns
    WHERE id = p_campaign_id AND organization_id = p_user_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'campaign_not_found_or_access_denied: %', p_campaign_id;
    END IF;

    DELETE FROM public.linkedin_posts
    WHERE campaign_id = p_campaign_id AND campaign_asset_id IS NULL;
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

REVOKE ALL ON FUNCTION public.replace_linkedin_campaign_content(UUID, UUID, JSONB, JSONB)
FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.replace_linkedin_campaign_content(UUID, UUID, JSONB, JSONB)
TO service_role;
