"""Auto-Pilot Worker — Daily execution loop with safety limits, business hours, and randomized delays."""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import UTC, datetime
from typing import Any

from src.gateways.unipile_gateway import UnipileGateway
from src.modules.linkedin.models import AutoPilotConfig, PostStatus, SequenceStatus
from src.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class AutoPilotWorker:
    """Autonomous execution worker for daily post publishing and outbound sequence steps."""

    def __init__(
        self,
        unipile: UnipileGateway | None = None,
        posts_repo: BaseRepository | None = None,
        sequence_repo: BaseRepository | None = None,
    ) -> None:
        self.unipile = unipile or UnipileGateway()
        self.posts_repo = posts_repo or BaseRepository("linkedin_posts")
        self.sequence_repo = sequence_repo or BaseRepository("outreach_sequences")

    async def execute_daily_run(
        self,
        account_id: str,
        config: AutoPilotConfig = AutoPilotConfig(),
    ) -> dict[str, Any]:
        """Run daily execution cycle for a connected LinkedIn account.

        Args:
            account_id: Unipile account ID for LinkedIn profile.
            config: AutoPilotConfig safety limits and business hours rules.

        Returns:
            Dict summary of actions executed.
        """
        now = datetime.now(UTC)
        current_hour = now.hour

        # Check Business Hours Gate
        if not (config.business_hours_start <= current_hour < config.business_hours_end):
            logger.info(
                "Skipping AutoPilot run outside business hours (Current: %d:00, Allowed: %d:00-%d:00)",
                current_hour,
                config.business_hours_start,
                config.business_hours_end,
            )
            return {"status": "skipped", "reason": "outside_business_hours"}

        stats = {
            "posts_published": 0,
            "invites_sent": 0,
            "messages_sent": 0,
            "profiles_visited": 0,
            "invites_withdrawn": 0,
        }

        # ── 1. Publish Due Feed Posts ──────────────────────────────────────────────
        due_posts = await self._fetch_due_posts(now)
        for post in due_posts:
            post_id = post.get("id")
            content = post.get("full_content", "")
            unipile_id = await self.unipile.create_post(account_id, content)

            if unipile_id:
                await self._update_post_status(post_id, PostStatus.PUBLISHED, unipile_id)
                stats["posts_published"] += 1
                logger.info("Published post %s to LinkedIn via Unipile (ID: %s)", post_id, unipile_id)
            else:
                await self._update_post_status(post_id, PostStatus.FAILED, None)

            # Randomized Jitter Delay between posts
            jitter = random.uniform(config.delay_min_seconds, config.delay_max_seconds)
            await asyncio.sleep(jitter)

        # ── 2. Process Outbound Sequences ──────────────────────────────────────────
        active_sequences = await self._fetch_active_sequences(config.daily_invite_limit + config.daily_message_limit)

        for seq in active_sequences:
            seq_id = seq.get("id")
            prospect_id = seq.get("prospect_linkedin_id")
            current_step = seq.get("current_step", 0)
            status = seq.get("status", SequenceStatus.PENDING)

            if status == SequenceStatus.REPLIED:
                logger.info("Sequence %s paused: Prospect replied.", seq_id)
                continue

            # Step 0: Profile Visit
            if current_step == 0:
                success = await self.unipile.visit_profile(account_id, prospect_id)
                if success:
                    await self._update_sequence_step(seq_id, 1, SequenceStatus.VISITING)
                    stats["profiles_visited"] += 1

            # Step 1: Send Connection Request
            elif current_step == 1 and stats["invites_sent"] < config.daily_invite_limit:
                invite_msg = seq.get("step_invite_msg", "")
                invite_id = await self.unipile.send_connection_request(account_id, prospect_id, invite_msg)
                if invite_id:
                    await self._update_sequence_step(
                        seq_id, 2, SequenceStatus.CONNECTING, invite_id=invite_id
                    )
                    stats["invites_sent"] += 1

            # Step 2: Send Value Message (if connected)
            elif current_step == 2 and stats["messages_sent"] < config.daily_message_limit:
                # Check connection status
                is_connected = await self.unipile.check_relation(account_id, prospect_id)
                if is_connected:
                    val_msg = seq.get("step_value_msg", "")
                    msg_id = await self.unipile.send_message(account_id, prospect_id, val_msg)
                    if msg_id:
                        await self._update_sequence_step(seq_id, 3, SequenceStatus.CONNECTED)
                        stats["messages_sent"] += 1

            # Randomized Jitter Delay between actions
            jitter = random.uniform(config.delay_min_seconds, config.delay_max_seconds)
            await asyncio.sleep(jitter)

        return {"status": "completed", "stats": stats}

    async def _fetch_due_posts(self, now: datetime) -> list[dict[str, Any]]:
        """Fetch posts scheduled on or before current time."""
        try:
            res = (
                self.posts_repo.client.table(self.posts_repo.table_name)
                .select("*")
                .eq("status", PostStatus.SCHEDULED.value)
                .lte("scheduled_at", now.isoformat())
                .execute()
            )
            return res.data if res.data else []
        except Exception as e:
            logger.error("Failed to fetch due posts: %s", e)
            return []

    async def _update_post_status(
        self, post_id: str, status: PostStatus, unipile_post_id: str | None
    ) -> None:
        try:
            update_data = {
                "status": status.value,
                "unipile_post_id": unipile_post_id,
                "published_at": datetime.now(UTC).isoformat() if status == PostStatus.PUBLISHED else None,
            }
            self.posts_repo.client.table(self.posts_repo.table_name).update(update_data).eq("id", post_id).execute()
        except Exception as e:
            logger.error("Failed to update post status for %s: %s", post_id, e)

    async def _fetch_active_sequences(self, limit: int) -> list[dict[str, Any]]:
        try:
            res = (
                self.sequence_repo.client.table(self.sequence_repo.table_name)
                .select("*")
                .neq("status", SequenceStatus.COMPLETED.value)
                .neq("status", SequenceStatus.REPLIED.value)
                .limit(limit)
                .execute()
            )
            return res.data if res.data else []
        except Exception as e:
            logger.error("Failed to fetch active sequences: %s", e)
            return []

    async def _update_sequence_step(
        self,
        seq_id: str,
        step: int,
        status: SequenceStatus,
        invite_id: str | None = None,
    ) -> None:
        try:
            update_data: dict[str, Any] = {
                "current_step": step,
                "status": status.value,
            }
            if invite_id:
                update_data["invite_id"] = invite_id
            self.sequence_repo.client.table(self.sequence_repo.table_name).update(update_data).eq("id", seq_id).execute()
        except Exception as e:
            logger.error("Failed to update sequence step for %s: %s", seq_id, e)
