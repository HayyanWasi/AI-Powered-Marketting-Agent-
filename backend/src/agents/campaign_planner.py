"""Campaign Planner Agent — builds the content calendar grid.

This agent:
- Takes the approved strategy
- Creates content slots per platform per day
- Assigns themes and phases to each slot

No LLM needed — pure date math and slot assignment.
"""

from dataclasses import replace

from src.agents.base import AgentResult, BaseAgent
from src.agents.context import ContentSlot, GenerationContext


class CampaignPlannerAgent(BaseAgent):
    """Builds the content calendar with platform-specific slots."""

    def __init__(self):
        super().__init__("campaign_planner")

    def execute(self, context: GenerationContext) -> AgentResult:
        """Generate content calendar slots."""
        if not context.strategy.approved:
            return AgentResult(
                success=False,
                context=context,
                message="Strategy must be approved before planning.",
            )

        if not context.event.platforms:
            return AgentResult(
                success=False,
                context=context,
                message="No platforms specified in event details.",
            )

        # Generate calendar slots
        slots = self._generate_slots(context)

        new_context = replace(
            context,
            calendar=tuple(slots),
            current_step="planning_complete",
        )

        self.logger.info("Generated %d content slots", len(slots))

        return AgentResult(
            success=True,
            context=new_context,
            message=f"Calendar created with {len(slots)} slots.",
        )

    def _generate_slots(self, context: GenerationContext) -> list[ContentSlot]:
        """Generate content slots.

        When an approved CampaignPlan is attached, slots are built from the
        plan's dated content calendar — real dates, themes, and phases decided
        by the Channel Planner specialist.  Otherwise falls back to the legacy
        fixed-phases loop so campaigns without a plan still work.
        """
        # ── Plan-aware path ──────────────────────────────────────────────
        if context.plan is not None and context.plan.approved:
            slots = []
            for cal_slot in context.plan.channel_plan.calendar_slots:
                slots.append(
                    ContentSlot(
                        slot_id=cal_slot.slot_id,
                        date=cal_slot.date,
                        platform=cal_slot.platform,
                        phase=cal_slot.phase.value,
                        theme=cal_slot.theme,
                        format_type=cal_slot.format_type,
                    )
                )
            self.logger.info("Built %d slots from approved plan calendar", len(slots))
            return slots

        # ── Legacy path ──────────────────────────────────────────────────
        slots = []
        slot_id = 0
        for platform in context.event.platforms:
            for phase in ["Awareness", "Authority", "Urgency"]:
                slot_id += 1
                slots.append(
                    ContentSlot(
                        slot_id=str(slot_id),
                        date=context.event.event_date,
                        platform=platform,
                        phase=phase,
                        theme=f"{phase} content for {context.brand.company_name}",
                        format_type=self._get_format(platform),
                    )
                )

        return slots

    def _get_format(self, platform: str) -> str:
        """Get the default format type for a platform."""
        formats = {
            "linkedin": "Feed Post",
            "instagram": "Carousel",
            "facebook": "Feed Post",
            "twitter": "Tweet",
            "tiktok": "Video Script",
        }
        return formats.get(platform.lower(), "Feed Post")
