"""Readability Scorer Sub-Agent — checks Flesch score and mobile readability.

No LLM needed — pure math.
"""

from dataclasses import replace

from src.agents.base import AgentResult, BaseAgent
from src.agents.context import GenerationContext


class ReadabilityScorerAgent(BaseAgent):
    """Scores content for readability and mobile-friendliness."""

    def __init__(self):
        super().__init__("readability_scorer")

    def execute(self, context: GenerationContext) -> AgentResult:
        """Score each content draft for readability and save to context."""
        if not context.content_drafts:
            return AgentResult(
                success=False,
                context=context,
                message="No content drafts to score.",
            )

        scored_drafts = []
        for draft in context.content_drafts:
            score = self._calculate_flesch(draft.variant_a)
            scored_drafts.append(replace(draft, readability_score=score))

            self.logger.info(
                "Slot %s readability: %.1f",
                draft.slot_id,
                score,
            )

        new_context = replace(context, content_drafts=tuple(scored_drafts))

        avg_score = sum(d.readability_score for d in scored_drafts) / len(scored_drafts)
        self.logger.info("Average readability: %.1f", avg_score)

        return AgentResult(
            success=True,
            context=new_context,
            message=f"Readability scored. Average: {avg_score:.1f} for {len(scored_drafts)} drafts.",
        )

    def _calculate_flesch(self, text: str) -> float:
        """Calculate Flesch Reading Ease score.

        60-70 = Standard
        70-80 = Fairly Easy
        80-90 = Easy
        """
        if not text:
            return 0.0

        words = text.split()
        sentences = text.count(".") + text.count("!") + text.count("?")
        if sentences == 0:
            sentences = 1

        syllables = sum(self._count_syllables(w) for w in words)
        word_count = len(words) or 1

        score = 206.835 - 1.015 * (word_count / sentences) - 84.6 * (syllables / word_count)
        return max(0, min(100, score))

    def _count_syllables(self, word: str) -> int:
        """Estimate syllable count."""
        word = word.lower().strip()
        if len(word) <= 3:
            return 1

        vowels = "aeiou"
        count = 0
        prev_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel

        if word.endswith("e"):
            count -= 1

        return max(1, count)
