"""Circuit Breaker — Halts all LinkedIn automation on 429/202 responses.

State is persisted to PostgreSQL so the breaker survives process restarts.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from src.config.supabase import get_supabase_client
from src.modules.linkedin.models import CircuitState

logger = logging.getLogger(__name__)

# Cooldown durations by trigger reason
_COOLDOWN_MAP: dict[int, tuple[str, float]] = {
    429: ("rate_limited", 4.0),
    202: ("checkpoint_challenge", 24.0),
}
_CONSECUTIVE_FAILURE_THRESHOLD = 3
_CONSECUTIVE_FAILURE_COOLDOWN = 1.0


class CircuitBreaker:
    """LinkedIn API circuit breaker with PostgreSQL-persisted state.

    State machine:
        CLOSED  → normal operation, all calls allowed
        OPEN    → tripped, all calls blocked until cooldown expires
        HALF_OPEN → cooldown expired, allow exactly ONE test call
    """

    def __init__(self, account_id: str) -> None:
        self._account_id = account_id
        self._state = CircuitState.CLOSED
        self._tripped_at: datetime | None = None
        self._trip_reason: str | None = None
        self._cooldown_hours: float = 4.0
        self._consecutive_failures: int = 0
        self._load_state()

    # ── Public API ────────────────────────────────────────────────────────

    def can_proceed(self) -> bool:
        """Check if API calls are currently allowed."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            if self._cooldown_elapsed():
                self._transition(CircuitState.HALF_OPEN)
                logger.info(
                    "Circuit breaker transitioning to HALF_OPEN for account %s "
                    "(cooldown elapsed after %s)",
                    self._account_id,
                    self._trip_reason,
                )
                return True
            return False

        # HALF_OPEN: allow exactly one test call
        return True

    def record_success(self) -> None:
        """Record a successful API call."""
        self._consecutive_failures = 0
        if self._state == CircuitState.HALF_OPEN:
            self._transition(CircuitState.CLOSED)
            logger.info(
                "Circuit breaker CLOSED for account %s (test call succeeded)",
                self._account_id,
            )

    def record_failure(self, status_code: int) -> None:
        """Record a failed API call and potentially trip the breaker."""
        if status_code in _COOLDOWN_MAP:
            reason, cooldown = _COOLDOWN_MAP[status_code]
            self._trip(reason, cooldown)
            return

        self._consecutive_failures += 1
        if self._consecutive_failures >= _CONSECUTIVE_FAILURE_THRESHOLD:
            self._trip("consecutive_errors", _CONSECUTIVE_FAILURE_COOLDOWN)

    def trip(self, reason: str, cooldown_hours: float) -> None:
        """Manually trip the circuit breaker (public wrapper)."""
        self._trip(reason, cooldown_hours)

    def get_status(self) -> dict[str, object]:
        """Return current breaker state for monitoring."""
        return {
            "account_id": self._account_id,
            "state": self._state.value,
            "tripped_at": self._tripped_at.isoformat() if self._tripped_at else None,
            "trip_reason": self._trip_reason,
            "cooldown_hours": self._cooldown_hours,
            "consecutive_failures": self._consecutive_failures,
        }

    # ── Internal ──────────────────────────────────────────────────────────

    def _trip(self, reason: str, cooldown_hours: float) -> None:
        self._state = CircuitState.OPEN
        self._tripped_at = datetime.now(UTC)
        self._trip_reason = reason
        self._cooldown_hours = cooldown_hours
        self._consecutive_failures = 0
        self._persist_state()
        logger.warning(
            "CIRCUIT BREAKER TRIPPED for account %s — reason: %s, "
            "cooldown: %.1fh. ALL automation halted.",
            self._account_id,
            reason,
            cooldown_hours,
        )

    def _cooldown_elapsed(self) -> bool:
        if self._tripped_at is None:
            return True
        elapsed = (datetime.now(UTC) - self._tripped_at).total_seconds()
        return elapsed >= self._cooldown_hours * 3600

    def _transition(self, new_state: CircuitState) -> None:
        self._state = new_state
        if new_state == CircuitState.CLOSED:
            self._tripped_at = None
            self._trip_reason = None
        self._persist_state()

    def _persist_state(self) -> None:
        """Persist current state to ``linkedin_circuit_breaker`` table."""
        try:
            client = get_supabase_client()
            data = {
                "account_id": self._account_id,
                "state": self._state.value,
                "tripped_at": self._tripped_at.isoformat() if self._tripped_at else None,
                "trip_reason": self._trip_reason,
                "cooldown_hours": self._cooldown_hours,
                "updated_at": datetime.now(UTC).isoformat(),
            }
            client.table("linkedin_circuit_breaker").upsert(
                data, on_conflict="account_id"
            ).execute()
        except Exception as e:
            logger.error("Failed to persist circuit breaker state: %s", e)

    def _load_state(self) -> None:
        """Load persisted state from DB on startup."""
        try:
            client = get_supabase_client()
            res = (
                client.table("linkedin_circuit_breaker")
                .select("*")
                .eq("account_id", self._account_id)
                .limit(1)
                .execute()
            )
            if res.data:
                row = res.data[0]
                self._state = CircuitState(row["state"])
                self._trip_reason = row.get("trip_reason")
                self._cooldown_hours = row.get("cooldown_hours", 4.0)
                tripped = row.get("tripped_at")
                if tripped:
                    self._tripped_at = datetime.fromisoformat(tripped)
                logger.info(
                    "Circuit breaker loaded from DB for account %s: state=%s",
                    self._account_id,
                    self._state.value,
                )
        except Exception as e:
            logger.warning("Could not load circuit breaker state: %s", e)
