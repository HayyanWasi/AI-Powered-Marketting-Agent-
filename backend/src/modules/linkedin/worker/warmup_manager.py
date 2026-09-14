"""Warm-up Manager.

Manages the account lifecycle phases (baseline -> ramp-up -> operating)
and gradually scales up API limits to avoid triggering anti-automation flags.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from src.config.supabase import get_supabase_client
from src.modules.linkedin.models import WarmupPhase, WarmupState

logger = logging.getLogger(__name__)


class WarmupManager:
    """Manages the lifecycle of a LinkedIn account's API limits."""

    def __init__(self, account_id: str) -> None:
        self._account_id = account_id

    def get_state(self) -> WarmupState:
        """Fetch the current warm-up state from the database."""
        try:
            client = get_supabase_client()
            res = (
                client.table("linkedin_warmup_state")
                .select("*")
                .eq("account_id", self._account_id)
                .limit(1)
                .execute()
            )
            if res.data:
                row = res.data[0]
                row["phase"] = WarmupPhase(row["phase"])
                # Handle dates if necessary based on Pydantic config
                return WarmupState(**row)

            # If no state exists, create a new one in RAMP_UP phase by default
            new_state = WarmupState(account_id=self._account_id)
            self._save_state(new_state)
            return new_state

        except Exception as e:
            logger.error("Failed to load warmup state for %s: %s", self._account_id, e)
            # Return a safe, conservative default in case of DB failure
            return WarmupState(
                account_id=self._account_id,
                current_daily_invite_limit=5,
                current_daily_engage_limit=5,
            )

    def _save_state(self, state: WarmupState) -> None:
        """Persist state to database."""
        try:
            client = get_supabase_client()
            data = {
                "id": str(state.id),
                "account_id": state.account_id,
                "activation_date": state.activation_date.isoformat(),
                "days_active": state.days_active,
                "current_daily_invite_limit": state.current_daily_invite_limit,
                "current_daily_engage_limit": state.current_daily_engage_limit,
                "phase": state.phase.value,
                "last_limit_increase_date": (
                    state.last_limit_increase_date.isoformat()
                    if state.last_limit_increase_date
                    else None
                ),
                "updated_at": datetime.now(UTC).isoformat(),
            }
            client.table("linkedin_warmup_state").upsert(data, on_conflict="account_id").execute()
        except Exception as e:
            logger.error("Failed to save warmup state for %s: %s", self._account_id, e)

    def evaluate_daily_limits(
        self, target_invite_limit: int, target_engage_limit: int
    ) -> WarmupState:
        """Evaluate and potentially increase limits based on days active.

        Call this once per day before generating the schedule.
        """
        state = self.get_state()

        # Simple daily active increment
        today = datetime.now(UTC).date()
        if today > state.activation_date:
            days_diff = (today - state.activation_date).days
            if days_diff > state.days_active:
                state.days_active = days_diff

        # Phase transitions
        if state.phase == WarmupPhase.BASELINE:
            # Baseline is manual activity only. We don't increase limits here.
            # Usually users manually switch to RAMP_UP in the UI.
            self._save_state(state)
            return state

        if state.phase == WarmupPhase.OPERATING:
            # If operating, limits should match the target config, unless downgraded
            state.current_daily_invite_limit = target_invite_limit
            state.current_daily_engage_limit = target_engage_limit
            self._save_state(state)
            return state

        # RAMP_UP logic
        # Increase limits by 2-5 per week, up to target limits
        last_increase = state.last_limit_increase_date or state.activation_date
        if (today - last_increase).days >= 7:
            # It's been a week, we can increase limits
            new_invite = min(target_invite_limit, state.current_daily_invite_limit + 3)
            new_engage = min(target_engage_limit, state.current_daily_engage_limit + 5)

            state.current_daily_invite_limit = new_invite
            state.current_daily_engage_limit = new_engage
            state.last_limit_increase_date = today

            logger.info(
                "Warmup limits increased for %s. Invites: %d, Engagements: %d",
                self._account_id,
                new_invite,
                new_engage,
            )

            # Did we reach operating limits?
            if new_invite >= target_invite_limit and new_engage >= target_engage_limit:
                state.phase = WarmupPhase.OPERATING
                logger.info("Account %s has reached OPERATING phase.", self._account_id)

        self._save_state(state)
        return state
