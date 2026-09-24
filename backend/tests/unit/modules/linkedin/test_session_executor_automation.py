from datetime import UTC, datetime, time
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from src.modules.linkedin.models import (
    GeneratedComment,
    ResolvedTarget,
    SessionWindow,
    TargetPost,
)
from src.modules.linkedin.worker.session_executor import SessionExecutor
from tests.unit.api.test_engagement_safety import MockSupabaseClient


def _post(post_id: str) -> TargetPost:
    return TargetPost(
        post_id=post_id,
        author_profile_id=f"author-{post_id}",
        author_name="Target Author",
        content="A detailed target post with enough context for a relevant AI comment.",
        posted_at=datetime.now(UTC),
        persona_label="Decision Makers",
    )


@pytest.mark.asyncio
async def test_session_executes_ai_comment_like_and_invite_with_separate_caps() -> None:
    stores = {
        "linkedin_review_queue": [],
        "linkedin_engagement_log": [],
        "linkedin_engaged_posts": [],
    }
    mock_client = MockSupabaseClient(stores)

    circuit_breaker = MagicMock()
    circuit_breaker.can_proceed.return_value = True
    rate_limiter = AsyncMock()
    ledger = AsyncMock()
    ledger.try_acquire.return_value = True
    resolver = AsyncMock()
    resolver.load_personas.return_value = ["persona"]
    resolver.get_engagement_targets.side_effect = [[_post("comment-post")], [_post("like-post")]]
    resolver.get_invite_targets.return_value = [
        ResolvedTarget(
            account_id="account-1",
            persona_label="Decision Makers",
            profile_id="profile-1",
        )
    ]
    review_queue = MagicMock()
    review_queue.get_approved_for_publishing.return_value = []
    comment_generator = MagicMock()
    comment_generator.generate_comment.return_value = GeneratedComment(
        target_post_id="comment-post",
        generated_text="The distinction you made here is useful and clearly explained.",
    )
    unipile = AsyncMock()
    unipile.like_post.return_value = True
    unipile.send_connection_request.return_value = "invite-1"

    executor = SessionExecutor(
        "account-1",
        "Asia/Karachi",
        circuit_breaker=circuit_breaker,
        rate_limiter=rate_limiter,
        action_ledger=ledger,
        target_resolver=resolver,
        review_queue=review_queue,
        comment_generator=comment_generator,
        unipile=unipile,
        client=mock_client,
    )
    session = SessionWindow(
        start=time(9),
        end=time(10),
        max_actions=10,
        action_types=("comment", "like", "invite"),
    )

    result = await executor.execute_session(
        session,
        daily_invite_limit=25,
        daily_like_limit=40,
        daily_comment_limit=15,
    )

    assert result.actions_attempted == 3
    assert result.actions_succeeded == 3
    assert ledger.try_acquire.await_args_list == [
        call("account-1", "comment", 15, "Asia/Karachi"),
        call("account-1", "like", 40, "Asia/Karachi"),
        call("account-1", "invite", 25, "Asia/Karachi"),
    ]
    # Safety invariant: comments are generation-only to review queue, never directly called
    unipile.comment_on_post.assert_not_awaited()
    assert len(stores["linkedin_review_queue"]) == 1
    queue_item = stores["linkedin_review_queue"][0]
    assert queue_item["status"] == "pending_review"
    assert "generated_at" in queue_item
    assert "created_at" not in queue_item
    assert (
        queue_item["generated_text"]
        == "The distinction you made here is useful and clearly explained."
    )

    unipile.like_post.assert_awaited_once_with("account-1", "like-post")
    unipile.send_connection_request.assert_awaited_once_with("account-1", "profile-1", None)


@pytest.mark.asyncio
async def test_review_queue_insert_uses_generated_at_and_pending_review() -> None:
    """Proves review queue insert uses canonical generated_at (no created_at) and reaches pending_review."""
    stores = {
        "linkedin_review_queue": [],
        "linkedin_engagement_log": [],
        "linkedin_engaged_posts": [],
    }
    mock_client = MockSupabaseClient(stores)

    circuit_breaker = MagicMock()
    circuit_breaker.can_proceed.return_value = True
    ledger = AsyncMock()
    resolver = AsyncMock()
    review_queue = MagicMock()
    comment_generator = MagicMock()
    unipile = AsyncMock()

    executor = SessionExecutor(
        "account-1",
        "UTC",
        circuit_breaker=circuit_breaker,
        rate_limiter=AsyncMock(),
        action_ledger=ledger,
        target_resolver=resolver,
        review_queue=review_queue,
        comment_generator=comment_generator,
        unipile=unipile,
        client=mock_client,
        company_profile_id="company-1",
        user_id="user-1",
    )

    target = _post("target-post-123")
    queued = await executor._queue_comment(
        target,
        comment_text="Insightful analysis on marketing automation.",
        current_count=0,
        max_count=5,
    )

    assert queued is True
    assert len(stores["linkedin_review_queue"]) == 1

    row = stores["linkedin_review_queue"][0]
    # 1. review queue insert uses generated_at and strictly NO created_at
    assert "generated_at" in row
    assert "created_at" not in row
    assert isinstance(row["generated_at"], str)

    # 2. generated draft reaches pending_review
    assert row["status"] == "pending_review"
    assert row["generated_text"] == "Insightful analysis on marketing automation."
    assert row["target_post_id"] == "target-post-123"
    assert row["linkedin_account_id"] == "account-1"
    assert row["company_profile_id"] == "company-1"
    assert row["user_id"] == "user-1"

    # Zero external dispatch
    unipile.comment_on_post.assert_not_awaited()


@pytest.mark.asyncio
async def test_ai_comment_failure_never_posts_fallback_text() -> None:
    stores = {
        "linkedin_review_queue": [],
        "linkedin_engagement_log": [],
        "linkedin_engaged_posts": [],
    }
    mock_client = MockSupabaseClient(stores)

    circuit_breaker = MagicMock()
    circuit_breaker.can_proceed.return_value = True
    ledger = AsyncMock()
    resolver = AsyncMock()
    resolver.load_personas.return_value = ["persona"]
    resolver.get_engagement_targets.return_value = [_post("comment-post")]
    review_queue = MagicMock()
    review_queue.get_approved_for_publishing.return_value = []
    comment_generator = MagicMock()
    comment_generator.generate_comment.side_effect = RuntimeError("all providers failed")
    unipile = AsyncMock()

    executor = SessionExecutor(
        "account-1",
        "UTC",
        circuit_breaker=circuit_breaker,
        rate_limiter=AsyncMock(),
        action_ledger=ledger,
        target_resolver=resolver,
        review_queue=review_queue,
        comment_generator=comment_generator,
        unipile=unipile,
        client=mock_client,
    )
    session = SessionWindow(
        start=time(9),
        end=time(10),
        max_actions=1,
        action_types=("comment",),
    )

    result = await executor.execute_session(session, 25, 40, 15)

    assert result.actions_attempted == 0
    assert result.details["comment_generation_failures"] == 1
    ledger.try_acquire.assert_not_awaited()
    unipile.comment_on_post.assert_not_awaited()
