"""Hook Analyzer Sub-Agent — scores the first line for scroll-stopping power.

Uses heuristics to score hooks from 0-100.
"""

from dataclasses import replace

from src.agents.base import AgentResult, BaseAgent
from src.agents.context import GenerationContext


class HookAnalyzerAgent(BaseAgent):
    """Scores content hooks for scroll-stopping power."""

    def __init__(self):
        super().__init__("hook_analyzer")

    def execute(self, context: GenerationContext) -> AgentResult:
        """Score each content draft's hook and save to context."""
        if not context.content_drafts:
            return AgentResult(
                success=False,
                context=context,
                message="No content drafts to analyze.",
            )

        scored_drafts = []
        for draft in context.content_drafts:
            score = self._score_hook(draft.variant_a)
            scored_drafts.append(replace(draft, hook_score=score))

            self.logger.info(
                "Slot %s hook score: %d/100",
                draft.slot_id,
                score,
            )

        new_context = replace(context, content_drafts=tuple(scored_drafts))

        avg_score = sum(d.hook_score for d in scored_drafts) / len(scored_drafts)
        self.logger.info("Average hook score: %.1f/100", avg_score)

        return AgentResult(
            success=True,
            context=new_context,
            message=f"Hook analysis complete. Average score: {avg_score:.0f}/100 for {len(scored_drafts)} drafts.",
        )

    def _score_hook(self, hook: str) -> int:
        """Score a hook from 0-100.

        Scoring criteria:
        - Length: 10-50 chars is ideal (+15)
        - Question marks suggest engagement (+10)
        - Numbers suggest specificity (+10)
        - Power words increase urgency (+10)
        - Too long (>100 chars) penalized (-10)
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
        power_words = [
            "discover",
            "secret",
            "exclusive",
            "free",
            "new",
            "proven",
            "boost",
            "ultimate",
        ]
        if any(w in hook.lower() for w in power_words):
            score += 10

        return min(100, max(0, score))
