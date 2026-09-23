from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.modules.linkedin.generators.comment_generator import CommentGenerator
from src.modules.linkedin.models import ReviewStatus, TargetPost
from src.services.llm_service import LLMService


def test_comment_generator_prompt_constraints():
    # Mock LLMService
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.generate.return_value = MagicMock(text="This is a great point.")

    generator = CommentGenerator(llm_service=mock_llm)

    post = TargetPost(
        post_id="post_123",
        author_profile_id="author_1",
        author_name="John Doe",
        content="I love AI.",
        posted_at=datetime.now(UTC),
        persona_label="AI Target",
    )

    comment = generator.generate_comment(post)

    # Verify the LLM was called
    mock_llm.generate.assert_called_once()
    request = mock_llm.generate.call_args[0][0]

    # Verify strict prompt rules are in the system prompt
    assert "1 or 2 short sentences" in request.system_prompt
    assert "NEVER use bullet points" in request.system_prompt
    assert "Do not include hashtags" in request.system_prompt

    # Verify output maps to PENDING_REVIEW
    assert comment.status == ReviewStatus.PENDING_REVIEW
    assert comment.target_post_id == "post_123"
    assert comment.generated_text == "This is a great point."


def test_comment_generator_failure_does_not_create_fake_review_item():
    mock_llm = MagicMock(spec=LLMService)
    # Simulate an LLM failure
    mock_llm.generate.side_effect = Exception("API Error")

    generator = CommentGenerator(llm_service=mock_llm)

    post = TargetPost(
        post_id="post_456",
        author_profile_id="author_2",
        author_name="Jane Smith",
        content="Testing errors.",
        posted_at=datetime.now(UTC),
        persona_label="Error Target",
    )

    with pytest.raises(RuntimeError, match="no review item was created"):
        generator.generate_comment(post)
