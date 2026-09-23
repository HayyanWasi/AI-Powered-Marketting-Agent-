-- 011_add_plan_version_rpc.up.sql

CREATE OR REPLACE FUNCTION add_plan_version(
    p_plan_id UUID,
    p_version INT,
    p_document JSONB,
    p_parent_version INT,
    p_change_summary TEXT,
    p_sections_changed TEXT[],
    p_status TEXT,
    p_language TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_version_row JSONB;
BEGIN
    -- Check if version already exists
    IF EXISTS (SELECT 1 FROM campaign_plan_versions WHERE plan_id = p_plan_id AND version = p_version) THEN
        RAISE EXCEPTION 'duplicate_version: Version % already exists for plan %', p_version, p_plan_id;
    END IF;

    -- Update the plan pointer first
    UPDATE campaign_plans
    SET 
        current_version = p_version,
        status = p_status::campaign_plan_status,
        language = p_language,
        updated_at = NOW()
    WHERE id = p_plan_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'plan_not_found: Plan % does not exist', p_plan_id;
    END IF;

    -- Insert the new version
    INSERT INTO campaign_plan_versions (
        plan_id, version, document, parent_version, change_summary, sections_changed
    ) VALUES (
        p_plan_id, p_version, p_document, p_parent_version, p_change_summary, p_sections_changed
    )
    RETURNING row_to_json(campaign_plan_versions.*) INTO v_version_row;

    RETURN v_version_row;
END;
$$;

