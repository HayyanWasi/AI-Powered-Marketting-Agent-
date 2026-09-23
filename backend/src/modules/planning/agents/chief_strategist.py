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
from src.modules.planning.models.campaign_plan import (
    CampaignPlan,
    ChiefReconciliation,
    PlanStatus,
)

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
    """Assemble the plan deterministically, then apply the chief's deltas.

    The five specialist sections are the source of truth and are assembled in
    code — the chief never re-emits them. Its compact reconciliation only
    supplies a title, an executive summary, and (rarely) a few prose
    corrections. If the reconciliation call fails or validates to nothing, the
    deterministically assembled plan is returned unchanged.
    """
    base = assemble(
        panel,
        title=brief.user_goal or "Campaign Plan",
        executive_summary=brief.user_goal or "",
    )

    variables = _chief_variables(brief, panel)
    try:
        recon = ChiefReconciliation.model_validate(
            await ask_json("plan_chief_strategist", variables, **kw)
        )
    except Exception as e:
        logger.warning(
            "Chief reconciliation failed (%s); using deterministic assembly", e
        )
        return base

    return _apply_reconciliation(base, recon)


def _chief_variables(brief: PlanBrief, panel: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Compact chief context: minimal identity + the five completed sections."""
    variables = brief.as_prompt_vars()
    variables.update(
        {
            key: json.dumps(
                panel.get(key) or {}, ensure_ascii=False, separators=(",", ":")
            )
            for key in (
                "audience_research",
                "positioning",
                "channel_plan",
                "measurement",
                "competitive",
            )
        }
    )
    return variables


def _apply_reconciliation(base: CampaignPlan, recon: ChiefReconciliation) -> CampaignPlan:
    """Overlay the chief's title/summary and allowlisted prose deltas.

    Every specialist section is preserved: only the named prose fields may
    change, and only when the chief supplied a non-empty value. Scheduler-owned
    calendar identity/timing, KPIs, personas, and list contents are untouched.
    """
    updates: dict[str, Any] = {
        "title": recon.title or base.title,
        "executive_summary": recon.executive_summary or base.executive_summary,
    }

    adj = recon.adjustments
    core_updates: dict[str, str] = {}
    if adj.unique_selling_proposition:
        core_updates["unique_selling_proposition"] = adj.unique_selling_proposition
    if adj.tone_of_voice:
        core_updates["tone_of_voice"] = adj.tone_of_voice
    if core_updates:
        updates["core_strategy"] = base.core_strategy.model_copy(update=core_updates)

    if adj.differentiation_angle:
        updates["competitive"] = base.competitive.model_copy(
            update={"differentiation_angle": adj.differentiation_angle}
        )

    return base.model_copy(update=updates)
