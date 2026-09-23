"""Session Executor — Runs a single burst of bounded activity safely.

Executes actions up to the limits defined in a SessionWindow, respecting
the circuit breaker, rate limiter, and atomic action ledger.

Safety Invariants:
- Comments are GENERATION ONLY into linkedin_review_queue (never dispatched directly).
- Pre-dispatch durable claims in linkedin_engagement_log before any external write.
- Permanent action identity prevents any automated retry on failed or needs_review.
- Relation check before sending connection requests.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx

from src.config.supabase import get_supabase_client
from src.gateways.unipile_gateway import UnipileGateway, get_unipile_gateway
from src.modules.linkedin.generators.comment_generator import CommentGenerator
from src.modules.linkedin.models import (
    EngagementActionType,
    EngagementLogStatus,
    SessionResult,
    SessionWindow,
    TargetPost,
)
from src.modules.linkedin.worker.action_ledger import ActionLedger
from src.modules.linkedin.worker.circuit_breaker import CircuitBreaker
from src.modules.linkedin.worker.rate_limiter import RateLimiter
from src.modules.linkedin.worker.review_queue import ReviewQueue
from src.modules.linkedin.worker.target_resolver import TargetResolver

logger = logging.getLogger(__name__)


class SessionExecutor:
    """Executes a single tenant-scoped session burst."""

    def __init__(
        self,
        account_id: str | UUID | None = None,
        timezone: str = "UTC",
        connection_note_template: str = "",
        circuit_breaker: CircuitBreaker | None = None,
        rate_limiter: RateLimiter | None = None,
        action_ledger: ActionLedger | None = None,
        target_resolver: TargetResolver | None = None,
        review_queue: ReviewQueue | None = None,
        comment_generator: CommentGenerator | None = None,
        unipile: UnipileGateway | None = None,
        gateway: Any = None,
        client: Any = None,
        *,
        linkedin_account_id: str | UUID | None = None,
        unipile_account_id: str | None = None,
        company_profile_id: str | UUID | None = None,
        user_id: str | UUID | None = None,
        brand_id: str | UUID | None = None,
        **kwargs: Any,
    ) -> None:
        raw_acc_id = account_id or linkedin_account_id or ""
        self.account_id = str(raw_acc_id)
        self.unipile_account_id = str(unipile_account_id or raw_acc_id)
        cid = company_profile_id or brand_id
        self.company_profile_id = str(cid) if cid else ""
        self.user_id = str(user_id) if user_id else ""
        self.timezone = timezone
        self.connection_note_template = connection_note_template
        self.circuit_breaker = circuit_breaker or CircuitBreaker(self.account_id)
        self.rate_limiter = rate_limiter or RateLimiter()
        self.action_ledger = action_ledger or ActionLedger()
        self.target_resolver = target_resolver or TargetResolver()
        self.review_queue = review_queue or ReviewQueue()
        self.comment_generator = comment_generator or CommentGenerator()
        self.unipile = gateway or unipile or get_unipile_gateway(self.circuit_breaker)
        self.client = client

    async def _safe_micro_delay(self) -> None:
        delay_fn = getattr(self.rate_limiter, "micro_delay", None)
        if callable(delay_fn):
            res = delay_fn()
            if asyncio.iscoroutine(res):
                await res

    async def _safe_action_delay(self) -> None:
        delay_fn = getattr(self.rate_limiter, "delay_between_actions", None)
        if callable(delay_fn):
            res = delay_fn()
            if asyncio.iscoroutine(res):
                await res

    async def execute_session(
        self,
        session: SessionWindow,
        daily_invite_limit: int,
        daily_like_limit: int,
        daily_comment_limit: int,
        allowed_action_types: tuple[str, ...] | None = None,
    ) -> SessionResult:
        """Run a single session burst."""
        result = SessionResult()

        if not self.circuit_breaker.can_proceed():
            result.status = "aborted"
            result.reason = "circuit_breaker_open"
            logger.warning("Session aborted for %s: Circuit Breaker OPEN", self.account_id)
            return result

        logger.info(
            "Starting engagement session for account %s (brand %s). Max actions: %d",
            self.account_id,
            self.company_profile_id,
            session.max_actions,
        )

        active_action_types = allowed_action_types or session.action_types

        # 1. AI Comments: GENERATION ONLY into Review Queue (Never sent directly)
        if (
            "comment" in active_action_types
            and result.actions_attempted < session.max_actions
            and self.circuit_breaker.can_proceed()
        ):
            remaining_actions = session.max_actions - result.actions_attempted
            await self._process_ai_comments(
                remaining_actions, daily_comment_limit, result
            )

        # 2. Auto Likes: Fully automatic with durable pre-dispatch claims
        if (
            "like" in active_action_types
            and result.actions_attempted < session.max_actions
            and self.circuit_breaker.can_proceed()
        ):
            remaining_actions = session.max_actions - result.actions_attempted
            await self._process_likes(remaining_actions, daily_like_limit, result)

        # 3. Auto Connection Requests: Automatic with relation check and pre-dispatch claims
        if (
            "invite" in active_action_types
            and result.actions_attempted < session.max_actions
            and self.circuit_breaker.can_proceed()
        ):
            remaining_actions = session.max_actions - result.actions_attempted
            await self._process_invites(remaining_actions, daily_invite_limit, result)

        return result

    async def _process_ai_comments(
        self, max_comments: int, daily_limit: int, result: SessionResult
    ) -> None:
        """Generate comments from target posts and save to Review Queue as pending_review.

        CRITICAL SAFETY: NEVER sends comments automatically to LinkedIn.
        """
        if max_comments <= 0 or daily_limit <= 0:
            return
        personas = await self.target_resolver.load_personas(
            company_profile_id=self.company_profile_id
        )
        if not personas:
            logger.info("No active personas found for brand %s; skipping comment generation.", self.company_profile_id)
            return

        targets = await self.target_resolver.get_engagement_targets(
            self.account_id,
            personas,
            count=max_comments,
            unipile_account_id=self.unipile_account_id,
        )

        for target in targets:
            if not self.circuit_breaker.can_proceed():
                break

            # 1. Generate comment via AI
            try:
                gen_res = self.comment_generator.generate_comment(target)
                if asyncio.iscoroutine(gen_res):
                    gen_res = await gen_res
                comment_text = (
                    gen_res
                    if isinstance(gen_res, str)
                    else getattr(gen_res, "generated_text", str(gen_res))
                )
            except Exception as exc:
                logger.error("AI comment generation failed for post %s: %s", target.post_id, exc)
                result.details["comment_generation_failures"] = (
                    result.details.get("comment_generation_failures", 0) + 1
                )
                continue

            # 2. Acquire ledger slot
            if not await self.action_ledger.try_acquire(
                self.account_id, "comment", daily_limit, self.timezone
            ):
                break

            result.actions_attempted += 1
            ok = await self._queue_comment(
                target, comment_text, current_count=result.actions_succeeded, max_count=max_comments
            )
            if ok:
                result.actions_succeeded += 1
                logger.info("Queued AI comment for post %s", target.post_id)
            else:
                result.actions_failed += 1

            await self._safe_micro_delay()

    async def _execute_like(
        self,
        target: TargetPost,
        current_count: int = 0,
        max_count: int = 10,
    ) -> bool:
        """Execute a single like action with durable claim and permanent idempotency."""
        if current_count >= max_count:
            return False

        client = self.client or get_supabase_client()

        # 1. Dedupe check against engagement log
        try:
            existing_log = (
                client.table("linkedin_engagement_log")
                .select("id, status")
                .eq("linkedin_account_id", self.account_id)
                .eq("target_post_id", target.post_id)
                .eq("action_type", "like")
                .limit(1)
                .execute()
            )
            if existing_log.data:
                return False
        except Exception:
            pass

        # 2. Create durable pre-dispatch claim
        claim_id = await self._create_claim(
            action_type=EngagementActionType.LIKE,
            target_post_id=target.post_id,
        )
        if not claim_id:
            return False

        await self._safe_micro_delay()

        # 3. Call Unipile
        try:
            success = await self.unipile.like_post(self.unipile_account_id, target.post_id)
            if success:
                await self._update_claim_status(claim_id, EngagementLogStatus.SUCCEEDED)
                with contextlib.suppress(Exception):
                    client.table("linkedin_engaged_posts").upsert({
                        "linkedin_account_id": self.account_id,
                        "post_id": target.post_id,
                        "action_type": "like",
                        "engaged_at": datetime.now(UTC).isoformat(),
                    }).execute()
                return True
            else:
                await self._update_claim_status(
                    claim_id, EngagementLogStatus.FAILED, error_message="Disallowed or falsy result from provider"
                )
                return False
        except (TimeoutError, httpx.TimeoutException) as exc:
            logger.warning("Timeout while liking post %s; marking needs_review: %s", target.post_id, exc)
            await self._update_claim_status(
                claim_id, EngagementLogStatus.NEEDS_REVIEW, error_message=f"Timeout: {exc}"
            )
            return False
        except Exception as e:
            logger.error("Error liking post %s: %s", target.post_id, e)
            await self._update_claim_status(
                claim_id, EngagementLogStatus.FAILED, error_message=str(e)
            )
            return False

    async def _queue_comment(
        self,
        target: TargetPost,
        comment_text: str,
        current_count: int = 0,
        max_count: int = 5,
    ) -> bool:
        """Insert generated comment into Review Queue as pending_review without external write."""
        if current_count >= max_count:
            return False

        client = self.client or get_supabase_client()

        # Dedupe check
        try:
            existing = (
                client.table("linkedin_review_queue")
                .select("id")
                .eq("linkedin_account_id", self.account_id)
                .eq("target_post_id", target.post_id)
                .limit(1)
                .execute()
            )
            if existing.data:
                return False
        except Exception:
            pass

        queue_row = {
            "user_id": self.user_id,
            "company_profile_id": self.company_profile_id,
            "linkedin_account_id": self.account_id,
            "target_post_id": target.post_id,
            "target_post_snippet": (target.content or "")[:200],
            "target_author_name": getattr(target, "author_name", ""),
            "persona_label": getattr(target, "persona_label", ""),
            "generated_text": comment_text,
            "status": "pending_review",
            "created_at": datetime.now(UTC).isoformat(),
        }

        try:
            res = client.table("linkedin_review_queue").insert(queue_row).execute()
            return bool(res.data)
        except Exception as e:
            logger.error("Failed to insert comment into review queue: %s", e)
            return False

    async def _generate_and_queue_comment(
        self,
        target: TargetPost,
        current_count: int = 0,
        max_count: int = 5,
    ) -> bool:
        """Generate AI comment and insert into Review Queue as pending_review without external write."""
        if current_count >= max_count:
            return False

        try:
            gen_res = self.comment_generator.generate_comment(target)
            if asyncio.iscoroutine(gen_res):
                gen_res = await gen_res
            comment_text = (
                gen_res
                if isinstance(gen_res, str)
                else getattr(gen_res, "generated_text", str(gen_res))
            )
        except Exception as exc:
            logger.error("AI comment generation failed for post %s: %s", target.post_id, exc)
            return False

        return await self._queue_comment(target, comment_text, current_count, max_count)

    async def _execute_connection(
        self,
        target: Any,
        current_count: int = 0,
        max_count: int = 10,
    ) -> bool:
        """Execute a connection request with relation checks and durable pre-dispatch claims."""
        if current_count >= max_count:
            return False

        profile_id = getattr(target, "profile_id", str(target))
        client = self.client or get_supabase_client()

        # 1. Relation check: skip if already connected or invitation pending
        try:
            rel = await self.unipile.check_relation(self.unipile_account_id, profile_id)
            if isinstance(rel, dict):
                st = (rel.get("status") or "").upper()
                if st in ("CONNECTED", "PENDING"):
                    return False
            elif rel is True:
                return False
        except Exception as e:
            logger.warning("Error checking relation for %s: %s; skipping.", profile_id, e)
            return False

        # 2. Dedupe check against engagement log
        try:
            existing_log = (
                client.table("linkedin_engagement_log")
                .select("id, status")
                .eq("linkedin_account_id", self.account_id)
                .eq("target_profile_id", profile_id)
                .eq("action_type", "connection_request")
                .limit(1)
                .execute()
            )
            if existing_log.data:
                return False
        except Exception:
            pass

        # 3. Create durable claim
        claim_id = await self._create_claim(
            action_type=EngagementActionType.CONNECTION_REQUEST,
            target_profile_id=profile_id,
        )
        if not claim_id:
            return False

        # 4. Render note
        note = ""
        display_name = getattr(target, "display_name", "")
        if self.connection_note_template and self.connection_note_template.strip():
            first_name = display_name.split()[0] if display_name else "there"
            note = self.connection_note_template.replace("{first_name}", first_name).strip()

        # 5. Call Unipile
        try:
            invitation_id = await self.unipile.send_connection_request(
                self.unipile_account_id, profile_id, note or None
            )
            if invitation_id:
                provider_id = (
                    invitation_id.get("id")
                    if isinstance(invitation_id, dict)
                    else str(invitation_id)
                )
                await self._update_claim_status(
                    claim_id, EngagementLogStatus.SUCCEEDED, provider_result_id=str(provider_id)
                )
                return True
            else:
                await self._update_claim_status(
                    claim_id, EngagementLogStatus.FAILED, error_message="Unipile returned falsy invite ID"
                )
                return False
        except (TimeoutError, httpx.TimeoutException) as exc:
            logger.warning("Timeout while inviting profile %s; marking needs_review: %s", profile_id, exc)
            await self._update_claim_status(
                claim_id, EngagementLogStatus.NEEDS_REVIEW, error_message=f"Timeout: {exc}"
            )
            return False
        except Exception as e:
            logger.error("Error inviting profile %s: %s", profile_id, e)
            await self._update_claim_status(
                claim_id, EngagementLogStatus.FAILED, error_message=str(e)
            )
            return False

    async def _process_likes(
        self, max_likes: int, daily_limit: int, result: SessionResult
    ) -> None:
        """Find targets and like posts with pre-dispatch claim and permanent idempotency."""
        if max_likes <= 0 or daily_limit <= 0:
            return
        personas = await self.target_resolver.load_personas(
            company_profile_id=self.company_profile_id
        )
        if not personas:
            return

        targets = await self.target_resolver.get_engagement_targets(
            self.account_id,
            personas,
            count=max_likes,
            unipile_account_id=self.unipile_account_id,
        )

        for target in targets:
            if not self.circuit_breaker.can_proceed():
                break

            if not await self.action_ledger.try_acquire(
                self.account_id, "like", daily_limit, self.timezone
            ):
                break

            result.actions_attempted += 1
            ok = await self._execute_like(
                target, current_count=result.actions_succeeded, max_count=max_likes
            )
            if ok:
                result.actions_succeeded += 1
                await self.target_resolver.record_engagement(
                    self.account_id, target.post_id, "like"
                )
            else:
                result.actions_failed += 1

            await self._safe_action_delay()

    async def _process_invites(
        self, max_invites: int, daily_limit: int, result: SessionResult
    ) -> None:
        """Send invitation requests with relation checks and durable pre-dispatch claims."""
        if max_invites <= 0 or daily_limit <= 0:
            return
        personas = await self.target_resolver.load_personas(
            company_profile_id=self.company_profile_id
        )
        if not personas:
            return

        targets = await self.target_resolver.get_invite_targets(
            self.account_id,
            personas,
            count=max_invites,
            unipile_account_id=self.unipile_account_id,
        )

        for target in targets:
            if not self.circuit_breaker.can_proceed():
                break

            if not await self.action_ledger.try_acquire(
                self.account_id, "invite", daily_limit, self.timezone
            ):
                break

            result.actions_attempted += 1
            ok = await self._execute_connection(
                target, current_count=result.actions_succeeded, max_count=max_invites
            )
            if ok:
                result.actions_succeeded += 1
                profile_id = getattr(target, "profile_id", str(target))
                await self.target_resolver.record_engagement(
                    self.account_id, profile_id, "invite"
                )
            else:
                result.actions_failed += 1

            await self._safe_action_delay()

    async def _create_claim(
        self,
        action_type: EngagementActionType,
        target_post_id: str | None = None,
        target_profile_id: str | None = None,
        review_queue_id: str | None = None,
        comment_text: str | None = None,
    ) -> str | None:
        """Atomically insert a durable pre-dispatch claim into linkedin_engagement_log."""
        try:
            client = self.client or get_supabase_client()
            claim_data = {
                "user_id": self.user_id,
                "company_profile_id": self.company_profile_id,
                "linkedin_account_id": self.account_id,
                "action_type": action_type.value,
                "target_post_id": target_post_id,
                "target_profile_id": target_profile_id,
                "review_queue_id": review_queue_id,
                "comment_text": comment_text,
                "status": EngagementLogStatus.CLAIMED.value,
                "created_at": datetime.now(UTC).isoformat(),
            }
            res = client.table("linkedin_engagement_log").insert(claim_data).execute()
            if res.data:
                return res.data[0]["id"]
            return None
        except Exception as e:
            logger.warning("Durable claim insertion conflicted or failed (%s): %s", action_type, e)
            return None

    async def _update_claim_status(
        self,
        claim_id: str,
        status: EngagementLogStatus,
        provider_result_id: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update claim result in engagement log."""
        try:
            client = self.client or get_supabase_client()
            update_data: dict[str, str] = {
                "status": status.value,
                "completed_at": datetime.now(UTC).isoformat(),
            }
            if provider_result_id:
                update_data["provider_result_id"] = provider_result_id
            if error_message:
                update_data["error_message"] = error_message
            client.table("linkedin_engagement_log").update(update_data).eq("id", claim_id).execute()
        except Exception as e:
            logger.error("Failed to update engagement log %s: %s", claim_id, e)

    @staticmethod
    def _is_uuid(val: str) -> bool:
        try:
            UUID(str(val))
            return True
        except ValueError:
            return False


# Backward compatibility and descriptive alias
EngagementSessionExecutor = SessionExecutor

