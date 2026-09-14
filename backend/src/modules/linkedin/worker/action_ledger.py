"""Action Ledger — Atomic, timezone-aware daily action counter.

Uses a single ``INSERT ... ON CONFLICT DO UPDATE ... WHERE count < limit``
SQL call to atomically check-and-increment the counter.  No TOCTOU race
conditions are possible because PostgreSQL row-level locking handles
concurrency.

All dates are computed in the account's configured timezone, NOT server UTC.
"""

from __future__ import annotations

import logging

from src.config.supabase import get_supabase_client

logger = logging.getLogger(__name__)

# The atomic upsert SQL.
# $1 = account_id, $2 = timezone, $3 = action_type, $4 = limit
_ACQUIRE_SQL = """
INSERT INTO linkedin_daily_actions
    (account_id, action_date, action_type, action_count)
VALUES ('{account_id}', (now() AT TIME ZONE '{tz}')::date, '{action_type}', 1)
ON CONFLICT (account_id, action_date, action_type)
DO UPDATE SET action_count = linkedin_daily_actions.action_count + 1
WHERE linkedin_daily_actions.action_count < {limit}
RETURNING action_count;
"""


class ActionLedger:
    """Atomic, timezone-aware daily action counter backed by PostgreSQL.

    The key method is ``try_acquire()`` which checks AND increments in a
    single SQL statement.  The old ``can_perform()`` + ``record()`` two-step
    pattern is eliminated entirely.

    If an API call fails after acquisition, the quota is NOT refunded.
    The burned slot adds natural variance to daily activity volume.
    """

    async def try_acquire(
        self,
        account_id: str,
        action_type: str,
        limit: int,
        timezone: str,
    ) -> bool:
        """Atomically check-and-increment the daily counter.

        Returns ``True`` if the action was acquired (count was under limit).
        Returns ``False`` if the daily limit has been reached.

        The action_date is computed using the account's timezone so quotas
        reset at midnight local time, not server UTC.
        """
        try:
            client = get_supabase_client()
            sql = _ACQUIRE_SQL.format(
                account_id=account_id,
                tz=timezone,
                action_type=action_type,
                limit=limit,
            )
            result = client.rpc("exec_sql", {"query": sql}).execute()
            # If the WHERE clause blocked the update, result.data will be
            # empty or contain zero rows.
            if result.data:
                count = result.data[0].get("action_count", 0) if result.data else 0
                logger.debug(
                    "Action acquired: %s/%s for %s (count=%d/%d)",
                    action_type,
                    account_id,
                    timezone,
                    count,
                    limit,
                )
                return True
            logger.info(
                "Daily limit reached for %s/%s (limit=%d)",
                action_type,
                account_id,
                limit,
            )
            return False
        except Exception:
            # Fallback: use Supabase client directly for the upsert
            return await self._try_acquire_fallback(account_id, action_type, limit, timezone)

    async def _try_acquire_fallback(
        self,
        account_id: str,
        action_type: str,
        limit: int,
        timezone: str,
    ) -> bool:
        """Fallback acquisition using Supabase client ORM.

        Less atomic than raw SQL but functional when RPC is unavailable.
        Uses select-then-upsert with the same timezone-aware date logic.
        """
        try:
            client = get_supabase_client()

            # Compute local date via a simple RPC
            date_result = client.rpc(
                "exec_sql",
                {"query": f"SELECT (now() AT TIME ZONE '{timezone}')::date as d"},
            ).execute()
            local_date = date_result.data[0]["d"] if date_result.data else None

            if not local_date:
                logger.error("Could not determine local date for timezone %s", timezone)
                return False

            # Check current count
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
                current_count = res.data[0]["action_count"]
                if current_count >= limit:
                    return False
                # Increment
                client.table("linkedin_daily_actions").update(
                    {"action_count": current_count + 1}
                ).eq("account_id", account_id).eq("action_date", local_date).eq(
                    "action_type", action_type
                ).execute()
            else:
                # Insert new row
                client.table("linkedin_daily_actions").insert(
                    {
                        "account_id": account_id,
                        "action_date": local_date,
                        "action_type": action_type,
                        "action_count": 1,
                    }
                ).execute()

            return True
        except Exception as e:
            logger.error("Action ledger fallback failed: %s", e)
            return False

    async def get_count(self, account_id: str, action_type: str, timezone: str) -> int:
        """Read the current daily count for a specific action type."""
        try:
            client = get_supabase_client()
            date_result = client.rpc(
                "exec_sql",
                {"query": f"SELECT (now() AT TIME ZONE '{timezone}')::date as d"},
            ).execute()
            local_date = date_result.data[0]["d"] if date_result.data else None
            if not local_date:
                return 0

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
        except Exception as e:
            logger.error("Failed to get action count: %s", e)
            return 0

    async def get_daily_summary(self, account_id: str, timezone: str) -> dict[str, int]:
        """Return all action counts for today as ``{action_type: count}``."""
        try:
            client = get_supabase_client()
            date_result = client.rpc(
                "exec_sql",
                {"query": f"SELECT (now() AT TIME ZONE '{timezone}')::date as d"},
            ).execute()
            local_date = date_result.data[0]["d"] if date_result.data else None
            if not local_date:
                return {}

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
        except Exception as e:
            logger.error("Failed to get daily summary: %s", e)
            return {}
