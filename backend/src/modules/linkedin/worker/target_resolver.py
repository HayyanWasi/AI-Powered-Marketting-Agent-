"""Target Resolver for two-step audience targeting pipeline.

Step 1: Search people by keywords to resolve profile IDs.
Step 2: Fetch recent posts from those profiles.

Includes deduplication logic to never re-engage the same post.
"""

import contextlib
import logging
import random
from datetime import UTC, datetime, timedelta

from src.config.supabase import get_supabase_client
from src.gateways.unipile_gateway import get_unipile_gateway
from src.modules.linkedin.models import ResolvedTarget, TargetPersona, TargetPost

logger = logging.getLogger(__name__)


class TargetResolver:
    """Resolves target personas into actionable posts for engagement."""

    async def load_personas(self, account_id: str) -> list[TargetPersona]:
        """Load active target personas from the database for the given account."""
        try:
            client = get_supabase_client()
            res = (
                client.table("linkedin_target_personas")
                .select("*")
                .eq("account_id", account_id)
                .eq("is_active", True)
                .execute()
            )
            personas = []
            for row in res.data or []:
                personas.append(TargetPersona(**row))
            return personas
        except Exception as e:
            logger.error("Failed to load personas for account %s: %s", account_id, e)
            return []

    async def resolve_personas(
        self, account_id: str, personas: list[TargetPersona]
    ) -> list[ResolvedTarget]:
        """Step 1: Search people and cache the profiles as resolved targets."""
        client = get_supabase_client()
        gateway = get_unipile_gateway()
        resolved_targets = []

        for persona in personas:
            try:
                # Check cache freshness (refresh weekly)
                res = (
                    client.table("linkedin_resolved_targets")
                    .select("resolved_at")
                    .eq("account_id", account_id)
                    .eq("persona_label", persona.label)
                    .order("resolved_at", desc=True)
                    .limit(1)
                    .execute()
                )

                needs_refresh = True
                if res.data:
                    last_resolved_str = res.data[0].get("resolved_at")
                    if last_resolved_str:
                        last_resolved = datetime.fromisoformat(
                            last_resolved_str.replace("Z", "+00:00")
                        )
                        if datetime.now(UTC) - last_resolved < timedelta(days=7):
                            needs_refresh = False

                if not needs_refresh:
                    # Load from cache
                    cached = (
                        client.table("linkedin_resolved_targets")
                        .select("*")
                        .eq("account_id", account_id)
                        .eq("persona_label", persona.label)
                        .execute()
                    )
                    for row in cached.data or []:
                        resolved_targets.append(ResolvedTarget(**row))
                    continue

                # Refresh needed: call Gateway
                logger.info(
                    "Refreshing targets for persona '%s' (account %s)", persona.label, account_id
                )
                profiles = await gateway.search_people(
                    account_id, persona.search_keywords, persona.max_profiles
                )

                for prof in profiles:
                    rt = ResolvedTarget(
                        account_id=account_id,
                        persona_label=persona.label,
                        profile_id=prof.get("provider_id") or prof.get("id", ""),
                        display_name=prof.get("name", ""),
                        headline=prof.get("headline", ""),
                    )

                    if not rt.profile_id:
                        continue

                    # Upsert into DB
                    client.table("linkedin_resolved_targets").upsert(
                        {
                            "id": str(rt.id),
                            "account_id": rt.account_id,
                            "persona_label": rt.persona_label,
                            "profile_id": rt.profile_id,
                            "display_name": rt.display_name,
                            "headline": rt.headline,
                            "resolved_at": rt.resolved_at.isoformat(),
                        },
                        on_conflict="account_id, persona_label, profile_id",
                    ).execute()

                    resolved_targets.append(rt)

            except Exception as e:
                logger.error("Failed to resolve persona '%s': %s", persona.label, e)

        return resolved_targets

    async def fetch_target_posts(
        self, account_id: str, resolved_targets: list[ResolvedTarget], limit_per_profile: int = 3
    ) -> list[TargetPost]:
        """Step 2: Fetch recent posts from resolved target profiles."""
        gateway = get_unipile_gateway()
        target_posts = []

        # Don't fetch for everyone every time, sample a few to avoid spamming the API
        sample_size = min(20, len(resolved_targets))
        sampled_targets = random.sample(resolved_targets, sample_size) if resolved_targets else []

        for rt in sampled_targets:
            try:
                posts_data = await gateway.get_user_posts(
                    account_id, rt.profile_id, limit_per_profile
                )

                seven_days_ago = datetime.now(UTC) - timedelta(days=7)

                for post_dict in posts_data:
                    created_at_str = post_dict.get("created_at")
                    text = post_dict.get("text", "")

                    # Filter posts already liked by the current user
                    if post_dict.get("user_reacted") == "LIKE":
                        continue

                    # Filter short posts
                    if len(text) < 50:
                        continue

                    posted_at = datetime.now(UTC)
                    if created_at_str:
                        with contextlib.suppress(ValueError):
                            posted_at = datetime.fromisoformat(
                                created_at_str.replace("Z", "+00:00")
                            )

                    # Filter stale posts
                    if posted_at < seven_days_ago:
                        continue

                    target_posts.append(
                        TargetPost(
                            post_id=post_dict.get("social_id") or post_dict.get("id", ""),
                            author_profile_id=rt.profile_id,
                            author_name=rt.display_name,
                            content=text,
                            posted_at=posted_at,
                            persona_label=rt.persona_label,
                        )
                    )
            except Exception as e:
                logger.error("Failed to fetch posts for profile %s: %s", rt.profile_id, e)

        return target_posts

    async def get_engagement_targets(
        self, account_id: str, personas: list[TargetPersona], count: int = 5
    ) -> list[TargetPost]:
        """High level method to get deduped engagement targets."""
        resolved = await self.resolve_personas(account_id, personas)
        posts = await self.fetch_target_posts(account_id, resolved)

        if not posts:
            return []

        # Deduplication
        try:
            client = get_supabase_client()
            res = (
                client.table("linkedin_engaged_posts")
                .select("post_id")
                .eq("account_id", account_id)
                .execute()
            )
            engaged_ids = {row["post_id"] for row in res.data or []}

            unengaged_posts = [p for p in posts if p.post_id not in engaged_ids and p.post_id]

            return random.sample(unengaged_posts, min(count, len(unengaged_posts)))
        except Exception as e:
            logger.error("Error during engagement deduplication: %s", e)
            return posts[:count]

    async def get_invite_targets(
        self, account_id: str, personas: list[TargetPersona], count: int = 5
    ) -> list[ResolvedTarget]:
        """Return resolved profiles that have not already received an invitation."""
        resolved = await self.resolve_personas(account_id, personas)
        if not resolved:
            return []

        try:
            client = get_supabase_client()
            res = (
                client.table("linkedin_engaged_posts")
                .select("post_id")
                .eq("account_id", account_id)
                .eq("action_type", "invite")
                .execute()
            )
            invited_profile_ids = {row["post_id"] for row in res.data or []}
            available = [
                target for target in resolved if target.profile_id not in invited_profile_ids
            ]
            return random.sample(available, min(count, len(available)))
        except Exception as e:
            logger.error("Error during invitation deduplication: %s", e)
            return resolved[:count]

    async def record_engagement(self, account_id: str, post_id: str, action_type: str) -> None:
        """Record an engagement to prevent future duplicates."""
        try:
            client = get_supabase_client()
            client.table("linkedin_engaged_posts").upsert(
                {
                    "account_id": account_id,
                    "post_id": post_id,
                    "action_type": action_type,
                    "engaged_at": datetime.now(UTC).isoformat(),
                },
                on_conflict="account_id, post_id, action_type",
            ).execute()
        except Exception as e:
            logger.error("Failed to record engagement %s on post %s: %s", action_type, post_id, e)
