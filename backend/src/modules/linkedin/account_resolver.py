"""Tenant-scoped LinkedIn Account Resolver for Engagement Automation.

Resolves a brand's default LinkedIn account deterministically:
company_profile_id
→ company_profiles.default_linkedin_account_id
→ linkedin_accounts.id
→ verify linkedin_accounts.user_id == company_profiles.user_id
→ verify status == 'connected'
→ resolve linkedin_accounts.unipile_account_id

Engagement automation must NEVER use settings.unipile_account_id as runtime account selection.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.config.supabase import get_supabase_client

logger = logging.getLogger(__name__)


class BrandAccountResolutionError(Exception):
    """Raised when brand LinkedIn account resolution fails or is disallowed."""

    pass


async def resolve_brand_linkedin_account(
    company_profile_id: str | UUID | dict[str, Any],
    user_id: str | UUID | None = None,
    client: Any = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Resolve and verify the connected LinkedIn account for a brand.

    Args:
        company_profile_id: Brand UUID or brand row dict.
        user_id: Optional user UUID. If provided, enforces that the brand belongs to this user.
        client: Optional Supabase client instance (for testing/dependency injection).

    Returns:
        (account_row, None) on success, or (None, failure_reason) on failure/unlinked.
    """
    if client is None:
        client = get_supabase_client()

    if isinstance(company_profile_id, dict):
        brand = company_profile_id
        raw_owner = brand.get("user_id") or user_id
        if not raw_owner and brand.get("id"):
            try:
                b_res = (
                    client.table("company_profiles")
                    .select("user_id")
                    .eq("id", str(brand["id"]))
                    .limit(1)
                    .execute()
                )
                if b_res.data:
                    raw_owner = b_res.data[0].get("user_id")
            except Exception:
                pass
        brand_owner_id = str(raw_owner) if raw_owner else None
        default_acc_id = brand.get("default_linkedin_account_id")
    else:
        try:
            query = (
                client.table("company_profiles")
                .select("id, user_id, default_linkedin_account_id")
                .eq("id", str(company_profile_id))
            )
            if user_id is not None:
                query = query.eq("user_id", str(user_id))

            res = query.limit(1).execute()
            brands = res.data or []
        except Exception as e:
            logger.warning("Error fetching company_profiles for %s: %s", company_profile_id, e)
            return None, f"Database error querying brand profile: {e}"

        if not brands:
            return None, "Brand profile not found or not owned by the specified user."

        brand = brands[0]
        raw_owner = brand.get("user_id")
        brand_owner_id = str(raw_owner) if raw_owner else None
        default_acc_id = brand.get("default_linkedin_account_id")

    if not default_acc_id:
        return None, "Brand has no default LinkedIn account configured."

    try:
        acc_res = (
            client.table("linkedin_accounts")
            .select("*")
            .eq("id", str(default_acc_id))
            .limit(1)
            .execute()
        )
        accounts = acc_res.data or []
    except Exception as e:
        logger.warning("Error fetching linkedin_accounts for %s: %s", default_acc_id, e)
        return None, f"Database error querying LinkedIn account: {e}"

    if not accounts:
        return None, "Default LinkedIn account not found."

    account = accounts[0]
    acc_owner_id = str(account.get("user_id")) if account.get("user_id") else None
    if brand_owner_id and acc_owner_id != brand_owner_id:
        raise BrandAccountResolutionError(
            f"LinkedIn account user_id {acc_owner_id} does not match brand owner {brand_owner_id}."
        )

    if account.get("status") != "connected":
        return None, f"LinkedIn account {default_acc_id} is disconnected (status: {account.get('status')})."

    unipile_account_id = account.get("unipile_account_id")
    if not unipile_account_id:
        return None, "LinkedIn account record is missing Unipile account ID."

    return account, None
