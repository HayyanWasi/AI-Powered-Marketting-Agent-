"""LinkedIn Post Generator — Generates research-grounded post copy per CalendarSlot."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from src.models.brand_context import BrandContext
from src.modules.linkedin.generators.content_context import ContentContextBuilder
from src.modules.linkedin.generators.local_llm_gate import (
    LINKEDIN_LOCAL_OLLAMA_TIMEOUT_SECONDS,
    linkedin_local_ollama_slot,
)
from src.modules.linkedin.models import ContentContext, LinkedInPost, PostStatus
from src.modules.linkedin.scheduling.slot_validation import normalize_calendar_slots
from src.modules.planning.models.campaign_plan import CampaignPlan
from src.modules.research.models.research_brief import ResearchBrief
from src.modules.research.services.llm_router import LLMRouterService

logger = logging.getLogger(__name__)

MAX_PROMPT_CHARS = 250000
PROMPT_BUDGET_MARGIN = 500
OPTIONAL_FIELD_TRUNCATION_MARKER = "... [FIELD TRUNCATED]"

# Plain-language writing rule appended to the LinkedIn post-generation
# instructions. Scope is deliberately narrow: it only shapes the wording of
# generated post copy. It does not touch planning, scheduling, providers,
# timeout, persistence, the JSON output contract, or campaign facts/CTA.
PLAIN_LANGUAGE_STYLE_RULE = (
    "### WRITING STYLE\n"
    "- Write in plain, natural English that a normal reader understands immediately.\n"
    "- Do NOT use em dashes (—) or en dashes (–) anywhere in the copy. Use short "
    "sentences, commas, or full stops instead of dashes as sentence separators.\n"
    "- Normal grammatical hyphens are allowed only inside genuine compound words "
    "(for example real-time, well-known).\n"
    "- Avoid marketing or business jargon such as leverage, synergy, unlock value, "
    "game-changing, cutting-edge, seamless ecosystem, best-in-class, revolutionize.\n"
    "- Prefer simple, common words over buzzwords. Do not remove industry terms that "
    "are genuinely needed for accuracy.\n"
    "- Keep the brand voice, campaign facts, CTA, and post structure exactly as required."
)

# Em dash (—, U+2014), en dash (–, U+2013), and horizontal bar (―, U+2015),
# together with the horizontal whitespace immediately around them. ASCII hyphens
# ("-", used in real-time / well-known) are intentionally NOT matched.
_DASH_SEPARATOR_RE = re.compile(r"[ \t]*[—–―]+[ \t]*")


def _to_plain_style(text: str) -> str:
    """Remove em/en dashes from generated copy without touching real hyphens.

    Em dashes (—) and en dashes (–) used as sentence separators are replaced with
    a comma and a space, so the copy reads as plain English. ASCII hyphens inside
    genuine compound words (real-time, well-known) are preserved. Line structure
    is kept: a dash that sat at the start or end of a line does not leave a
    dangling comma.
    """
    if not text:
        return text
    cleaned = _DASH_SEPARATOR_RE.sub(", ", text)
    cleaned = re.sub(r",[ \t]*\n", ",\n", cleaned)  # no trailing space after a moved comma
    cleaned = re.sub(r"(^|\n)[ \t]*,[ \t]*", r"\1", cleaned)  # drop a comma that now begins a line
    cleaned = re.sub(r",[ \t]*,", ",", cleaned)  # collapse doubled commas
    return cleaned.strip()


class LinkedInPostGenerator:
    """Generates research-anchored LinkedIn feed posts for approved campaign slots."""

    def __init__(self, llm_router: LLMRouterService | None = None) -> None:
        self.llm = llm_router or LLMRouterService()

    @staticmethod
    def _parse_scheduled_at(
        slot_date: str, post_time_str: str = "10:00 AM", tz_name: str = "Asia/Karachi"
    ) -> datetime:
        """Convert a slot date string + wall-clock posting time → UTC datetime.

        Args:
            slot_date: ISO date string from CalendarSlot (e.g. '2026-09-10').
            post_time_str: Human-readable 12h time, e.g. '10:00 AM' or '04:00 PM'.
            tz_name: IANA timezone name for the posting account.

        Returns:
            UTC-aware datetime for the scheduled post publication.
        """
        tz = ZoneInfo(tz_name)

        # Parse the slot date
        local_date: date | None = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y", "%d %B %Y"):
            try:
                local_date = datetime.strptime(slot_date, fmt).date()
                break
            except (ValueError, TypeError):
                continue

        if local_date is None:
            local_date = date.today()

        # Parse the posting time (12h format with AM/PM, fallback to 10:00 AM)
        local_time = None
        for time_fmt in ("%I:%M %p", "%H:%M"):
            try:
                local_time = datetime.strptime(post_time_str.strip().upper(), time_fmt).time()
                break
            except (ValueError, AttributeError):
                continue

        if local_time is None:
            local_time = time(10, 0)  # Default 10:00 AM

        # Combine and convert to UTC
        local_dt = datetime.combine(local_date, local_time, tzinfo=tz)
        return local_dt.astimezone(UTC)

    @staticmethod
    def _next_workday(d: date) -> date:
        """Return the next workday (Mon–Fri) after the given date.

        Used to resolve date collisions — ensures no two posts from the
        same campaign land on the same calendar day.
        """
        next_d = d + timedelta(days=1)
        # Skip Saturday (5) and Sunday (6)
        while next_d.weekday() >= 5:
            next_d += timedelta(days=1)
        return next_d

    @staticmethod
    def _format_field(label: str, value: object, *, prefix: str = "") -> str:
        rendered = str(value).strip() if value is not None else ""
        return f"{prefix}{label}: {rendered or '(not specified)'}"

    @staticmethod
    def _append_optional_fields(
        prompt_parts: list[str],
        fields: list[tuple[str, object]],
        available_chars: int,
        *,
        prefix: str = "",
    ) -> int:
        """Append complete named fields, truncating only an optional field value."""
        for label, value in fields:
            rendered = str(value).strip() if value is not None else ""
            if not rendered:
                continue

            # Every optional line follows either its section heading or a prior line.
            separator_cost = 1
            full_line = f"{prefix}{label}: {rendered}"
            if len(full_line) + separator_cost <= available_chars:
                prompt_parts.append(full_line)
                available_chars -= len(full_line) + separator_cost
                continue

            fixed = f"{prefix}{label}: "
            value_budget = (
                available_chars
                - separator_cost
                - len(fixed)
                - len(OPTIONAL_FIELD_TRUNCATION_MARKER)
            )
            if value_budget > 0:
                prompt_parts.append(
                    f"{fixed}{rendered[:value_budget]}{OPTIONAL_FIELD_TRUNCATION_MARKER}"
                )
            return 0
        return available_chars

    @staticmethod
    def _build_slot_strategy_section(ctx: ContentContext) -> str:
        """Render the per-slot writing directives as a mandatory prompt section.

        Slot Theme and Messaging Pillar are always present (required fields) and
        are the primary drivers of per-post differentiation. format/angle and the
        slot-specific CTA are included when available. The wording explicitly
        marks these as mandatory content directives so the model writes to the
        specific slot strategy instead of restating the overall campaign, which
        is the observed cause of duplicate post content.
        """
        lines = ["### SLOT STRATEGY (MANDATORY CONTENT DIRECTIVE)"]
        lines.append(LinkedInPostGenerator._format_field("Slot Theme", ctx.theme, prefix="- "))
        lines.append(
            LinkedInPostGenerator._format_field(
                "Messaging Pillar", ctx.messaging_pillar, prefix="- "
            )
        )
        if (ctx.format_type or "").strip():
            lines.append(
                LinkedInPostGenerator._format_field("Format / Angle", ctx.format_type, prefix="- ")
            )
        if (ctx.differentiation_angle or "").strip():
            lines.append(
                LinkedInPostGenerator._format_field(
                    "Differentiation Angle", ctx.differentiation_angle, prefix="- "
                )
            )
        if (ctx.cta or "").strip():
            lines.append(
                LinkedInPostGenerator._format_field("Slot-Specific CTA", ctx.cta, prefix="- ")
            )
        lines.append(
            "The post MUST be specifically written around the assigned Slot Theme and "
            "Messaging Pillar above. These are mandatory content directives, not optional "
            "context. The hook, body angle, examples, and core message MUST reflect this "
            "specific slot strategy. Do NOT write a generic summary of the overall "
            "campaign. If two slots have different themes or pillars, their posts MUST "
            "communicate meaningfully different ideas. Keep all campaign facts, brand "
            "voice, and CTA accuracy unchanged; do not invent facts to force variety."
        )
        return "\n".join(lines)

    @classmethod
    def _build_user_prompt(cls, ctx: ContentContext, mandatory_instructions: str) -> str:
        """Build a bounded prompt without ever slicing authoritative fields."""
        if ctx.brand is None:
            raise ValueError("Brand context is required.")

        mandatory_brand_lines = [
            cls._format_field("Company", ctx.brand.company_name),
            cls._format_field("Brand tone / writing style", ctx.brand.brand_tone),
            cls._format_field("Brand guidelines", ctx.brand.guidelines),
            cls._format_field("Do not / guardrails", "; ".join(ctx.brand.negative_guardrails)),
        ]
        mandatory_brand_section = "\n".join(
            [
                "### BRAND IDENTITY",
                *mandatory_brand_lines,
                "Follow this company's tone and guardrails in EVERY section.",
                "Brand rules override conflicting campaign tone suggestions. Never invent missing brand facts.",
            ]
        )

        mandatory_campaign_lines = [
            cls._format_field(
                "Campaign Type", ctx.campaign_type or ctx.campaign_category, prefix="- "
            ),
            cls._format_field("Campaign Name", ctx.campaign_name or ctx.event_name, prefix="- "),
            cls._format_field("Objective", ctx.objective, prefix="- "),
            cls._format_field(
                "Value Proposition",
                ctx.value_proposition or ctx.outcome_value_proposition,
                prefix="- ",
            ),
            cls._format_field("Target Audience", ctx.target_audience, prefix="- "),
            cls._format_field(
                "CTA / Destination URL", ctx.cta_url or ctx.registration_link, prefix="- "
            ),
        ]

        details = ctx.product_facts or ctx.curriculum_breakdown
        if details:
            mandatory_campaign_lines.append(cls._format_field("Key Details", details, prefix="- "))

        is_event = ctx.campaign_type in (
            "webinar",
            "workshop",
            "conference",
            "in_person_event",
        ) or bool(ctx.venue or ctx.event_date)
        if is_event:
            for label, value in (
                ("Event Date", ctx.event_date),
                ("Venue", ctx.venue),
                ("Pricing", ctx.ticket_price),
            ):
                if value:
                    mandatory_campaign_lines.append(cls._format_field(label, value, prefix="- "))

        optional_campaign_fields: list[tuple[str, object]] = []
        if ctx.guest_name and ctx.guest_name.lower() not in (
            "none",
            "null",
            "no guest",
            "undefined",
            "n/a",
            "solo",
            "nobody",
        ):
            guest = ctx.guest_name
            if ctx.guest_position:
                guest += f" ({ctx.guest_position})"
            mandatory_campaign_lines.append(f"- Featured Guest/Speaker: {guest}")
            if ctx.guest_profile and ctx.guest_profile.get("professional_biography"):
                optional_campaign_fields.append(
                    ("Guest biography", ctx.guest_profile["professional_biography"])
                )
        elif is_event:
            mandatory_campaign_lines.append(
                "- Featured Guest/Speaker: None (Hosted directly by internal team. Do not invent any guest speaker!)"
            )

        mandatory_campaign_section = "### CAMPAIGN FACTS\n" + "\n".join(mandatory_campaign_lines)

        # Slot-specific writing directives. These are the primary driver of
        # per-post differentiation: without them every slot receives the same
        # campaign facts and the model produces the same generic campaign post.
        # They are placed in the MANDATORY prompt body (never budget-trimmed) and
        # explicitly framed as content directives rather than optional context.
        mandatory_slot_strategy_section = cls._build_slot_strategy_section(ctx)

        strategy_heading = "### CAMPAIGN STRATEGY"
        research_heading = "### RESEARCH EVIDENCE"
        strategy_omitted = (
            "Optional strategy context omitted to preserve authoritative brand and campaign facts."
        )
        research_omitted = (
            "Research evidence omitted or unavailable; do not invent supporting facts."
        )
        base_prompt = "\n\n".join(
            (
                mandatory_brand_section,
                mandatory_campaign_section,
                mandatory_slot_strategy_section,
                f"{strategy_heading}\n{strategy_omitted}",
                f"{research_heading}\n{research_omitted}",
                mandatory_instructions,
            )
        )
        hard_limit = MAX_PROMPT_CHARS - PROMPT_BUDGET_MARGIN
        if len(base_prompt) > hard_limit:
            raise RuntimeError(
                "Required campaign and brand context exceeds the supported LinkedIn generation context."
            )

        remaining = hard_limit - len(base_prompt)

        # Preserve optional brand identity ahead of strategy and research. Long
        # examples/history are deliberately last within this group.
        optional_brand_lines: list[str] = []
        remaining = cls._append_optional_fields(
            optional_brand_lines,
            [
                ("Website", ctx.brand.website),
                ("Industry", ctx.brand.industry),
                ("Brand audience", ctx.brand.target_audience),
                ("Specializations", "; ".join(ctx.brand.specializations)),
                ("Personality traits", "; ".join(ctx.brand.personality_traits)),
                ("Company description", ctx.brand.description),
                ("Track record", ctx.brand.track_record),
                ("Sample voice", ctx.brand.sample_voice),
            ],
            remaining,
        )

        optional_campaign_lines: list[str] = []
        remaining = cls._append_optional_fields(
            optional_campaign_lines,
            optional_campaign_fields,
            remaining,
            prefix="- ",
        )

        # Slot Theme, Messaging Pillar, format/angle, and the slot CTA are now
        # emitted in the mandatory slot-strategy section above, so they are
        # intentionally NOT repeated here. This optional section only carries
        # supporting strategic context that may be trimmed under prompt budget.
        strategy_lines: list[str] = []
        remaining = cls._append_optional_fields(
            strategy_lines,
            [
                ("Positioning", ctx.positioning),
                ("Unique Selling Proposition (USP)", ctx.usp),
                ("Tone of Voice", ctx.tone_of_voice),
            ],
            remaining,
            prefix="- ",
        )

        research_lines: list[str] = []
        research_fields = [
            (
                f"[{fact.dimension.upper()}] Evidence",
                f"Claim: {fact.claim} | Quote: '{fact.quote}' (Source: {fact.source_url})",
            )
            for fact in ctx.researched_facts
        ]
        cls._append_optional_fields(
            research_lines,
            research_fields,
            remaining,
            prefix="- ",
        )

        brand_section = mandatory_brand_section
        if optional_brand_lines:
            brand_section += "\n" + "\n".join(optional_brand_lines)
        campaign_section = mandatory_campaign_section
        if optional_campaign_lines:
            campaign_section += "\n" + "\n".join(optional_campaign_lines)
        strategy_section = (
            strategy_heading
            + "\n"
            + ("\n".join(strategy_lines) if strategy_lines else strategy_omitted)
        )
        research_section = (
            research_heading
            + "\n"
            + ("\n".join(research_lines) if research_lines else research_omitted)
        )
        prompt = "\n\n".join(
            (
                brand_section,
                campaign_section,
                mandatory_slot_strategy_section,
                strategy_section,
                research_section,
                mandatory_instructions,
            )
        )
        if len(prompt) > hard_limit:
            raise RuntimeError("LinkedIn prompt budgeting exceeded its supported context.")
        return prompt

    async def generate_all_posts(
        self,
        campaign_id: UUID,
        plan: CampaignPlan,
        brief: ResearchBrief | None = None,
        event_name: str = "",
        event_date: str = "",
        venue: str = "",
        registration_link: str = "",
        target_audience: str = "",
        curriculum_breakdown: str = "",
        ticket_price: str = "",
        guest_name: str | None = None,
        guest_title: str | None = None,
        guest_profile: dict | None = None,
        post_time_str: str = "10:00 AM",
        timezone_name: str = "Asia/Karachi",
        brand: BrandContext | None = None,
        campaign_type: str = "",
        campaign_name: str = "",
        objective: str = "",
        value_proposition: str = "",
        cta_url: str = "",
        campaign_category: str = "",
        outcome_value_proposition: str = "",
        product_facts: str = "",
        on_post_started: Callable[[int, str, int], Awaitable[None]] | None = None,
        on_post_completed: Callable[[int, str, int, LinkedInPost], Awaitable[None]] | None = None,
    ) -> list[LinkedInPost]:
        """Generate a list of LinkedInPosts grounded strictly in web research evidence.

        Args:
            campaign_id: UUID of the target campaign.
            plan: The approved CampaignPlan.
            brief: Master ResearchBrief containing verified evidence items.
            event_name: Event name from intake checklist.
            event_date: Event date from intake checklist.
            venue: Venue from intake checklist.
            registration_link: Registration URL from intake checklist.
            target_audience: Target audience from intake checklist.
            curriculum_breakdown: Curriculum/content breakdown from intake checklist.
            ticket_price: Pricing info (Free/Paid) from intake checklist.
            guest_name: Guest speaker name from intake checklist.
            guest_title: Guest speaker title from intake checklist.
            guest_profile: Guest profile dictionary from intake checklist.
            post_time_str: Daily post time string.
            timezone_name: Account timezone name.
            brand: Canonical BrandContext.
            campaign_type: Campaign type from intake (e.g. app_launch).
            campaign_name: Campaign name from intake/campaign.
            objective: Campaign objective from intake.
            value_proposition: Value proposition from intake.
            cta_url: Primary CTA URL from intake.
            on_post_started: Optional async callback invoked as each post begins
                generating — ``(index, slot_id, total_posts)``. Purely for
                progress observation; it does not affect scheduling or concurrency.
            on_post_completed: Optional async callback invoked once a single post
                has been fully generated and finalized (schedule overlay applied) —
                ``(index, slot_id, total_posts, post)``. Only fully validated posts
                are ever passed here.

        Returns:
            List of LinkedInPost objects in 'draft' status.
        """
        posts: list[LinkedInPost] = []
        prepared_posts = []
        slots = (
            plan.channel_plan.calendar_slots
            if plan.channel_plan and plan.channel_plan.calendar_slots
            else ()
        )

        if not slots:
            raise ValueError(
                "The stored plan has no content calendar. Refine the plan before generating posts."
            )
        if brand is None:
            raise ValueError("Resolved Brand Setup is required for LinkedIn generation.")
        if plan.schedule_plan is None or not plan.schedule_plan.slots:
            raise ValueError("The stored plan has no canonical LinkedIn schedule.")
        slots = normalize_calendar_slots(slots, plan.schedule_plan)
        scheduled_by_id = {str(item.slot_id): item for item in plan.schedule_plan.slots}

        logger.info(
            "[POST GENERATOR] Starting post generation for campaign_id=%s | event='%s' | guest='%s' | slots=%d",
            campaign_id,
            event_name,
            guest_name,
            len(slots),
        )

        for idx, slot in enumerate(slots, 1):
            logger.info(
                "[POST GENERATOR Slot %d/%d] Generating post for slot_id='%s' | theme='%s' | date='%s'",
                idx,
                len(slots),
                slot.slot_id,
                slot.theme,
                slot.date,
            )
            schedule_slot = scheduled_by_id[slot.slot_id]
            scheduled_at = schedule_slot.scheduled_at_utc
            local_date = schedule_slot.local_date
            timezone_name = schedule_slot.timezone
            post_time_str = schedule_slot.local_time.strftime("%I:%M %p")

            logger.info(
                "[POST GENERATOR Slot %d/%d] Scheduled at UTC: %s (local: %s %s %s)",
                idx,
                len(slots),
                scheduled_at.isoformat(),
                local_date,
                post_time_str,
                timezone_name,
            )

            ctx = ContentContextBuilder.build_context(
                slot,
                plan,
                brief,
                event_name=event_name,
                event_date=event_date,
                venue=venue,
                registration_link=registration_link,
                target_audience=target_audience,
                curriculum_breakdown=curriculum_breakdown,
                ticket_price=ticket_price,
                guest_name=guest_name,
                guest_position=guest_title,
                guest_organization=None,
                guest_profile=guest_profile,
                post_time_str=post_time_str,
                brand=brand,
                campaign_type=campaign_type,
                campaign_name=campaign_name,
                objective=objective,
                value_proposition=value_proposition,
                cta_url=cta_url,
                campaign_category=campaign_category,
                outcome_value_proposition=outcome_value_proposition,
                product_facts=product_facts,
            )
            prepared_posts.append((idx, slot, ctx, scheduled_at))

        # Independent calendar slots use the same prompt/schema, so generate a
        # small batch concurrently and preserve the original calendar order.
        # The concurrency limit and scheduling are unchanged; the optional
        # progress callbacks only observe posts as they complete.
        semaphore = asyncio.Semaphore(min(3, len(prepared_posts)))
        total = len(prepared_posts)

        async def _generate_prepared(item):
            idx, slot, ctx, scheduled_at = item
            async with semaphore:
                if on_post_started is not None:
                    await on_post_started(idx, str(slot.slot_id), total)
                post = await self._generate_single_post(campaign_id, ctx, scheduled_at=scheduled_at)
            if post:
                # Finalize the post with its canonical schedule metadata before it
                # is surfaced, so a progressively delivered post is already complete.
                canonical_slot = scheduled_by_id[slot.slot_id]
                post = post.model_copy(
                    update={
                        "timezone": canonical_slot.timezone,
                        "schedule_reason": canonical_slot.schedule_reason,
                        "schedule_source": canonical_slot.schedule_source,
                        "schedule_confidence": canonical_slot.schedule_confidence,
                    }
                )
                if on_post_completed is not None:
                    await on_post_completed(idx, str(slot.slot_id), total, post)
            return idx, slot, post

        generated = await asyncio.gather(*(_generate_prepared(item) for item in prepared_posts))
        for idx, slot, post in generated:
            if post:
                logger.info(
                    "[POST GENERATOR Slot %d/%d SUCCESS] hook='%s' | scheduled_at=%s",
                    idx,
                    len(slots),
                    post.hook[:80],
                    post.scheduled_at.isoformat(),
                )
                posts.append(post)
            else:
                logger.warning(
                    "[POST GENERATOR Slot %d/%d WARNING] Failed to generate post for slot_id='%s'",
                    idx,
                    len(slots),
                    slot.slot_id,
                )

        return posts

    async def _generate_single_post(
        self, campaign_id: UUID, ctx: ContentContext, scheduled_at: datetime | None = None
    ) -> LinkedInPost | None:
        """Call LLM with strict grounding constraints."""
        system_prompt = (
            "You are an Elite LinkedIn Copywriter. Your MANDATE is to write high-converting, "
            "data-driven LinkedIn posts using ONLY the real brand, campaign facts, and research evidence provided below. "
            "If a Featured Guest/Speaker is present, incorporate their name and title appropriately. "
            "CRITICAL: If Guest/Speaker is not provided or marked None, absolutely DO NOT invent, assume, or mention any guest, speaker, or keynote! "
            "Always use the exact campaign name, objective, value proposition, and CTA destination link provided. "
            "DO NOT hallucinate, invent statistics, or use generic industry hype. "
            "Write in plain, natural English. Do NOT use em dashes or en dashes, and avoid marketing jargon. "
            "DO NOT write 'link in bio' when a real destination or CTA link is provided. Use the exact link."
        )

        if ctx.brand is None:
            raise ValueError("Brand context is required.")

        mandatory_instructions = """### INSTRUCTIONS
