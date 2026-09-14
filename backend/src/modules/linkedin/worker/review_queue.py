"""Review Queue — PostgreSQL-backed mandatory human approval gate.

All AI-generated comments enter this queue. They must be manually approved
before the scheduler will publish them. Stale drafts are automatically expired.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.config.supabase import get_supabase_client
from src.modules.linkedin.models import GeneratedComment, ReviewStatus

logger = logging.getLogger(__name__)


class ReviewQueue:
    """Manages the human-in-the-loop review gate for AI comments."""

    def add_comment(self, comment: GeneratedComment) -> UUID:
        """Add a newly generated comment to the queue for human review."""
        try:
            client = get_supabase_client()
            expires_at = datetime.now(UTC) + timedelta(hours=48)

            data = {
                "id": str(comment.id),
                "target_post_id": comment.target_post_id,
                "target_post_snippet": comment.target_post_snippet,
                "target_author_name": comment.target_author_name,
                "persona_label": comment.persona_label,
                "generated_text": comment.generated_text,
                "status": comment.status.value,
                "reject_reason": comment.reject_reason,
                "unipile_id": comment.unipile_id,
                "generated_at": comment.generated_at.isoformat(),
                "expires_at": expires_at.isoformat(),
            }

            client.table("linkedin_review_queue").insert(data).execute()
            logger.info(
                "Added comment %s to review queue for post %s", comment.id, comment.target_post_id
            )
            return comment.id
        except Exception as e:
            logger.error("Failed to add comment to review queue: %s", e)
            raise

    def get_pending(self, limit: int = 50) -> list[GeneratedComment]:
        """Fetch all comments currently awaiting human review."""
        try:
            client = get_supabase_client()
            res = (
                client.table("linkedin_review_queue")
                .select("*")
                .eq("status", ReviewStatus.PENDING_REVIEW.value)
                .order("generated_at", desc=False)
                .limit(limit)
                .execute()
            )
            comments = []
            for row in res.data or []:
                row["status"] = ReviewStatus(row["status"])
                # Convert string dates to datetime if needed by Pydantic
                comments.append(GeneratedComment(**row))
            return comments
        except Exception as e:
            logger.error("Failed to fetch pending comments: %s", e)
            return []

    def get_approved_for_publishing(self, limit: int = 10) -> list[GeneratedComment]:
        """Fetch comments that are approved and ready to be published."""
        try:
            client = get_supabase_client()
            res = (
                client.table("linkedin_review_queue")
                .select("*")
                .eq("status", ReviewStatus.APPROVED.value)
                .order("reviewed_at", desc=False)
                .limit(limit)
                .execute()
            )
            comments = []
            for row in res.data or []:
                row["status"] = ReviewStatus(row["status"])
                comments.append(GeneratedComment(**row))
            return comments
        except Exception as e:
            logger.error("Failed to fetch approved comments: %s", e)
            return []

    def approve(self, comment_id: UUID | str) -> bool:
        """Mark a comment as approved."""
        try:
            client = get_supabase_client()
            res = (
                client.table("linkedin_review_queue")
                .update(
                    {
                        "status": ReviewStatus.APPROVED.value,
                        "reviewed_at": datetime.now(UTC).isoformat(),
                    }
                )
                .eq("id", str(comment_id))
                .execute()
            )
            return len(res.data) > 0 if res.data else False
        except Exception as e:
            logger.error("Failed to approve comment %s: %s", comment_id, e)
            return False

    def reject(self, comment_id: UUID | str, reason: str = "") -> bool:
        """Mark a comment as rejected."""
        try:
            client = get_supabase_client()
            res = (
                client.table("linkedin_review_queue")
                .update(
                    {
                        "status": ReviewStatus.REJECTED.value,
                        "reject_reason": reason,
                        "reviewed_at": datetime.now(UTC).isoformat(),
                    }
                )
                .eq("id", str(comment_id))
                .execute()
            )
            return len(res.data) > 0 if res.data else False
        except Exception as e:
            logger.error("Failed to reject comment %s: %s", comment_id, e)
            return False

    def mark_published(self, comment_id: UUID | str, unipile_id: str) -> bool:
        """Mark an approved comment as successfully published."""
        try:
            client = get_supabase_client()
            res = (
                client.table("linkedin_review_queue")
                .update(
                    {
                        "status": ReviewStatus.PUBLISHED.value,
                        "published_at": datetime.now(UTC).isoformat(),
                        "unipile_id": unipile_id,
                    }
                )
                .eq("id", str(comment_id))
                .execute()
            )
            return len(res.data) > 0 if res.data else False
        except Exception as e:
            logger.error("Failed to mark comment %s published: %s", comment_id, e)
            return False

    def expire_stale(self, hours: int = 48) -> int:
        """Automatically expire comments that have been pending too long."""
        try:
            client = get_supabase_client()
            cutoff = datetime.now(UTC) - timedelta(hours=hours)

            # Using Supabase ORM for update with filter
            res = (
                client.table("linkedin_review_queue")
                .update({"status": ReviewStatus.EXPIRED.value})
                .eq("status", ReviewStatus.PENDING_REVIEW.value)
                .lt("generated_at", cutoff.isoformat())
                .execute()
            )
            count = len(res.data) if res.data else 0
            if count > 0:
                logger.info("Expired %d stale comments from review queue", count)
            return count
        except Exception as e:
            logger.error("Failed to expire stale comments: %s", e)
            return 0
