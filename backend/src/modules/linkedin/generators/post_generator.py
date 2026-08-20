"""LinkedIn Post Generator — Generates research-grounded post copy per CalendarSlot."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from src.modules.linkedin.generators.content_context import ContentContextBuilder
from src.modules.linkedin.models import ContentContext, LinkedInPost, PostStatus
from src.modules.planning.models.campaign_plan import CampaignPlan
from src.modules.research.models.research_brief import ResearchBrief
from src.modules.research.services.llm_router import LLMRouterService

logger = logging.getLogger(__name__)


class LinkedInPostGenerator:
    """Generates research-anchored LinkedIn feed posts for approved campaign slots."""

    def __init__(self, llm_router: LLMRouterService | None = None) -> None:
        self.llm = llm_router or LLMRouterService()

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
        ticket_price: str = "Free",
        guest_name: str | None = None,
        guest_title: str | None = None,
        guest_profile: dict | None = None,
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

        Returns:
            List of LinkedInPost objects in 'draft' status.
        """
        posts: list[LinkedInPost] = []
        slots = plan.channel_plan.calendar_slots if plan.channel_plan and plan.channel_plan.calendar_slots else ()

        if not slots:
            from src.modules.planning.models.campaign_plan import CalendarSlot, CampaignPhase
            event_label = event_name or "our upcoming event"
            today = date.today()

            # Parse the event date if provided, else use 7 days from today as a safe default
            event_dt: date | None = None
            if event_date:
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y", "%d %B %Y"):
                    try:
                        event_dt = datetime.strptime(event_date, fmt).date()
                        break
                    except ValueError:
                        continue

            if event_dt is None or event_dt <= today:
                event_dt = today + timedelta(days=7)

            days_remaining = (event_dt - today).days
            logger.info(
                "[POST GENERATOR FALLBACK] Days remaining until event: %d — building date-aware fallback slots.",
                days_remaining,
            )

            cta_text = f"Register now: {registration_link}" if registration_link else "Reserve your seat today"

            # Build smart date-aware fallback slots
            if days_remaining <= 2:
                # Urgent: only a last-chance post today
                slot_dates = [today]
                themes = [f"🚨 Last chance — {event_label} is TODAY/TOMORROW!"]
                phases = [CampaignPhase.LAST_CALL]
            elif days_remaining <= 7:
                # Short runway: one teaser + one urgency
                slot_dates = [today, event_dt - timedelta(days=1)]
                themes = [
                    f"Don't miss {event_label} — it's happening this week!",
                    f"Final reminder: {event_label} starts tomorrow!",
                ]
                phases = [CampaignPhase.LAUNCH, CampaignPhase.LAST_CALL]
            else:
                # Comfortable runway: teaser, value, urgency spread across the timeline
                mid_point = today + timedelta(days=days_remaining // 2)
                slot_dates = [today, mid_point, event_dt - timedelta(days=2)]
                themes = [
                    f"Why attend {event_label}? — Authority & Value",
                    f"What you will learn at {event_label}",
                    f"Last chance — {event_label} is almost here!",
                ]
                phases = [CampaignPhase.TEASER, CampaignPhase.SUSTAIN, CampaignPhase.LAST_CALL]

            slots = tuple(
                CalendarSlot(
                    slot_id=f"fallback_slot_{i + 1}",
                    date=slot_dates[i].strftime("%Y-%m-%d"),
                    platform="LinkedIn",
                    phase=phases[i],
                    theme=themes[i],
                    format_type="Text Post",
                    messaging_pillar="Authority & Vision" if i == 0 else "Urgency & Event Conversion",
                    cta=cta_text,
                )
                for i in range(len(slot_dates))
            )
            logger.info("[POST GENERATOR FALLBACK] Generated %d smart fallback slots.", len(slots))

        logger.info("[POST GENERATOR] Starting post generation for campaign_id=%s | event='%s' | guest='%s' | slots=%d", campaign_id, event_name, guest_name, len(slots))

        for idx, slot in enumerate(slots, 1):
            logger.info("[POST GENERATOR Slot %d/%d] Generating post for slot_id='%s' | theme='%s'", idx, len(slots), slot.slot_id, slot.theme)
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
            )
            post = await self._generate_single_post(campaign_id, ctx)
            if post:
                logger.info("[POST GENERATOR Slot %d/%d SUCCESS] Generated post hook: '%s'", idx, len(slots), post.hook[:80])
                posts.append(post)
            else:
                logger.warning("[POST GENERATOR Slot %d/%d WARNING] Failed to generate post for slot_id='%s'", idx, len(slots), slot.slot_id)

            import asyncio
            await asyncio.sleep(4)  # Prevent Gemini 429 Rate Limit Exceeded

        return posts

    async def _generate_single_post(
        self, campaign_id: UUID, ctx: ContentContext
    ) -> LinkedInPost | None:
        """Call LLM with strict grounding constraints."""
        facts_formatted = "\n".join(
            f"- [{f.dimension.upper()}] Claim: {f.claim} | Quote: '{f.quote}' (Source: {f.source_url})"
            for f in ctx.researched_facts
        ) if ctx.researched_facts else "No direct evidence provided. Rely strictly on strategic USP and event details below."

        system_prompt = (
            "You are an Elite LinkedIn Copywriter. Your MANDATE is to write high-converting, "
            "data-driven LinkedIn posts using ONLY the real event and research facts provided below. "
            "If a Guest/Speaker is present, open with their name and title as the hook. "
            "Always use the exact event name, venue, date, and registration link provided. "
            "DO NOT hallucinate, invent statistics, or use generic industry hype. "
            "DO NOT write 'link in bio' when a real registration link is provided — use the exact link."
        )

        # Build guest line
        guest_line = ""
        if ctx.guest_name:
            guest_line = f"- Guest/Speaker: {ctx.guest_name}"
            if ctx.guest_position:
                guest_line += f" ({ctx.guest_position})"
            if ctx.guest_profile and ctx.guest_profile.get("professional_biography"):
                guest_line += f"\n- Guest Bio/Research: {ctx.guest_profile.get('professional_biography')}"

        # Build registration CTA line
        reg_line = f"- Registration Link: {ctx.registration_link} (USE THIS EXACT LINK in the CTA)" if ctx.registration_link else "- Registration Link: not provided"

        user_prompt = f"""
Campaign Event Details (USE THESE — do not invent alternatives):
- Event Name: {ctx.event_name or '(not specified)'}
- Event Date: {ctx.event_date or '(not specified)'}
- Venue: {ctx.venue or '(not specified)'}
- Target Audience: {ctx.target_audience or '(not specified)'}
- Curriculum/Topics: {ctx.curriculum_breakdown or '(not specified)'}
- Pricing: {ctx.ticket_price}
{guest_line}
{reg_line}

Campaign Strategic Context:
- Slot Theme: {ctx.theme}
- Messaging Pillar: {ctx.messaging_pillar}
- CTA: {ctx.cta}
- Tone of Voice: {ctx.tone_of_voice}
- Unique Selling Proposition: {ctx.usp}
- Differentiation Angle: {ctx.differentiation_angle}

REAL RESEARCHED FACTS & EVIDENCE (Grounding Source):
{facts_formatted}

INSTRUCTIONS:
Write a compelling LinkedIn post formatted with:
1. Hook: 1-3 lines attention grabbing opener (use event name and guest if provided)
2. Body: 3-5 short paragraphs with line breaks, incorporating event details and facts naturally
3. CTA: Clear, direct call-to-action using the exact registration link if provided

Return ONLY valid JSON matching this schema:
{{
  "hook": "attention grabbing opener",
  "body": "main post text with line breaks",
  "cta": "call to action line with real link"
}}
"""
        try:
            res = await self.llm.generate_json(system_prompt, user_prompt)
            hook = res.get("hook", "").strip()
            body = res.get("body", "").strip()
            cta = res.get("cta", "").strip()

            full_content = f"{hook}\n\n{body}\n\n{cta}".strip()
            evidence_ids = tuple(f.fact_id for f in ctx.researched_facts)

            # Determine scheduled_at datetime (defaulting to today + slot index offset if date parsing fails)
            scheduled_dt = datetime.now(UTC)

            logger.info(
                "[POST GEN] Slot=%s | Event='%s' | Guest='%s' | Hook='%s...'",
                ctx.slot_id,
                ctx.event_name,
                ctx.guest_name,
                hook[:60] if hook else "(empty)",
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
            return None

