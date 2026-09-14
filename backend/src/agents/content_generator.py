"""Content Generation Agent — writes platform-native copy with 3 variants.

This agent:
- Reads strategy, brand, guest, and event data from context
- Generates 3 copy variants per slot (story, value, question) via the LLM
- Generates an image prompt for each slot

Requires: LLMService (Groq primary, Gemini fallback).
"""

import logging
import re
from dataclasses import replace

from src.agents.base import AgentResult, BaseAgent
from src.agents.context import ContentDraft, ContentSlot, GenerationContext
from src.models.llm import LLMRequest
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert social media copywriter. You write concise, "
    "platform-native marketing copy. You never invent facts, statistics, "
    "or claims not present in the provided context. Always respond using "
    "the exact labeled format requested — no preamble, no extra commentary."
)

# Category -> angle guidance, injected into the prompt so copy leads with
# the right psychological hook for the campaign type.
_CATEGORY_ANGLES: dict[str, str] = {
    "seminar": (
        "Angle: AUTHORITY. VARIANT_A must open with the guest's name and "
        "title as the hook. VARIANT_B lists concrete takeaways attendees "
        "will leave with. VARIANT_C asks a question built around learning "
        "from the named guest."
    ),
    "product_launch": (
        "Angle: DIFFERENTIATION. VARIANT_A tells a before/after story. "
        "VARIANT_B lists features tied directly to benefits. VARIANT_C "
        "asks what's stopping the reader from the outcome."
    ),
    "ecommerce_sale": (
        "Angle: URGENCY. VARIANT_A tells a short deal-scarcity story. "
        "VARIANT_B lists the discount and deadline plainly. VARIANT_C "
        "asks if the reader is still paying full price."
    ),
    "saas_demo": (
        "Angle: OBJECTION HANDLING. VARIANT_A tells a customer-style "
        "story. VARIANT_B lists ROI/metric-style benefits. VARIANT_C "
        "asks what if demos didn't waste the reader's time."
    ),
    "course_enrollment": (
        "Angle: OUTCOME/CREDENTIAL. VARIANT_A tells a graduate-style "
        "story. VARIANT_B lists curriculum and certificate details. "
        "VARIANT_C challenges the reader's excuse not to enroll."
    ),
}
_DEFAULT_ANGLE = (
    "Angle: VALUE. Ground each variant in the specific brand, event, and "
    "guest details given below — do not default to generic industry hype."
)


