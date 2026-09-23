"""The specialist panel that drafts a campaign plan.

Each specialist is a plain async callable rather than a ``BaseAgent`` subclass:
``BaseAgent.execute`` is synchronous, and the whole point of the panel is that
the five run concurrently. They are composed by the ``campaign_plan`` graph.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.config.prompts import render_template
from src.models.llm import LLMRequest
from src.modules.planning.models.brief import PlanBrief
from src.modules.planning.models.campaign_plan import (
    ChannelPlan,
    ChiefReconciliation,
    Competitive,
    CoreStrategy,
    Measurement,
)
from src.modules.planning.prompts import register_planning_templates
from src.services.llm_service import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    LLMService,
    parse_json_object,
)

logger = logging.getLogger(__name__)

register_planning_templates()

_SYSTEM_PROMPT = (
    "You are part of a senior marketing strategy panel. You produce rigorous, "
    "specific, decision-ready work in your own discipline and return it as JSON."
)

# ── Provider-specific planning execution policy (single truthful source) ──
# A single local Ollama GPU can only do one heavy generation at a time; hosted
# providers tolerate the intended fan-out of two. These are the ONLY knobs that
# decide live specialist concurrency — both the LangGraph path and run_panel
# read them, so there is no second, divergent "cap" hiding elsewhere.
_OLLAMA_SPECIALIST_CONCURRENCY = 1
_REMOTE_SPECIALIST_CONCURRENCY = 2

# Heavy planning generations legitimately run ~90s+ on the local model; a single
# request timeout well above that is applied to Ollama planning calls only.
_OLLAMA_PLANNING_TIMEOUT_SECONDS = 180.0


def planning_specialist_concurrency(llm: LLMService | None = None) -> int:
    """Max specialists that may hit the provider at once, by active provider."""
    service = llm or LLMService()
    return (
        _OLLAMA_SPECIALIST_CONCURRENCY
        if service.is_local_ollama()
        else _REMOTE_SPECIALIST_CONCURRENCY
    )


def planning_timeout_seconds(llm: LLMService | None = None) -> float | None:
    """Per-request planning timeout: 180s whenever the lane has an Ollama leg.

    The override is only consumed by the Ollama provider inside the service, so
    a lane with an Ollama primary and remote fallback still gives its Ollama
    call the long timeout while the remote legs keep their own defaults.
    """
    service = llm or LLMService()
    return _OLLAMA_PLANNING_TIMEOUT_SECONDS if service.has_ollama_provider() else None


_SPECIALIST_SCHEMAS = {
    "plan_audience_research": CoreStrategy,
    "plan_positioning": CoreStrategy,
    "plan_channel": ChannelPlan,
    "plan_channel_repair": ChannelPlan,
    "plan_measurement": Measurement,
    "plan_competitive": Competitive,
    "plan_chief_strategist": ChiefReconciliation,
}

_OUTPUT_TOKEN_BUDGETS = {
    "plan_audience_research": 1800,
    "plan_positioning": 1600,
    "plan_channel": 2400,
    "plan_channel_repair": 2400,
    "plan_measurement": 1400,
    "plan_competitive": 2200,
    # Delta-only reconciliation: a title, a short summary, notes, and at most a
    # few prose adjustments — never a re-emitted plan.
    "plan_chief_strategist": 700,
}


async def ask_json(
    template_name: str,
    variables: dict[str, str],
    *,
    trace_id: str | None = None,
    workflow_id: str | None = None,
    llm: LLMService | None = None,
) -> dict[str, Any]:
    """Render a template and get JSON back from the reasoning model."""
    prompt = render_template(template_name, variables)

    service = llm or LLMService()
    schema = _SPECIALIST_SCHEMAS.get(template_name)
    response = await asyncio.to_thread(
        service.generate,
        LLMRequest(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=prompt,
            prompt_name=template_name,
            json_mode=True,
            output_schema=schema,
            max_tokens=_OUTPUT_TOKEN_BUDGETS.get(template_name, DEFAULT_MAX_OUTPUT_TOKENS),
            timeout=planning_timeout_seconds(service),
        ),
    )
    payload = parse_json_object(response.text)
    schema = _SPECIALIST_SCHEMAS.get(template_name)
    if schema is not None:
        schema.model_validate(payload)
    return payload


def _extract_keywords(text: str, max_words: int = 5) -> str:
    """Extract core niche keywords from a long user prompt.

    Strips common filler phrases (drive, registrations, create, campaign,
    upcoming, seminar, for, the, etc.) so queries stay focused and effective.
    """
    import re

    filler = {
        "drive",
        "create",
        "generate",
        "registrations",
        "campaign",
        "make",
        "upcoming",
        "the",
        "for",
        "our",
        "a",
        "an",
        "at",
        "in",
        "of",
        "on",
        "with",
        "and",
        "to",
        "from",
        "by",
        "is",
        "are",
        "was",
        "be",
        "do",
        "want",
        "write",
        "build",
        "run",
        "launch",
        "how",
        "we",
        "us",
        "i",
        "please",
        "my",
        "seminar",
        "workshop",
        "event",
        "course",
        "class",
        "register",
        "registration",
        "join",
        "promotion",
    }
    words = re.findall(r"[A-Za-z0-9]+", text)
    keywords = [w for w in words if w.lower() not in filler and len(w) > 2]
    return " ".join(keywords[:max_words])


def _single_search(query: str, limit: int = 4) -> list[dict]:
    """Execute one DuckDuckGo search, returning up to `limit` results or []."""
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=limit))
    except Exception as e:
        logger.error("DDGS search error for query '%s': %s", query, e)
        return []


def _build_niche(brief: PlanBrief) -> str:
    parts = []
    if brief.campaign_name:
        parts.append(brief.campaign_name)
    if brief.company_name:
        parts.append(brief.company_name)
    if brief.category:
        parts.append(brief.category)
    if not parts and brief.user_goal:
        parts.append(_extract_keywords(brief.user_goal))
    return " ".join(parts)[:40]


def _format_research(merged: list[dict], max_results: int = 10, body_chars: int = 320) -> str:
    """Render merged, de-duplicated search results compactly.

    Preserves each result's title, source URL, and evidence snippet, but bounds
    the raw body and caps the number of results so a long scrape does not blow
    up the specialist's input. No summarisation or invention — just truncation.
    """
    lines = []
    for r in merged[:max_results]:
        title = (r.get("title") or "").strip()
        href = (r.get("href") or "").strip()
        body = " ".join((r.get("body") or "").split())[:body_chars]
        lines.append(f"- {title} ({href})\n  {body}")
    return "\n".join(lines)


async def _parallel_research(brief: PlanBrief, limit_per_query: int = 4) -> str:
    """Run 3 tiered queries in parallel and merge unique results."""
    niche = _build_niche(brief) or "campaign"
    category = brief.category or niche.split()[-1] if niche.split() else niche
    target = brief.target_audience or "target audience"

    if brief.campaign_type == "app_launch":
        queries = [
            f"{niche} app competitors alternatives",
            f"{niche} app market trends {category}".strip(),
            f"{category} app user acquisition {target}".strip(),
        ]
    else:
        queries = [
            f"{niche} competitors alternatives",
            f"{niche} {category} best practices",
            f"{category} marketing to {target}",
        ]

    raw_results = await asyncio.gather(
        *[asyncio.to_thread(_single_search, q, limit_per_query) for q in queries]
    )

    seen_urls: set[str] = set()
    merged: list[dict] = []
    for result_list in raw_results:
        for r in result_list:
            url = r.get("href", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                merged.append(r)

    if not merged:
        logger.warning("All parallel searches returned empty for niche=%r", niche)
        return "RESEARCH FAILED: No web evidence could be retrieved. Proceed based on your internal knowledge."

    return _format_research(merged)


# ── Specialists ──────────────────────────────────────────────────────────


async def audience_research(brief: PlanBrief, **kw: Any) -> dict[str, Any]:
    """Personas, the primary objective, and SMART goals."""
    research = "" if brief.has_usable_research() else await _parallel_research(brief)
    return await ask_json("plan_audience_research", brief.to_template_vars(research), **kw)


async def positioning(brief: PlanBrief, **kw: Any) -> dict[str, Any]:
    """Positioning statement, USP, messaging pillars, tone, objections."""
    return await ask_json("plan_positioning", brief.to_template_vars(), **kw)


def _resolve_calendar_slot_ids(payload: dict[str, Any], brief: PlanBrief) -> dict[str, Any]:
    """Translate the planner's numbered slot references back into real slot IDs.

    The planner is asked to reference each fixed slot by its position in the
    numbered FIXED LINKEDIN SCHEDULE list rather than copying its 36-character
    slot_id verbatim — a plain number is far less likely to be garbled than a
    UUID. This maps that number back to the canonical slot_id before the plan
    reaches ``normalize_calendar_slots``, which still validates identity and
    content strictly and is left untouched.
    """
    if not brief.schedule_plan or not isinstance(payload.get("calendar_slots"), list):
        return payload
    slots = brief.schedule_plan.slots
    for entry in payload["calendar_slots"]:
        if not isinstance(entry, dict):
            continue
        ref = str(entry.get("slot_id", "")).strip()
        if ref.isdigit():
            index = int(ref) - 1
            if 0 <= index < len(slots):
                entry["slot_id"] = str(slots[index].slot_id)
    return payload


def _validate_channel_payload(
    payload_resolved: dict[str, Any], brief: PlanBrief, raw_payload: dict[str, Any]
) -> str | None:
    from src.modules.linkedin.scheduling.slot_validation import (
        ScheduleSlotMismatchError,
        normalize_calendar_slots,
    )
    from src.modules.planning.models.campaign_plan import ChannelPlan

    if not brief.schedule_plan:
        return None

    try:
        parsed = ChannelPlan.model_validate(payload_resolved)
    except Exception:
        return "JSON structure or types were invalid."

    req_count = len(brief.schedule_plan.slots)
    ret_count = len(parsed.calendar_slots)

    if ret_count < req_count:
        return f"You returned {ret_count} calendar slots but exactly {req_count} are required.\nReturn all slot ordinals exactly once: {','.join(str(i) for i in range(1, req_count+1))}.\nDo not change schedule identity/timing."
    if ret_count > req_count:
        return f"You returned extra schedule slots.\nReturn exactly the canonical ordinals: {','.join(str(i) for i in range(1, req_count+1))}."

    seen = set()
    for s in raw_payload.get("calendar_slots", []):
        if isinstance(s, dict):
            ref = str(s.get("slot_id", "")).strip()
            if ref in seen:
                return f"Ordinal {ref} was duplicated.\nReturn every required ordinal exactly once."
            seen.add(ref)

    try:
        normalize_calendar_slots(parsed.calendar_slots, brief.schedule_plan)
    except ScheduleSlotMismatchError as exc:
        msg = str(exc)
        if "unknown schedule slot" in msg:
            return f"You returned unknown or invalid slot ordinals.\nReturn exactly the canonical ordinals: {','.join(str(i) for i in range(1, req_count+1))}."
        return f"A slot changed an immutable field ({msg}).\nUse the canonical fixed schedule values exactly."
    return None


async def channel_planner(brief: PlanBrief, **kw: Any) -> dict[str, Any]:
    """Platform mix, campaign phases, and the dated content calendar."""
    import copy

    research = "" if brief.has_usable_research() else await _parallel_research(brief)

    payload = await ask_json("plan_channel", brief.to_template_vars(research), **kw)
    return _resolve_calendar_slot_ids(payload, brief)
    raw_payload_copy = copy.deepcopy(payload)
    payload_resolved = _resolve_calendar_slot_ids(payload, brief)

    error_msg = _validate_channel_payload(payload_resolved, brief, raw_payload_copy)
    if not error_msg:
        return payload_resolved

    logger.warning("channel_planner invalid output, running repair: %s", error_msg)

    repair_vars = brief.to_template_vars(research)
    repair_vars["validation_error"] = error_msg

    repaired_payload = await ask_json("plan_channel_repair", repair_vars, **kw)
    repaired_raw_copy = copy.deepcopy(repaired_payload)
    repaired_resolved = _resolve_calendar_slot_ids(repaired_payload, brief)

    error_msg2 = _validate_channel_payload(repaired_resolved, brief, repaired_raw_copy)
    if error_msg2:
        logger.error("channel_planner repair failed: %s", error_msg2)
        # Truthful failure, propagates up
        raise ValueError(f"Channel planner failed validation after repair: {error_msg2}")

    return repaired_resolved


async def measurement(brief: PlanBrief, **kw: Any) -> dict[str, Any]:
    """Funnel KPIs, targets, tracking plan, definition of success."""
    return await ask_json("plan_measurement", brief.to_template_vars(), **kw)


async def _parallel_competitor_research(brief: PlanBrief, limit_per_query: int = 4) -> str:
    """Run specialized competitor discovery queries in parallel."""
    niche = _build_niche(brief) or "campaign"
    category = brief.category or niche.split()[-1] if niche.split() else niche

    if brief.campaign_type == "app_launch":
        queries = [
            f"{niche} top competing apps services alternatives",
            f"{niche} app pricing features reviews complaints",
            f"{niche} mobile app growth marketing channels",
            f"{category} app alternatives market gap",
        ]
    else:
        queries = [
            f"{niche} top competitor platforms alternatives",
            f"{niche} competitor pricing reviews complaints gaps",
            f"{niche} social media content strategy marketing",
            f"{category} alternatives vs comparison market gap",
        ]

    raw_results = await asyncio.gather(
        *[asyncio.to_thread(_single_search, q, limit_per_query) for q in queries]
    )

    seen_urls: set[str] = set()
    merged: list[dict] = []
    for result_list in raw_results:
        for r in result_list:
            url = r.get("href", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                merged.append(r)

    if not merged:
        logger.warning("All parallel competitor searches returned empty for niche=%r", niche)
        return "RESEARCH FAILED: No competitor data could be retrieved. Proceed based on your internal knowledge."

    return _format_research(merged)


async def competitive(brief: PlanBrief, **kw: Any) -> dict[str, Any]:
    """Competitor landscape and the differentiation angle."""
    research = "" if brief.has_usable_research() else await _parallel_competitor_research(brief)
    return await ask_json("plan_competitive", brief.to_template_vars(research), **kw)


SPECIALISTS = {
    "audience_research": audience_research,
    "positioning": positioning,
    "channel_plan": channel_planner,
    "measurement": measurement,
    "competitive": competitive,
}

# Lighter specialist set for Quick tier — skips the 4-search competitive scan
QUICK_SPECIALISTS = {
    "audience_research": audience_research,
    "positioning": positioning,
    "channel_plan": channel_planner,
    "measurement": measurement,
}


async def run_panel(brief: PlanBrief, **kw: Any) -> dict[str, dict[str, Any]]:
    """Run all five specialists concurrently, capped for rate limits.

    A specialist that fails yields an empty section rather than sinking the
    whole panel — the marketer can refine a thin section, but cannot refine a
    plan that never arrived.
    """
    semaphore = asyncio.Semaphore(planning_specialist_concurrency(kw.get("llm")))

    async def _run(name: str, fn) -> tuple[str, dict[str, Any]]:
        async with semaphore:
            try:
                res = await fn(brief, **kw)
                if not res:
                    raise RuntimeError(f"Specialist {name} returned empty result")
                return name, res
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Panel specialist %s failed: %s", name, e)
                raise RuntimeError(f"Specialist '{name}' failed due to LLM/API error: {e}") from e

    tasks = [asyncio.create_task(_run(n, f)) for n, f in SPECIALISTS.items()]
    try:
        results = await asyncio.gather(*tasks)
    except Exception:
        for t in tasks:
            if not t.done():
                t.cancel()
        raise
    return dict(results)
