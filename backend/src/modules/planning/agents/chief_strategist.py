"""Chief strategist — reconciles the panel's five sections into one plan.

The panel already returns section-shaped JSON, so assembly does not *need* an
LLM. The synthesis call exists to resolve cross-section contradictions (a
calendar slot citing a pillar positioning never defined, KPI targets that
disagree with the SMART goals). If it fails, deterministic assembly still
produces a valid plan.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.modules.planning.agents.panel import ask_json
from src.modules.planning.models.brief import PlanBrief
from src.modules.planning.models.campaign_plan import CampaignPlan, PlanStatus

logger = logging.getLogger(__name__)


def assemble(
    panel: dict[str, dict[str, Any]],
    *,
    title: str = "",
    executive_summary: str = "",
) -> CampaignPlan:
    """Build a CampaignPlan from raw panel sections without an LLM.

    ``core_strategy`` is the merge of two specialists: audience_research owns
    the objective/goals/personas, positioning owns everything else.
    """
    audience = panel.get("audience_research") or {}
    position = panel.get("positioning") or {}

    document = {
        "title": title,
        "executive_summary": executive_summary,
        "core_strategy": {**audience, **position},
        "channel_plan": panel.get("channel_plan") or {},
        "measurement": panel.get("measurement") or {},
        "competitive": panel.get("competitive") or {},
        "status": PlanStatus.DRAFT.value,
    }
    return CampaignPlan.model_validate(document)


async def synthesize(
    brief: PlanBrief,
    panel: dict[str, dict[str, Any]],
    **kw: Any,
) -> CampaignPlan:
    """Reconcile the panel's sections into a coherent plan.

    Falls back to deterministic assembly when the synthesis call fails or
    returns something that will not validate.
    """
    variables = brief.as_prompt_vars()
    variables.update(
        {
            key: json.dumps(panel.get(key) or {}, ensure_ascii=False, indent=2)
            for key in ("audience_research", "positioning", "channel_plan", "measurement", "competitive")
        }
    )

    try:
        document = await ask_json("plan_chief_strategist", variables, **kw)
        document["status"] = PlanStatus.DRAFT.value
        plan = CampaignPlan.model_validate(document)
    except Exception as e:
        logger.warning("Chief strategist synthesis failed (%s); assembling directly", e)
        return assemble(panel)

    # A synthesis that dropped a section is worse than no synthesis for that
    # section — backfill from the specialist's own output.
    fallback = assemble(panel, title=plan.title, executive_summary=plan.executive_summary)
    patches = {
        name: getattr(fallback, name)
        for name in ("core_strategy", "channel_plan", "measurement", "competitive")
        if _is_empty(getattr(plan, name)) and not _is_empty(getattr(fallback, name))
    }
    if patches:
        logger.info("Backfilled synthesized sections from panel: %s", ", ".join(patches))
        plan = plan.model_copy(update=patches)
    return plan


def _is_empty(section: Any) -> bool:
    """True when a section model carries no content at all."""
    return not any(section.model_dump(mode="json").values())
