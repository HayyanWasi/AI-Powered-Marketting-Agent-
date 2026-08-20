"""Marketing Strategy Agent — generates the campaign strategy brief.

This agent:
- Analyzes brand context, guest profiles, and event details
- Generates USP hook, messaging pillars, objection handling, CTAs
- Uses LLM (Groq primary, Gemini fallback) for reasoning

Requires: LLMService (Groq primary, Gemini fallback)
"""

import logging
import re
from dataclasses import replace

from src.agents.base import AgentResult, BaseAgent
from src.agents.context import GenerationContext, StrategyData
from src.config.settings import settings
from src.models.llm import LLMRequest
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert Chief Marketing Officer (CMO). You create compelling "
    "marketing strategies for events and brands. Always respond using the exact "
    "labeled format requested — no preamble, no extra commentary."
)


class StrategyAgent(BaseAgent):
    """Generates the marketing strategy brief.

    Acts as virtual CMO — creates the strategic backbone
    that all content generation follows.
    """

    def __init__(self, llm_service: LLMService | None = None):
        """Initialize the agent.

        Args:
            llm_service: LLM backend. Constructed lazily on first
                use if not provided.
        """
        super().__init__("strategy")
        self._llm = llm_service

    def execute(self, context: GenerationContext) -> AgentResult:
        """Derive the strategy brief for downstream content generation.

        When an approved CampaignPlan is present it is the source of truth and
        no LLM call is made — the plan the marketer approved is what content
        must follow. Otherwise fall back to generating a brief directly.
        """
        if context.plan is not None and context.plan.approved:
            strategy = context.plan.to_strategy_data()
            return AgentResult(
                success=True,
                context=replace(
                    context, strategy=strategy, current_step="strategy_complete"
                ),
                message="Strategy derived from the approved campaign plan.",
            )

        if not context.brand.company_name:
            return AgentResult(
                success=False,
                context=context,
                message="Brand data required for strategy generation.",
            )

        # Build prompt for LLM
        prompt = self._build_strategy_prompt(context)

        try:
            response = self._get_llm().generate(
                LLMRequest(
                    system_prompt=_SYSTEM_PROMPT,
                    user_prompt=prompt,
                    prompt_name="generate_strategy",
                )
            )
            parsed = self._parse_response(response.text)
            failure = "LLM response did not match the expected format" if parsed is None else ""
        except Exception as e:
            self.logger.warning("LLM strategy generation failed: %s", e)
            parsed = None
            failure = str(e)

        if parsed is None:
            if not settings.ALLOW_PLACEHOLDER_CONTENT:
                # Surfacing the failure lets the workflow's retry wrapper run.
                # Silently shipping placeholder copy hides a broken pipeline.
                return AgentResult(
                    success=False,
                    context=context,
                    message=f"Strategy generation failed: {failure}",
                )
            self.logger.warning("Using placeholder strategy (%s)", failure)
            strategy = self._placeholder_strategy(context)
        else:
            strategy = parsed

        # Create new context with strategy
        new_context = replace(context, strategy=strategy, current_step="strategy_complete")

        self.logger.info("Strategy generated: %s", strategy.usp_hook[:50])

        return AgentResult(
            success=True,
            context=new_context,
            message="Strategy brief generated. Requires human approval.",
            requires_human=True,
        )

    def _build_strategy_prompt(self, context: GenerationContext) -> str:
        """Build the LLM prompt for strategy generation."""
        guests_text = (
            "\n".join(f"- {g.full_name}, {g.position} at {g.organization}" for g in context.guests)
            or "No guests specified"
        )

        return f"""Create a marketing strategy brief for this event:

Event: {context.event.event_name}
Date: {context.event.event_date}
Venue: {context.event.venue}
Platforms: {', '.join(context.event.platforms) or 'Not specified'}
Registration: {context.event.registration_link or 'Not provided'}

Brand: {context.brand.company_name}
Brand Guidelines: {context.brand.brand_guidelines or 'Not provided'}
Brand Tone: {context.brand.brand_tone or 'Professional'}

Guests/Speakers:
{guests_text}

Generate a strategy with EXACTLY this format:
USP_HOOK: <one compelling sentence that captures the unique selling proposition>
MESSAGING_PILLARS: <3 themes, comma-separated>
OBJECTION_HANDLING: <2 common objections with counter-arguments, separated by semicolon>
CTA_HIERARCHY: <2 calls-to-action (awareness then conversion), comma-separated>"""

    @staticmethod
    def _parse_response(text: str) -> StrategyData | None:
        """Parse the labeled LLM response into StrategyData."""
        labels = ["USP_HOOK", "MESSAGING_PILLARS", "OBJECTION_HANDLING", "CTA_HIERARCHY"]
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

        if not values.get("USP_HOOK"):
            return None

        # Parse comma/semicolon separated values
        pillars = tuple(
            p.strip() for p in values.get("MESSAGING_PILLARS", "").split(",") if p.strip()
        ) or ("Industry leaders", "High value", "Limited seats")

        objections = tuple(
            o.strip() for o in values.get("OBJECTION_HANDLING", "").split(";") if o.strip()
        ) or ("Is it worth my time? — Industry leaders attend",)

        ctas = tuple(
            c.strip() for c in values.get("CTA_HIERARCHY", "").split(",") if c.strip()
        ) or ("Follow for updates", "Register now")

        return StrategyData(
            usp_hook=values["USP_HOOK"],
            messaging_pillars=pillars,
            objection_handling=objections,
            cta_hierarchy=ctas,
            approved=False,
        )

    def _placeholder_strategy(self, context: GenerationContext) -> StrategyData:
        """Deterministic fallback when LLM is unavailable."""
        return StrategyData(
            usp_hook=f"Discover something new with {context.brand.company_name}",
            messaging_pillars=(
                "Learn from industry leaders",
                "Free entry, high value",
                "Limited seats available",
            ),
            objection_handling=(
                "Is it worth my time? — Industry leaders attend",
                "Is it free? — Yes, but seats are limited",
            ),
            cta_hierarchy=(
                "Follow for updates",
                "Register now — limited seats",
            ),
            approved=False,
        )

    def _get_llm(self) -> LLMService:
        """Return the LLM service, constructing it lazily."""
        if self._llm is None:
            self._llm = LLMService()
        return self._llm
