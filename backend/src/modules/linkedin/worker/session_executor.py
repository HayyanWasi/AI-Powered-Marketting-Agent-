"""Session Executor — Runs a single burst of bounded activity safely.

Executes actions up to the limits defined in a SessionWindow, respecting
the circuit breaker, rate limiter, and atomic action ledger. Never refunds
burned quota on errors to maintain natural variance.
"""

from __future__ import annotations

import logging

from src.gateways.unipile_gateway import get_unipile_gateway
from src.modules.linkedin.models import SessionResult, SessionWindow
from src.modules.linkedin.worker.action_ledger import ActionLedger
from src.modules.linkedin.worker.circuit_breaker import CircuitBreaker
from src.modules.linkedin.worker.rate_limiter import RateLimiter
from src.modules.linkedin.worker.review_queue import ReviewQueue
from src.modules.linkedin.worker.target_resolver import TargetResolver

logger = logging.getLogger(__name__)


class SessionExecutor:
    """Executes a single session burst."""

    def __init__(
        self,
        account_id: str,
        timezone: str,
        circuit_breaker: CircuitBreaker | None = None,
        rate_limiter: RateLimiter | None = None,
        action_ledger: ActionLedger | None = None,
        target_resolver: TargetResolver | None = None,
        review_queue: ReviewQueue | None = None,
    ) -> None:
        self.account_id = account_id
        self.timezone = timezone
        self.circuit_breaker = circuit_breaker or CircuitBreaker(account_id)
        self.rate_limiter = rate_limiter or RateLimiter()
        self.action_ledger = action_ledger or ActionLedger()
        self.target_resolver = target_resolver or TargetResolver()
        self.review_queue = review_queue or ReviewQueue()
        self.unipile = get_unipile_gateway(self.circuit_breaker)

    async def execute_session(
        self, session: SessionWindow, daily_invite_limit: int, daily_engage_limit: int
    ) -> SessionResult:
        """Run a single session burst.

        Args:
            session: The bounded session parameters.
            daily_invite_limit: The maximum invites allowed for the day.
            daily_engage_limit: The maximum engagements allowed for the day.

        Returns:
            SessionResult detailing the outcome.
        """
        result = SessionResult()

        if not self.circuit_breaker.can_proceed():
            result.status = "aborted"
            result.reason = "circuit_breaker_open"
            logger.warning("Session aborted for %s: Circuit Breaker OPEN", self.account_id)
            return result

        logger.info(
            "Starting session for %s. Max actions: %d", self.account_id, session.max_actions
        )

        # 1. Publish approved comments
        pending_comments = self.review_queue.get_approved_for_publishing(limit=session.max_actions)
        for comment in pending_comments:
            if result.actions_attempted >= session.max_actions:
                break

            if not self.circuit_breaker.can_proceed():
                break

            # Attempt to acquire engagement quota
            if not await self.action_ledger.try_acquire(
                self.account_id, "comment", daily_engage_limit, self.timezone
            ):
                logger.info("Daily comment limit reached for %s", self.account_id)
                break

            result.actions_attempted += 1

            # Execute via gateway
            logger.info("Publishing comment %s to post %s", comment.id, comment.target_post_id)
            unipile_id = await self.unipile.comment_on_post(
                self.account_id, comment.target_post_id, comment.generated_text
            )

            if unipile_id:
                self.review_queue.mark_published(comment.id, unipile_id)
                result.actions_succeeded += 1
            else:
                result.actions_failed += 1
                # Notice: we DO NOT refund the quota on failure.

            await self.rate_limiter.delay_between_actions()

        # 2. Add likes if we have quota and time left in session
        if result.actions_attempted < session.max_actions and self.circuit_breaker.can_proceed():
            remaining_actions = session.max_actions - result.actions_attempted
            await self._process_likes(remaining_actions, daily_engage_limit, result)

        return result

    async def _process_likes(self, max_likes: int, daily_limit: int, result: SessionResult) -> None:
        """Find and like posts."""
        personas = await self.target_resolver.load_personas(self.account_id)
        if not personas:
            return

        targets = await self.target_resolver.get_engagement_targets(
            self.account_id, personas, count=max_likes
        )

        for target in targets:
            if not self.circuit_breaker.can_proceed():
                break

            if not await self.action_ledger.try_acquire(
                self.account_id, "like", daily_limit, self.timezone
            ):
                break

            result.actions_attempted += 1

            # Mimic reading before liking
            await self.rate_limiter.micro_delay()

            success = await self.unipile.like_post(self.account_id, target.post_id)
            if success:
                result.actions_succeeded += 1
                await self.target_resolver.record_engagement(
                    self.account_id, target.post_id, "like"
                )
            else:
                result.actions_failed += 1

            await self.rate_limiter.delay_between_actions()
