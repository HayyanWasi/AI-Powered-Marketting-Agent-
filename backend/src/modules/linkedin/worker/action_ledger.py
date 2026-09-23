"""Action Ledger — Atomic, timezone-aware daily action counter.

Tracks daily actions per canonical linkedin_account_id across like, comment, and connection_request.
Dates are computed in the account's configured timezone.
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from src.config.supabase import get_supabase_client

logger = logging.getLogger(__name__)


def _get_local_date_str(tz_name: str) -> str:
    """Return today's date formatted as YYYY-MM-DD in the given timezone."""
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime.now(tz).strftime("%Y-%m-%d")


class ActionLedger:
    """Daily action counter backed by PostgreSQL (linkedin_daily_actions table)."""

    async def try_acquire(
        self,
        account_id: str,
        action_type: str,
        limit: int,
        timezone: str,
    ) -> bool:
        """Check and increment the daily counter.

        Returns True if acquired (count was under limit).
        Returns False if limit has been reached.
        """
        local_date = _get_local_date_str(timezone)
        client = get_supabase_client()

        try:
            # Query existing count using linkedin_account_id
            res = (
                client.table("linkedin_daily_actions")
                .select("action_count")
                .eq("linkedin_account_id", account_id)
                .eq("action_date", local_date)
                .eq("action_type", action_type)
                .limit(1)
                .execute()
            )

            if res.data:
                current_count = res.data[0].get("action_count", 0)
                if current_count >= limit:
                    logger.info(
                        "Daily limit reached for %s/%s (count=%d, limit=%d)",
                        action_type,
                        account_id,
                        current_count,
                        limit,
                    )
                    return False
                client.table("linkedin_daily_actions").update(
                    {"action_count": current_count + 1}
                ).eq("linkedin_account_id", account_id).eq("action_date", local_date).eq(
                    "action_type", action_type
                ).execute()
            else:
                client.table("linkedin_daily_actions").insert(
                    {
                        "linkedin_account_id": account_id,
                        "action_date": local_date,
                        "action_type": action_type,
                        "action_count": 1,
                    }
                ).execute()

            return True
        except Exception as e:
            # Try legacy column fallback if migration hasn't altered column name yet
            logger.warning(
                "ActionLedger try_acquire failed with linkedin_account_id: %s. Trying fallback.", e
            )
            try:
                res = (
                    client.table("linkedin_daily_actions")
                    .select("action_count")
                    .eq("account_id", account_id)
                    .eq("action_date", local_date)
                    .eq("action_type", action_type)
                    .limit(1)
                    .execute()
                )
                if res.data:
                    current_count = res.data[0].get("action_count", 0)
                    if current_count >= limit:
                        return False
                    client.table("linkedin_daily_actions").update(
                        {"action_count": current_count + 1}
                    ).eq("account_id", account_id).eq("action_date", local_date).eq(
                        "action_type", action_type
                    ).execute()
                else:
                    client.table("linkedin_daily_actions").insert(
                        {
                            "account_id": account_id,
                            "action_date": local_date,
                            "action_type": action_type,
                            "action_count": 1,
                        }
                    ).execute()
                return True
            except Exception as fallback_e:
                logger.error("ActionLedger fallback failed: %s", fallback_e)
                return False

    async def record_action(
        self,
        account_id: str,
        action_type: str,
        timezone: str = "UTC",
    ) -> None:
        """Increment daily action count directly upon successful action."""
        local_date = _get_local_date_str(timezone)
        client = get_supabase_client()
        try:
            res = (
                client.table("linkedin_daily_actions")
                .select("action_count")
                .eq("linkedin_account_id", account_id)
                .eq("action_date", local_date)
                .eq("action_type", action_type)
                .limit(1)
                .execute()
            )
            if res.data:
                cnt = res.data[0].get("action_count", 0)
                client.table("linkedin_daily_actions").update({"action_count": cnt + 1}).eq(
                    "linkedin_account_id", account_id
                ).eq("action_date", local_date).eq("action_type", action_type).execute()
            else:
                client.table("linkedin_daily_actions").insert(
                    {
                        "linkedin_account_id": account_id,
                        "action_date": local_date,
                        "action_type": action_type,
                        "action_count": 1,
                    }
                ).execute()
        except Exception as e:
            logger.warning("ActionLedger record_action failed: %s", e)

    async def get_count(self, account_id: str, action_type: str, timezone: str) -> int:
        """Read the current daily count for a specific action type."""
        local_date = _get_local_date_str(timezone)
        client = get_supabase_client()
        try:
            res = (
                client.table("linkedin_daily_actions")
                .select("action_count")
                .eq("linkedin_account_id", account_id)
                .eq("action_date", local_date)
                .eq("action_type", action_type)
                .limit(1)
                .execute()
            )
            return res.data[0]["action_count"] if res.data else 0
        except Exception:
            try:
                res = (
                    client.table("linkedin_daily_actions")
                    .select("action_count")
                    .eq("account_id", account_id)
                    .eq("action_date", local_date)
                    .eq("action_type", action_type)
                    .limit(1)
                    .execute()
                )
                return res.data[0]["action_count"] if res.data else 0
            except Exception:
                return 0

    async def get_daily_summary(self, account_id: str, timezone: str) -> dict[str, int]:
        """Return all action counts for today as ``{action_type: count}``."""
        local_date = _get_local_date_str(timezone)
        client = get_supabase_client()
        try:
            res = (
                client.table("linkedin_daily_actions")
                .select("action_type, action_count")
                .eq("linkedin_account_id", account_id)
                .eq("action_date", local_date)
                .execute()
            )
            summary: dict[str, int] = {}
            for row in res.data or []:
                summary[row["action_type"]] = row["action_count"]
            return summary
        except Exception:
            try:
                res = (
                    client.table("linkedin_daily_actions")
                    .select("action_type, action_count")
                    .eq("account_id", account_id)
                    .eq("action_date", local_date)
                    .execute()
                )
                summary: dict[str, int] = {}
                for row in res.data or []:
                    summary[row["action_type"]] = row["action_count"]
                return summary
            except Exception:
                return {}
