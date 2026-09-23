"""Comment Generator (Post-Context-Only).

Generates human-like LinkedIn comments strictly based on the text of the
target post, with NO web search or bullet points.
"""

from __future__ import annotations

import logging

from src.models.llm import LLMRequest
from src.modules.linkedin.models import GeneratedComment, TargetPost
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)

_COMMENT_SYSTEM_PROMPT = """You are an expert LinkedIn ghostwriter. Write one relevant, plain-text comment on the supplied LinkedIn post.
Follow these rules:
1. Write ONLY 1 or 2 short sentences.
2. NEVER use bullet points, numbered lists, or emojis.
3. NEVER cite external sources or write essays.
4. Keep it direct, human, and slightly casual but professional.
5. Base your comment ONLY on the provided post text. Do not invent facts.
6. Do not include hashtags.

Output ONLY the text of the comment. No quotes, no intro text.
"""


class CommentGenerator:
    """Generates grounded LinkedIn comments with the canonical LLM service."""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self._llm = llm_service or LLMService()

    def generate_comment(
        self, target_post: TargetPost, commenter_persona: str = ""
    ) -> GeneratedComment:
        """Generate a comment strictly based on the target post content."""
        user_prompt = f"Target Post:\n{target_post.content}"

        request = LLMRequest(
            system_prompt=_COMMENT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            prompt_name="linkedin_comment_generator",
        )

        try:
            response = self._llm.generate(request)
            generated_text = response.text.strip().strip('"').strip("'")

            if not generated_text:
                raise RuntimeError("Comment model returned empty content")

        except Exception as e:
            logger.error("Failed to generate comment: %s", e)
            raise RuntimeError(
                "LinkedIn comment generation failed; no review item was created"
            ) from e

        snippet = target_post.content[:200]
        if len(target_post.content) > 200:
            snippet += "..."

        return GeneratedComment(
            target_post_id=target_post.post_id,
            target_post_snippet=snippet,
            target_author_name=target_post.author_name,
            persona_label=target_post.persona_label,
            generated_text=generated_text,
        )