class ContentGenerationAgent(BaseAgent):
    """Generates platform-native content with multiple variants."""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        super().__init__("content_generator")
        self._llm = llm_service

    def execute(self, context: GenerationContext) -> AgentResult:
        """Generate content for all calendar slots."""
        if not context.calendar:
            return AgentResult(
                success=False,
                context=context,
                message="No calendar slots to generate content for.",
            )

        drafts = [self._generate_for_slot(slot, context) for slot in context.calendar]

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

    def _generate_for_slot(self, slot: ContentSlot, context: GenerationContext) -> ContentDraft:
        """Generate 3 variants and an image prompt for a single slot."""
        prompt = self._build_content_prompt(slot, context)

        # ── DATA INSERTION LOGGING ──
        self.logger.info(
            "=== [CONTENT GENERATION] PROMPT DATA INSERTION AUDIT (Slot: %s) ===", slot.slot_id
        )
        self.logger.info("Prompt String Sent to LLM:\n%s", prompt)

        check_event = context.event.event_name in prompt if context.event.event_name else True
        check_guest = context.guests[0].full_name in prompt if context.guests else True
        check_date = context.event.event_date in prompt if context.event.event_date else True
        check_venue = context.event.venue in prompt if context.event.venue else True
        check_link = (
            context.event.registration_link in prompt if context.event.registration_link else True
        )

        if check_event and check_guest and check_date and check_venue and check_link:
            self.logger.info(
                "[AUDIT RESULT] Data-Insertion: PASSED (All available fields present in prompt)"
            )
        else:
            self.logger.warning(
                "[AUDIT RESULT] Data-Insertion: FAILED (Some fields missing from prompt string)"
            )

        try:
            response = self._get_llm().generate(
                LLMRequest(
                    system_prompt=_SYSTEM_PROMPT,
                    user_prompt=prompt,
                    prompt_name="generate_content",
                )
            )
            parsed = self._parse_response(response.text)
        except Exception as e:  # noqa: BLE001 - degrade gracefully on any LLM error
            self.logger.warning(
                "LLM copy generation failed for slot %s (%s); using placeholder",
                slot.slot_id,
                e,
            )
            parsed = None

        if parsed is None:
            return self._placeholder_draft(slot, context)

        variant_a, variant_b, variant_c, image_prompt = parsed

        # ── INSTRUCTION FOLLOWING LOGGING ──
        full_copy = f"{variant_a}\n{variant_b}\n{variant_c}"
        self.logger.info("=== [CONTENT GENERATION] INSTRUCTION FOLLOWING AUDIT ===")
        self.logger.info(
            "Generated Copy Variants:\nVARIANT_A: %s\nVARIANT_B: %s\nVARIANT_C: %s",
            variant_a,
            variant_b,
            variant_c,
        )

        if context.guests:
            has_guest_name = any(
                g.full_name in full_copy or g.full_name.split()[0] in full_copy
                for g in context.guests
            )
            self.logger.info(
                "[INSTRUCTION AUDIT] Guest Name Included: %s",
                "PASSED" if has_guest_name else "FAILED",
            )
        if context.event.registration_link:
            has_link = context.event.registration_link in full_copy or "http" in full_copy
            self.logger.info(
                "[INSTRUCTION AUDIT] Registration Link Included: %s",
                "PASSED" if has_link else "FAILED",
            )

        return ContentDraft(
            slot_id=slot.slot_id,
            variant_a=variant_a,
            variant_b=variant_b,
            variant_c=variant_c,
            image_prompt=image_prompt or self._default_image_prompt(slot, context),
            selected_variant="",
        )

    def _build_content_prompt(self, slot: ContentSlot, context: GenerationContext) -> str:
        """Build the LLM user prompt for content generation.

        Folds in brand, guest, event, category angle, and (when present)
        the plan's strategy — draft or approved — so copy reflects all
        dimensions instead of defaulting to generic hype copy.
        """
        from src.agents.context_selector import ContextSelector

        guests_text = ", ".join(g.full_name for g in context.guests) or "N/A"
        guest_bios = ContextSelector.select_guest_context(slot, context.guests)
        guest_directive = (
            "GUEST RULE: The guest(s) above are the primary hook. "
            "VARIANT_A must open by naming them and their title — do not "
            "reduce them to 'expert speakers' or bury them mid-paragraph."
            if context.guests
            else ""
        )

        # Registration link — was previously missing from the prompt entirely.
        registration_line = (
            f"Registration link: {context.event.registration_link}\n"
            "CTA RULE: Use this exact link in VARIANT_A and VARIANT_B's CTA. "
            "Never write 'link in bio' when a real link is provided above."
            if getattr(context.event, "registration_link", None)
            else "Registration link: not provided — use a clear directional "
            "CTA instead of inventing a link."
        )

        # ── Plan strategy block — now included for draft plans too, not
        # only approved ones. A draft USP/tone is still better than none. ──
        plan_block = ""
        if context.plan is not None:
            cs = context.plan.core_strategy

            phase_cta = ""
            for phase_plan in context.plan.channel_plan.phases:
                if phase_plan.phase.value == slot.phase:
                    phase_cta = phase_plan.primary_cta
                    break
            if not phase_cta and context.plan.channel_plan.phases:
                phase_cta = context.plan.channel_plan.phases[-1].primary_cta

            objections = "; ".join(
                f"{o.objection} → {o.response}" for o in cs.objection_handling[:2]
            )

            status_note = (
                "APPROVED"
                if context.plan.approved
                else "DRAFT (still authoritative for tone/messaging)"
            )
            plan_block = f"""
MARKETING STRATEGY [{status_note}] (follow this):
USP: {cs.unique_selling_proposition}
Messaging pillar for this post: {slot.theme}
Tone of voice: {cs.tone_of_voice}
CTA for this phase: {phase_cta}
Objection handling: {objections}
"""

        category = getattr(slot, "category", None) or getattr(context.event, "category", None)
        angle_guidance = _CATEGORY_ANGLES.get(category, _DEFAULT_ANGLE)

        pricing_line = ""
        pricing = getattr(context.event, "ticket_price", None)  # e.g. "Free", "PKR 500"
        outcome = getattr(context.event, "outcome_deliverable", None)
        if pricing or outcome:
            pricing_line = (
                f"Pricing: {pricing or 'not specified'}\n"
                f"Outcome/deliverable: {outcome or 'not specified'}\n"
                "STATE THIS PLAINLY — do not replace with vague language "
                "like 'unlock your potential'."
            )

        return f"""Write a {slot.platform} post for: {slot.theme}
Platform: {slot.platform} (format: {slot.format_type})
Phase: {slot.phase}

{angle_guidance}

Brand: {context.brand.company_name}
Brand tone: {context.brand.brand_tone}
Brand guidelines: {context.brand.brand_guidelines}
Event: {context.event.event_name} on {context.event.event_date} at {context.event.venue}
{registration_line}
{pricing_line}
Guests/Speakers: {guests_text}
{guest_bios}
{guest_directive}
{plan_block}
RULE: Never invent statistics, quotes, or facts not present above. If a
detail isn't given, omit it rather than guessing.

Respond in EXACTLY this format:
VARIANT_A: <story-driven hook post>
VARIANT_B: <value/benefit list post>
VARIANT_C: <question hook post>
IMAGE_PROMPT: <a vivid visual description for an image generator, on-brand>"""

    @staticmethod
    def _parse_response(text: str) -> tuple[str, str, str, str] | None:
        """Parse the labeled LLM response into its four parts."""
        labels = ["VARIANT_A", "VARIANT_B", "VARIANT_C", "IMAGE_PROMPT"]
        values: dict[str, str] = {}
        for i, label in enumerate(labels):
            next_labels = "|".join(labels[i + 1 :]) or r"\Z"
            match = re.search(
                rf"{label}\s*:\s*(.*?)(?=\n\s*(?:{next_labels})\s*:|\Z)",
                text,
                re.DOTALL | re.IGNORECASE,
            )
            if match:
                values[label] = match.group(1).strip()

        if not any(values.get(v) for v in ("VARIANT_A", "VARIANT_B", "VARIANT_C")):
            return None

        return (
            values.get("VARIANT_A", ""),
            values.get("VARIANT_B", ""),
            values.get("VARIANT_C", ""),
            values.get("IMAGE_PROMPT", ""),
        )

    def _placeholder_draft(self, slot: ContentSlot, context: GenerationContext) -> ContentDraft:
        """Deterministic fallback content when the LLM is unavailable.

        Uses real context data (event, guest) instead of fully generic
        copy, so a transient LLM outage doesn't produce content that looks
        disconnected from the actual campaign.
        """
        event = context.event.event_name
        venue = context.event.venue
        company = context.brand.company_name
        guest_line = (
            f"featuring {context.guests[0].full_name}, {getattr(context.guests[0], 'position', '')}"
            if context.guests
            else "with our featured guest"
        )

        return ContentDraft(
            slot_id=slot.slot_id,
            variant_a=f"[Story] {company} presents {event} at {venue}, {guest_line}.",
            variant_b=f"[Value] Join {event} at {venue} — {guest_line}. Details to follow.",
            variant_c=f"[Question] What if you could learn directly from {guest_line.replace('featuring ', '').replace('with our ', '')}? Join us at {event}.",
            image_prompt=self._default_image_prompt(slot, context),
            selected_variant="",
        )

    @staticmethod
    def _default_image_prompt(slot: ContentSlot, context: GenerationContext) -> str:
        """Build a default image prompt from event/brand context."""
        return (
            f"Professional event banner for {context.event.event_name}, "
            f"{context.brand.company_name} branding"
        )

    def _get_llm(self) -> LLMService:
        """Return the LLM service, constructing it lazily."""
        if self._llm is None:
            self._llm = LLMService()
        return self._llm
