from unittest.mock import MagicMock, patch

import pytest

from src.modules.linkedin.models import GeneratedComment, ReviewStatus
from src.modules.linkedin.worker.review_queue import ReviewQueue


@pytest.fixture
def mock_supabase():
    with patch("src.modules.linkedin.worker.review_queue.get_supabase_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


def test_add_comment(mock_supabase):
    queue = ReviewQueue()

    comment = GeneratedComment(
        target_post_id="post_1",
        target_post_snippet="Snippet",
        target_author_name="Jane Doe",
        persona_label="Test",
        generated_text="Good post!",
    )

    cid = queue.add_comment(comment)

    # Assert DB insert called
    mock_supabase.table().insert.assert_called_once()
    args = mock_supabase.table().insert.call_args[0][0]

    # Verify the comment status defaults correctly
    assert args["status"] == ReviewStatus.PENDING_REVIEW.value
    # Verify expiration is computed (exists)
    assert args["expires_at"] is not None


def test_approve_comment(mock_supabase):
    mock_supabase.table().update().eq().execute.return_value = MagicMock(data=[{"id": "c1"}])
    queue = ReviewQueue()

    result = queue.approve("c1")

    assert result is True
    # Verify it updates to APPROVED
    args = mock_supabase.table().update.call_args[0][0]
    assert args["status"] == ReviewStatus.APPROVED.value


def test_reject_comment(mock_supabase):
    mock_supabase.table().update().eq().execute.return_value = MagicMock(data=[{"id": "c2"}])
    queue = ReviewQueue()

    result = queue.reject("c2", "Too robotic")

    assert result is True
    # Verify it updates to REJECTED and logs reason
    args = mock_supabase.table().update.call_args[0][0]
    assert args["status"] == ReviewStatus.REJECTED.value
    assert args["reject_reason"] == "Too robotic"


def test_expire_stale(mock_supabase):
    mock_supabase.table().update().eq().lt().execute.return_value = MagicMock(
        data=[{"id": "c1"}, {"id": "c2"}]
    )
    queue = ReviewQueue()

    count = queue.expire_stale(hours=48)

    assert count == 2
    args = mock_supabase.table().update.call_args[0][0]
    assert args["status"] == ReviewStatus.EXPIRED.value
