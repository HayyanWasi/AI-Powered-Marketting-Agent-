"""Marketing Strategy Agent — generates the campaign strategy brief.

This agent:
- Analyzes brand context, guest profiles, and event details
- Generates USP hook, messaging pillars, objection handling, CTAs
- Uses LLM (Gemini) for reasoning

Requires: LLM (Gemini 1.5 Flash — free tier)
"""

from src.agents.base import BaseAgent, AgentResult
from src.agents.context import GenerationContext, StrategyData


class StrategyAgent(BaseAgent):
    """Generates the marketing strategy brief.

    Acts as virtual CMO — creates the strategic backbone
    that all content generation follows.
    """

    def __init__(self):
        super().__init__("strategy")

    def execute(self, context: GenerationContext) -> AgentResult:
        """Generate strategy brief using LLM.

        In production, this calls Gemini 1.5 Flash with a CMO prompt.
        """
        if not context.brand.company_name:
            return AgentResult(
                success=False,
                context=context,
                message="Brand data required for strategy generation.",
            )

        # Build prompt for LLM
        prompt = self._build_strategy_prompt(context)

        # TODO: Call Gemini LLM here
        # For now, return a placeholder strategy
        strategy = StrategyData(
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

        # Create new context with strategy
        from dataclasses import replace

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
        guests_text = "\n".join(
            f"- {g.full_name}, {g.position} at {g.organization}" for g in context.guests
        )

        return f"""You are an expert Chief Marketing Officer.

Create a marketing strategy brief for this event:

Event: {context.event.event_name}
Date: {context.event.event_date}
Platforms: {', '.join(context.event.platforms)}

Brand: {context.brand.company_name}
Brand Guidelines: {context.brand.brand_guidelines}
Brand Tone: {context.brand.brand_tone}

Guests:
{guests_text}

Generate:
1. USP Hook (one compelling sentence)
2. Messaging Pillars (3 themes)
3. Objection Handling (2 common objections + counter-arguments)
4. CTA Hierarchy (2 calls-to-action, awareness then conversion)"""
