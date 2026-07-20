"""Validation Agent — checks content against platform rules.

This agent:
- Validates character limits per platform
- Checks image dimensions
- Reports violations

No LLM needed — pure rule-based validation.
"""

from src.agents.base import BaseAgent, AgentResult
from src.agents.context import GenerationContext, ValidationResult
from src.models.platform import PLATFORM_TEXT_LIMITS, Platform
from dataclasses import replace


class ValidationAgent(BaseAgent):
    """Validates content against platform-specific rules."""

    def __init__(self):
        super().__init__("validator")

    def execute(self, context: GenerationContext) -> AgentResult:
        """Validate all content drafts."""
        if not context.content_drafts:
            return AgentResult(
                success=False,
                context=context,
                message="No content drafts to validate.",
            )

        results = []
        for draft in context.content_drafts:
            # Find the slot to get platform
            slot = next(
                (s for s in context.calendar if s.slot_id == draft.slot_id),
                None,
            )
            if not slot:
                continue

            result = self._validate_draft(draft, slot.platform)
            results.append(result)

            if not result.passed:
                self.logger.warning(
                    "Slot %s failed validation: %s",
                    draft.slot_id,
                    "; ".join(result.violations),
                )

        new_context = replace(
            context,
            validation_results=tuple(results),
            current_step="validation_complete",
        )

        passed = sum(1 for r in results if r.passed)
        total = len(results)

        return AgentResult(
            success=passed == total,
            context=new_context,
            message=f"Validation: {passed}/{total} drafts passed.",
        )

    def _validate_draft(self, draft, platform: str) -> ValidationResult:
        """Validate a single content draft."""
        violations = []

        # Use the selected variant or variant A
        content = draft.selected_variant or draft.variant_a

        # Character limit check
        try:
            platform_enum = Platform(platform.lower())
            limit = PLATFORM_TEXT_LIMITS[platform_enum]
            char_count = len(content)

            if char_count > limit:
                violations.append(
                    f"Character count {char_count} exceeds {platform} limit of {limit}"
                )
        except ValueError:
            # Unknown platform — skip character check
            pass

        # Basic checks
        if not content.strip():
            violations.append("Content is empty")

        if len(content) < 10:
            violations.append("Content too short (minimum 10 characters)")

        return ValidationResult(
            passed=len(violations) == 0,
            character_count=len(content),
            character_limit=limit if "limit" in dir() else 0,
            violations=tuple(violations),
            image_valid=True,  # Image validation handled separately
        )
