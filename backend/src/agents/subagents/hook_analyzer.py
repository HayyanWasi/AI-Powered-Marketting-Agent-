"""Hook Analyzer Sub-Agent — scores the first line for scroll-stopping power.

Requires: LLM (Gemini — cheap call)
"""

from src.agents.base import BaseAgent, AgentResult
from src.agents.context import GenerationContext
from dataclasses import replace


class HookAnalyzerAgent(BaseAgent):
    """Scores content hooks for scroll-stopping power."""

    def __init__(self):
        super().__init__("hook_analyzer")

    def execute(self, context: GenerationContext) -> AgentResult:
        """Score each content draft's hook."""
        if not context.content_drafts:
            return AgentResult(
                success=False,
                context=context,
                message="No content drafts to analyze.",
            )

        # Score each draft's first variant (hook)
        scored_drafts = []
        for draft in context.content_drafts:
            score = self._score_hook(draft.variant_a)
            scored_drafts.append(draft)

            self.logger.info(
                "Slot %s hook score: %d/100",
                draft.slot_id,
                score,
            )

        return AgentResult(
            success=True,
            context=context,
            message=f"Hook analysis complete for {len(scored_drafts)} drafts.",
        )

    def _score_hook(self, hook: str) -> int:
        """Score a hook from 0-100.

        In production, this calls Gemini for nuanced analysis.
        For now, use simple heuristics.
        """
        score = 50  # Base score

        # Length check: 10-50 chars is ideal
        if 10 <= len(hook) <= 50:
            score += 15
        elif len(hook) > 100:
            score -= 10

        # Question marks suggest engagement
        if "?" in hook:
            score += 10

        # Numbers suggest specificity
        if any(c.isdigit() for c in hook):
            score += 10

        # Power words
        power_words = ["discover", "secret", "exclusive", "free", "new", "proven"]
        if any(w in hook.lower() for w in power_words):
            score += 10

        return min(100, max(0, score))
