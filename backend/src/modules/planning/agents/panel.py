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
from src.modules.ai_generation.services.llm_service import LLMService
from src.modules.planning.models.brief import PlanBrief
from src.modules.planning.prompts import register_planning_templates

logger = logging.getLogger(__name__)

register_planning_templates()

_SYSTEM_PROMPT = (
    "You are part of a senior marketing strategy panel. You produce rigorous, "
    "specific, decision-ready work in your own discipline and return it as JSON."
)

# Groq's free tier rate-limits aggressively; five simultaneous 70B calls trip it.
_PANEL_CONCURRENCY = 3


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
    if llm is None:
        try:
            from src.modules.research.services.llm_router import LLMRouterService
            router = LLMRouterService()
            result = await router.generate_json(system_prompt=_SYSTEM_PROMPT, user_prompt=prompt)
            if result:
                return result
        except Exception as e:
            logger.warning("LLMRouterService call failed in panel specialist (%s), using default LLMService", e)

    service = llm or LLMService(model=LLMService.DEFAULT_MODEL)
    return await service.generate_json(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=prompt,
        trace_id=trace_id,
        workflow_id=workflow_id,
        prompt_name=template_name,
        raise_on_error=True,
    )


def _extract_keywords(text: str, max_words: int = 5) -> str:
    """Extract core niche keywords from a long user prompt.

    Strips common filler phrases (drive, registrations, create, campaign,
    upcoming, seminar, for, the, etc.) so queries stay focused and effective.
    """
    import re
    filler = {
        "drive", "create", "generate", "registrations", "campaign", "make",
        "upcoming", "the", "for", "our", "a", "an", "at", "in", "of", "on",
        "with", "and", "to", "from", "by", "is", "are", "was", "be", "do",
        "want", "write", "build", "run", "launch", "how", "we", "us", "i",
        "please", "my", "seminar", "workshop", "event", "course", "class",
        "register", "registration", "join", "promotion",
    }
    words = re.findall(r"[A-Za-z0-9]+", text)
    keywords = [w for w in words if w.lower() not in filler and len(w) > 2]
    return " ".join(keywords[:max_words])


def _single_search(query: str, limit: int = 4) -> list[dict]:
    """Execute one DuckDuckGo search, returning up to `limit` results or []."""
    try:
        from src.services.search import GuestSearchService
        results = GuestSearchService().search(query)[:limit]
        return results
    except Exception as e:
        logger.warning("Search failed for %r: %s", query, e)
        return []


async def _parallel_research(base_query: str, limit_per_query: int = 4) -> str:
    """Run 3 tiered queries in parallel and merge unique results.

    Strategy:
      Q1  – specific niche (e.g. 'AI Seminar competitors alternatives')
      Q2  – broader category (e.g. 'AI online courses bootcamps')
      Q3  – general alternatives (e.g. 'AI training workshops alternatives')

    All three fire simultaneously; total wait = max(Q1, Q2, Q3) ≈ 3-4s.
    """
    niche = _extract_keywords(base_query)
    if not niche:
        niche = base_query[:40]

    # Pick generic category word (last meaningful word in niche)
    category = niche.split()[-1] if niche.split() else niche

    queries = [
        f"{niche} competitors alternatives",
        f"{niche} online courses bootcamps",
        f"{category} training workshops alternatives",
    ]

    raw_results = await asyncio.gather(
        *[asyncio.to_thread(_single_search, q, limit_per_query) for q in queries]
    )

    # Merge and deduplicate by URL
    seen_urls: set[str] = set()
    merged: list[dict] = []
    for result_list in raw_results:
        for r in result_list:
            url = r.get("href", "")
            if url not in seen_urls:
                seen_urls.add(url)
                merged.append(r)

    if not merged:
        logger.warning("All parallel searches returned empty for base_query=%r", base_query)
        return ""

    return "\n".join(
        f"- {r.get('title', '')} ({r.get('href', '')})\n  {r.get('body', '')}"
        for r in merged
    )


# ── Specialists ──────────────────────────────────────────────────────────


async def audience_research(brief: PlanBrief, **kw: Any) -> dict[str, Any]:
    """Personas, the primary objective, and SMART goals."""
    base = f"{brief.user_goal or brief.event_name} target audience demographics"
    research = await _parallel_research(base)
    return await ask_json("plan_audience_research", brief.as_prompt_vars(research), **kw)


async def positioning(brief: PlanBrief, **kw: Any) -> dict[str, Any]:
    """Positioning statement, USP, messaging pillars, tone, objections."""
    return await ask_json("plan_positioning", brief.as_prompt_vars(), **kw)


async def channel_planner(brief: PlanBrief, **kw: Any) -> dict[str, Any]:
    """Platform mix, campaign phases, and the dated content calendar."""
    base = f"{brief.user_goal or brief.event_name} social media marketing"
    research = await _parallel_research(base)
    return await ask_json("plan_channel", brief.as_prompt_vars(research), **kw)


async def measurement(brief: PlanBrief, **kw: Any) -> dict[str, Any]:
    """Funnel KPIs, targets, tracking plan, definition of success."""
    return await ask_json("plan_measurement", brief.as_prompt_vars(), **kw)


async def _parallel_competitor_research(base_query: str, limit_per_query: int = 4) -> str:
    """Run 4 specialized competitor discovery queries in parallel.

    Queries cover:
    1. Direct Competitors & Market Alternatives
    2. Pricing Models, Customer Reviews & Gaps
    3. Content & Social Media Strategy Benchmarks
    4. Search Intent & Positioning Vectors
    """
    niche = _extract_keywords(base_query)
    if not niche:
        niche = base_query[:40]

    category = niche.split()[-1] if niche.split() else niche

    queries = [
        f"{niche} top competitor platforms alternative courses",
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
            if url not in seen_urls:
                seen_urls.add(url)
                merged.append(r)

    if not merged:
        logger.warning("All parallel competitor searches returned empty for base_query=%r", base_query)
        return ""

    return "\n".join(
        f"- {r.get('title', '')} ({r.get('href', '')})\n  {r.get('body', '')}"
        for r in merged
    )


async def competitive(brief: PlanBrief, **kw: Any) -> dict[str, Any]:
    """Competitor landscape and the differentiation angle."""
    base = f"{brief.user_goal or brief.event_name} competitors alternative courses"
    research = await _parallel_competitor_research(base)
    return await ask_json("plan_competitive", brief.as_prompt_vars(research), **kw)


SPECIALISTS = {
    "audience_research": audience_research,
    "positioning": positioning,
    "channel_plan": channel_planner,
    "measurement": measurement,
    "competitive": competitive,
}


async def run_panel(brief: PlanBrief, **kw: Any) -> dict[str, dict[str, Any]]:
    """Run all five specialists concurrently, capped for rate limits.

    A specialist that fails yields an empty section rather than sinking the
    whole panel — the marketer can refine a thin section, but cannot refine a
    plan that never arrived.
    """
    semaphore = asyncio.Semaphore(_PANEL_CONCURRENCY)

    async def _run(name: str, fn) -> tuple[str, dict[str, Any]]:
        async with semaphore:
            try:
                res = await fn(brief, **kw)
                if not res:
                    raise RuntimeError(f"Specialist {name} returned empty result")
                return name, res
            except Exception as e:
                logger.error("Panel specialist %s failed: %s", name, e)
                raise RuntimeError(f"Specialist '{name}' failed due to LLM/API error: {e}") from e

    results = await asyncio.gather(*(_run(n, f) for n, f in SPECIALISTS.items()))
    return dict(results)
