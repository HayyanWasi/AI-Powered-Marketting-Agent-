import logging

logger = logging.getLogger(__name__)

PROMPT_TEMPLATES: dict[str, str] = {}


class _SafeDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_template(name: str, variables: dict[str, str]) -> str:
    if name not in PROMPT_TEMPLATES:
        raise KeyError(f"Template '{name}' not found")
    template = PROMPT_TEMPLATES[name]
    rendered = template.format_map(_SafeDict(variables))
    logger.debug("Rendered template '%s'", name)
    return rendered


def register_template(name: str, template: str) -> None:
    if name in PROMPT_TEMPLATES:
        raise ValueError(f"Template '{name}' already exists")
    PROMPT_TEMPLATES[name] = template
    logger.debug("Registered template '%s'", name)


def register_default_templates() -> None:
    """Register default prompt templates for the application."""
    register_template(
        "strategy_generation",
        """You are an expert Chief Marketing Officer (CMO). You create compelling
marketing strategies for events and brands.

Create a marketing strategy brief for this event:

Event: {event_name}
Date: {event_date}
Venue: {venue}
Platforms: {platforms}
Registration: {registration_link}

Brand: {company_name}
Brand Guidelines: {brand_guidelines}
Brand Tone: {brand_tone}

Guests/Speakers:
{guests}

Generate a strategy with EXACTLY this format:
USP_HOOK: <one compelling sentence that captures the unique selling proposition>
MESSAGING_PILLARS: <3 themes, comma-separated>
OBJECTION_HANDLING: <2 common objections with counter-arguments, separated by semicolon>
CTA_HIERARCHY: <2 calls-to-action (awareness then conversion), comma-separated>""",
    )

    register_template(
        "guest_analysis",
        """You are a research assistant that analyzes web search result metadata to build structured guest/speaker profiles.

Given a list of search results (each with page title, snippet, and URL), extract the following information about the person being searched:

- full_name: The person's full name
- current_position: Their current professional role or title
- organization: The company or organization they currently work for
- professional_biography: A concise 2-4 sentence biography summarizing only information supported by the provided search results
- areas_of_expertise: A list of topics or fields they are knowledgeable in
- confidence_level: HIGH if information is consistent across multiple (>=3) sources and corroborated, MEDIUM if some corroboration exists (2 sources), LOW if only a single source or conflicting information

Rules:
1. Only use information present in the provided search results. NEVER invent or assume missing information.
2. If a field cannot be determined from the provided results, leave it as an empty string or empty list.
3. If results contain conflicting information, prefer information appearing consistently across multiple results.
4. If conflicts cannot be resolved, lower the confidence level.
5. Duplicate information from multiple sources should be merged into a single coherent entry.

Respond in EXACTLY this JSON format:
{{
    "full_name": "",
    "current_position": "",
    "organization": "",
    "professional_biography": "",
    "areas_of_expertise": [],
    "confidence_level": "LOW"
}}""",
    )

    register_template(
        "content_generation",
        """You are an expert social media copywriter. You write concise,
platform-native marketing copy. Always respond using the exact
labeled format requested — no preamble, no extra commentary.

Write a {platform} post for: {theme}
Platform: {platform} (format: {format_type})
Phase: {phase}

Brand: {company_name}
Brand tone: {brand_tone}
Brand guidelines: {brand_guidelines}
Event: {event_name} on {event_date} at {venue}
Guests/Speakers: {guests}
{guest_bios}

PLATFORM SPECS (LinkedIn):
- CRITICAL HARD LIMIT: Each variant (A, B, and C) MUST be between 1,200-1,500
  characters TOTAL, including spaces. Count carefully before responding. This is
  words is NOT approx 1500 — measure by CHARACTERS, not word count. A variant
  over 1,500 characters is a failed response.
- Line breaks every 1-2 sentences (short punchy lines, not dense paragraphs)
- 3-5 relevant hashtags at the end
- No emojis in the first line`

HOOK FORMULAS — each variant must open with a hook that follows ONE of these patterns.
Pick the pattern that best fits the variant's job below. Do not write a generic
opening sentence that could apply to any event — the hook must be specific to
this event's actual details.

- Bold claim: state a strong, specific claim tied to the event topic or guest's work
- Personal story / guest angle: open through the guest's specific experience or achievement
- Contrarian take: challenge a common assumption in this field
- Data drop: lead with a specific number or fact (only if present in the provided context — never invent one)
- Question: ask a sharp, specific question tied to the event's actual topic or guest

BANNED PHRASES — do not use these or close variants of them anywhere in the post:
"in today's fast-paced world", "unlock your potential", "don't miss out",
"game-changer", "elevate your", "take your [X] to the next level",
"in the ever-evolving landscape of", "unparalleled", "seamless", "leverage",
"dive into", "embark on a journey", "at the forefront of"

If you catch yourself about to write one of these, stop and replace it with a
concrete, specific statement drawn from the actual event details provided above.

Respond in EXACTLY this format:
VARIANT_A: <hook using Bold claim OR Personal story/guest angle pattern, then body, then CTA>
VARIANT_B: <hook using Data drop OR a value/benefit list pattern, then body, then CTA>
VARIANT_C: <hook using Question OR Contrarian take pattern, then body, then CTA>""",
    )

    logger.info("Registered %d default prompt templates", len(PROMPT_TEMPLATES))


# Register default templates on module import
register_default_templates()
