"""Content Generation Agent — writes platform-native copy with 3 variants.

This agent:
- Reads strategy, brand, guest data from context
- Fetches trending topics via DuckDuckGo (free)
- Generates 3 copy variants per slot (story, value, question)
- Generates image prompts

Requires: LLM (Gemini 1.5 Flash — free tier) + DuckDuckGo (free)
"""

from src.agents.base import BaseAgent, AgentResult
from src.agents.context import GenerationContext, ContentDraft
from dataclasses import replace


class ContentGenerationAgent(BaseAgent):
    """Generates platform-native content with multiple variants."""

    def __init__(self):
        super().__init__("content_generator")

    def execute(self, context: GenerationContext) -> AgentResult:
        """Generate content for all calendar slots."""
        if not context.calendar:
            return AgentResult(
                success=False,
                context=context,
                message="No calendar slots to generate content for.",
            )

        drafts = []
        for slot in context.calendar:
            draft = self._generate_for_slot(slot, context)
            drafts.append(draft)

        new_context = replace(
            context,
            content_drafts=tuple(drafts),
            current_step="content_complete",
        )

        self.logger.info("Generated %d content drafts", len(drafts))

        return AgentResult(
            success=True,
            context=new_context,
            message=f"Content generated for {len(drafts)} slots. Requires human approval.",
            requires_human=True,
        )

    def _generate_for_slot(self, slot, context: GenerationContext) -> ContentDraft:
        """Generate 3 variants for a single slot."""
        # Build prompt for LLM
        prompt = self._build_content_prompt(slot, context)

        # TODO: Call Gemini LLM here
        # For now, return placeholder content
        return ContentDraft(
            slot_id=slot.slot_id,
            variant_a=f"[Story] {context.brand.company_name} presents an exclusive opportunity at {context.event.event_name}.",
            variant_b=f"[Value] 3 reasons to attend {context.event.event_name}: expert speakers, networking, free entry.",
            variant_c=f"[Question] What if you could learn from the best in the industry? Join us at {context.event.event_name}.",
            image_prompt=f"Professional event banner for {context.event.event_name}, {context.brand.company_name} branding",
            selected_variant="",
        )

    def _build_content_prompt(self, slot, context: GenerationContext) -> str:
        """Build the LLM prompt for content generation."""
        guests_text = ", ".join(g.full_name for g in context.guests)

        return f"""You are an expert copywriter for {slot.platform}.

Write a post for: {slot.theme}
Platform: {slot.platform} (format: {slot.format_type})
Phase: {slot.phase}

Brand: {context.brand.company_name}
Tone: {context.brand.brand_tone}
Guests: {guests_text}

Generate 3 variants:
- Variant A: Story-driven hook
- Variant B: Value/benefit list
- Variant C: Question hook

Also generate an image prompt for visual content."""