Write a compelling LinkedIn post formatted with:
1. Hook: 1-3 lines attention grabbing opener
2. Body: 3-5 short paragraphs with line breaks, incorporating campaign facts naturally
3. CTA: Clear, direct call-to-action using the exact CTA / destination link if provided

CRITICAL: The post MUST be written specifically about the 'Slot Theme' and 'Messaging Pillar' provided in the Campaign Strategy section. Do not write a generic campaign summary.

Return ONLY valid JSON matching this schema:
{
  "hook": "attention grabbing opener",
  "body": "main post text with line breaks",
  "cta": "call to action line with real link"
}"""
        mandatory_instructions = f"{mandatory_instructions}\n\n{PLAIN_LANGUAGE_STYLE_RULE}"
        user_prompt = self._build_user_prompt(ctx, mandatory_instructions)

        try:
            # Serialize this local-Ollama call against all other LinkedIn
            # generation (posts + outreach) so the single GPU is never
            # double-booked. A no-op when the router targets remote providers.
            async with linkedin_local_ollama_slot(self.llm):
                res = await self.llm.generate_json(
                    system_prompt,
                    user_prompt,
                    timeout=LINKEDIN_LOCAL_OLLAMA_TIMEOUT_SECONDS,
                )
            # Enforce the plain-language style deterministically: strip em/en
            # dashes from the model output while keeping real hyphens. This
            # guarantees the no-em-dash contract regardless of the model.
            hook = _to_plain_style(res.get("hook", "").strip())
            body = _to_plain_style(res.get("body", "").strip())
            cta = _to_plain_style(res.get("cta", "").strip())

            if not hook or not body or not cta:
                raise ValueError("The model returned an incomplete LinkedIn post. Please retry.")

            full_content = f"{hook}\n\n{body}\n\n{cta}".strip()
            evidence_ids = tuple(f.fact_id for f in ctx.researched_facts)

            # Use the pre-computed scheduled_at passed in from generate_all_posts.
            # Fallback to now+1hour only if called directly without a schedule.
            scheduled_dt = (
                scheduled_at if scheduled_at is not None else datetime.now(UTC) + timedelta(hours=1)
            )

            logger.info(
                "[POST GEN] Slot=%s | Event='%s' | Guest='%s' | Hook='%s...' | ScheduledAt=%s",
                ctx.slot_id,
                ctx.event_name,
                ctx.guest_name,
                hook[:60] if hook else "(empty)",
                scheduled_dt.isoformat(),
            )

            return LinkedInPost(
                campaign_id=campaign_id,
                slot_id=ctx.slot_id,
                scheduled_at=scheduled_dt,
                hook=hook,
                body=body,
                cta_text=cta,
                full_content=full_content,
                evidence_ids=evidence_ids,
                status=PostStatus.DRAFT,
            )
        except Exception as e:
            logger.error("Failed to generate LinkedIn post for slot %s: %s", ctx.slot_id, e)
            raise RuntimeError("LinkedIn post generation failed. Please retry.") from e
