"""Refinement agents — route a critique, revise only what it targets, reply.

Section isolation is the contract: a marketer who asks to change the calendar
expects the positioning they already approved to come back byte-identical.
Only sections named by the router are regenerated.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.modules.planning.agents.panel import ask_json
from src.modules.planning.models.brief import PlanBrief
from src.modules.planning.models.campaign_plan import SECTION_NAMES, CampaignPlan

logger = logging.getLogger(__name__)


class Route:
    """Where a critique should land."""

    def __init__(
        self,
        target_sections: tuple[str, ...] = (),
        instructions: dict[str, str] | None = None,
        language: str = "en",
        is_approval: bool = False,
        reasoning: str = "",
    ) -> None:
        self.target_sections = target_sections
        self.instructions = instructions or {}
        self.language = language
        self.is_approval = is_approval
        self.reasoning = reasoning


def _plan_summary(plan: CampaignPlan) -> str:
    """A compact view of the plan — enough to route, cheaper than the full doc."""
    return json.dumps(
        {
            "title": plan.title,
            "objective": plan.core_strategy.objective,
            "usp": plan.core_strategy.unique_selling_proposition,
            "messaging_pillars": list(plan.core_strategy.messaging_pillars),
            "platforms": [p.platform for p in plan.channel_plan.platforms],
            "calendar_slot_count": len(plan.channel_plan.calendar_slots),
            "kpis": [k.name for k in plan.measurement.kpis],
            "differentiation_angle": plan.competitive.differentiation_angle,
        },
        ensure_ascii=False,
        indent=2,
    )


async def route_critique(plan: CampaignPlan, critique: str, **kw: Any) -> Route:
    """Decide which sections a critique touches, and in what language it came."""
    try:
        result = await ask_json(
            "plan_route_critique",
            {"plan_summary": _plan_summary(plan), "critique": critique},
            **kw,
        )
    except Exception as e:
        logger.warning("Critique routing failed (%s); treating as a question", e)
        return Route(language=plan.language)

    targets = tuple(s for s in (result.get("target_sections") or []) if s in SECTION_NAMES)
    instructions = {
        k: v for k, v in (result.get("instructions") or {}).items() if k in SECTION_NAMES
    }
    return Route(
        target_sections=targets,
        instructions=instructions,
        language=result.get("language") or plan.language,
        is_approval=bool(result.get("is_approval")),
        reasoning=result.get("reasoning") or "",
    )


async def revise_section(
    plan: CampaignPlan,
    brief: PlanBrief,
    section_name: str,
    critique: str,
    instructions: str = "",
    **kw: Any,
) -> dict[str, Any]:
    """Regenerate one section. Returns {} when the revision is unusable."""
    if section_name not in SECTION_NAMES:
        raise ValueError(f"Unknown plan section: {section_name}")

    section = getattr(plan, section_name)
    variables = brief.as_prompt_vars()
    variables.update(
        {
            "section_name": section_name,
            "section_content": json.dumps(
                section.model_dump(mode="json"), ensure_ascii=False, indent=2
            ),
            "plan_context": _plan_summary(plan),
            "critique": critique,
            "instructions": instructions or critique,
        }
    )

    try:
        result = await ask_json("plan_revise_section", variables, **kw)
    except Exception as e:
        logger.error("Revision of %s failed: %s", section_name, e)
        return {}

    # The model may wrap its answer in the section name, or return it bare.
    payload = result.get(section_name, result)
    if not isinstance(payload, dict) or not payload:
        logger.warning("Revision of %s returned no usable content", section_name)
        return {}

    try:
        # Validate through the section's own model so a malformed revision
        # cannot reach the plan.
        return type(section).model_validate(payload).model_dump(mode="json")
    except Exception as e:
        logger.warning(
            "Revised %s full validation failed: %s; attempting field-by-field merge",
            section_name,
            e,
        )
        try:
            current_dict = section.model_dump(mode="json")
            if isinstance(payload, dict):
                for k, v in payload.items():
                    if k in current_dict:
                        current_dict[k] = v
                return type(section).model_validate(current_dict).model_dump(mode="json")
        except Exception as e2:
            logger.error("Fallback validation of %s also failed: %s", section_name, e2)
        return {}


async def compose_reply(
    critique: str,
    sections_changed: tuple[str, ...],
    change_details: str,
    language: str,
    **kw: Any,
) -> str:
    """Write the marketer-facing reply, mirroring the language they wrote in."""
    try:
        result = await ask_json(
            "plan_compose_reply",
            {
                "critique": critique,
                "sections_changed": ", ".join(sections_changed) or "(none)",
                "change_details": change_details or "(no changes)",
                "language": language,
            },
            **kw,
        )
        reply = (result.get("reply") or "").strip()
    except Exception as e:
        logger.warning("Reply composition failed: %s", e)
        reply = ""

    if reply:
        return reply
    if sections_changed:
        return f"Updated the {', '.join(sections_changed)} section(s) based on your feedback."
    return "I did not change the plan. Could you tell me which part you would like revised?"
