"""Focused contract checks for the active-flow RLS hardening migration."""

from pathlib import Path

MIGRATION = Path(__file__).resolve().parents[2] / "migrations" / "015_harden_active_flow_rls.up.sql"
SQL = MIGRATION.read_text(encoding="utf-8")


def test_active_tables_enable_rls_and_have_no_broad_policy() -> None:
    tables = (
        "company_profiles",
        "campaigns",
        "intake_checklists",
        "intake_messages",
        "campaign_plans",
        "campaign_plan_versions",
        "campaign_plan_messages",
        "linkedin_posts",
        "outreach_sequences",
    )

    for table in tables:
        assert f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;" in SQL

    normalized = " ".join(SQL.lower().split())
    for table in tables:
        assert f"on public.{table} for all" not in normalized
    assert "using (true)" not in normalized
    assert "to authenticated" in normalized


def test_mutable_resources_have_operation_specific_owner_checks() -> None:
    mutable_tables = (
        "company_profiles",
        "campaigns",
        "intake_checklists",
        "intake_messages",
        "campaign_plans",
        "campaign_plan_messages",
        "linkedin_posts",
        "outreach_sequences",
    )

    for table in mutable_tables:
        for operation in ("select", "insert", "update", "delete"):
            assert f"CREATE POLICY {table}_{operation}_own" in SQL

    # Plan versions are append-only: authenticated owners may read/create them,
    # and the absence of UPDATE/DELETE policies rejects those operations.
    assert "CREATE POLICY campaign_plan_versions_select_own" in SQL
    assert "CREATE POLICY campaign_plan_versions_insert_own" in SQL
    assert "campaign_plan_versions_update_own" not in SQL
    assert "campaign_plan_versions_delete_own" not in SQL


def test_foreign_brand_and_campaign_relationships_are_checked() -> None:
    assert "private.user_owns_company_profile(company_profile_id)" in SQL
    assert "profile.user_id = (SELECT auth.uid())" in SQL
    assert "campaign.organization_id = (SELECT auth.uid())" in SQL
    assert "private.user_owns_campaign(campaign_id)" in SQL
    assert "private.user_owns_plan(plan_id)" in SQL


def test_temporary_intake_requires_owner_and_rejects_existing_foreign_campaign() -> None:
    assert "owner_id = (SELECT auth.uid())" in SQL
    assert "private.intake_campaign_is_allowed(campaign_id)" in SQL
    assert "NOT EXISTS (" in SQL
    assert "OR private.user_owns_campaign(p_campaign_id)" in SQL


def test_ownership_helpers_are_restricted_security_definer_functions() -> None:
    assert SQL.count("SECURITY DEFINER") == 4
    assert SQL.count("SET search_path = ''") == 4
    assert "REVOKE ALL ON FUNCTION private.user_owns_campaign(UUID) FROM PUBLIC;" in SQL
    assert "GRANT USAGE ON SCHEMA private TO authenticated, service_role;" in SQL
