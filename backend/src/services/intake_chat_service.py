"""Intake Chat Service — Conversational Campaign Requirement Gathering & Parameter Extraction."""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from src.models.intake import (
    CampaignType,
    ExtractedData,
    IntakeChecklist,
    UnifiedIntakeResponse,
)
from src.modules.research.services.llm_router import LLMRouterService
from src.repositories.base import BaseRepository
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class IntakeProcessingError(Exception):
    """Raised when an intake turn cannot be processed by the AI pipeline."""


class IntakePersistenceError(Exception):
    """Raised when authoritative intake persistence fails."""


# ── UNIFIED BATCH INTAKE PROMPT ──
_UNIFIED_INTAKE_PROMPT = """\
You are an intelligent campaign requirements gathering agent and data extractor.

Your job:
1. Extract all campaign details provided in the user's latest message or conversation into the 'extracted' JSON object.
2. Formulate a friendly, natural conversational 'reply' acknowledging the newly provided details and asking ONLY for the next 1-2 missing fields.

CRITICAL RULES TO NEVER ASK FOR ALREADY ANSWERED QUESTIONS:
1. LOOK CAREFULLY AT 'ALREADY COLLECTED INFORMATION'. NEVER ask for any detail that has already been collected or that the user just provided in their message.
2. If the user says "no guest", "none", "no speaker", "solo", or "n/a", extract "has_guest": false and DO NOT ask for guest name or title.
3. Only ask for items from the 'CURRENTLY MISSING REQUIRED FIELDS' list. Choose at most 2 missing items at a time.
4. If all required fields are collected, confirm all details are gathered and invite the user to proceed.
5. Provide ONLY valid JSON adhering strictly to the required schema. No markdown formatting blocks around the JSON.
6. OBJECTIVE PRESERVATION: If the user provides a campaign objective or goal (e.g. 'Build awareness for the new hospital and launch event'), extract and PRESERVE THEIR EXACT WORDING verbatim in 'objective'. NEVER summarize, paraphrase, shorten, genericize, or replace the user's objective statement.
7. TICKET & ADMISSION NEGATION: If the user indicates ticket price, admission, or fee is unknown, undecided, not decided, not supplied, not available yet, or TBD, extract 'is_free_or_paid': null. NEVER infer 'Paid' or 'Free' or invent ticket prices when ticket details are absent or undecided. Only extract 'Paid' or 'Free' when the user explicitly affirms it (e.g. 'Tickets cost PKR 2,000' -> 'Paid', 'Admission is free' -> 'Free').
8. FIELD PERSISTENCE: Never overwrite or alter previously collected valid information unless the user explicitly requested a change.
9. AUDIENCE INFERENCE: Infer a behavioral audience profile from the campaign facts and the user's wording. Do not ask for a target audience when the campaign clearly identifies who must act. Keep occupation/industry strings open-ended; never force them into a fixed category list. Explicit audience statements always win.
10. CAMPAIGN VALIDITY WINDOW: If the user gives a campaign date RANGE (e.g. "from 20 September 2026 to 1 October 2026", "between Sep 20 and Oct 1 2026"), extract the two bounds as ISO dates into 'campaign_start_date' and 'campaign_end_date' (e.g. "2026-09-20" and "2026-10-01"). This is the scheduling window, NOT an event date. NEVER put a date range into 'event_date'. Only populate 'event_date' when the user gives a single actual event/webinar date.

JSON OUTPUT SCHEMA:
{
  "extracted": {
    "campaign_type": string or null (app_launch, product_launch, service_launch, physical_event, webinar, general_promotion),
    "campaign_name": string or null,
    "objective": string or null,
    "target_audience": string or null,
    "campaign_start_date": string or null (ISO YYYY-MM-DD; campaign validity window START, not an event date),
    "campaign_end_date": string or null (ISO YYYY-MM-DD; campaign validity window END, not an event date),
    "audience_profile": {
      "summary": string,
      "occupation_groups": [string], "industries": [string], "seniority_levels": [string],
      "work_environments": [string], "schedule_patterns": [string], "attention_patterns": [string],
      "locations": [string], "timezones": [string],
      "source": "explicit" or "inferred" or "mixed" or "fallback",
      "confidence": "low" or "medium" or "high", "evidence": [string],
      "inference_version": "audience-v1"
    } or null,
    "audience_profile_version": "audience-v1" or null,
    "value_proposition": string or null,
    "cta_url": string or null,
    "category": string or null,
    "event_date": string or null,
    "venue": string or null,
    "has_guest": boolean or null,
    "guest_name": string or null,
    "guest_title": string or null,
    "curriculum_breakdown": string or null,
    "outcome_deliverable": string or null,
    "is_free_or_paid": string or null,
    "registration_link": string or null
  },
  "reply": "Friendly response acknowledging newly provided info and asking ONLY for the next 1-2 still-missing fields."
}
"""


_FIELD_LABELS: dict[str, str] = {
    "campaign_type": "the type of campaign (app launch, product launch, service launch, physical event, webinar, or general promotion)",
    "campaign_name": "the event or campaign name",
    "objective": "the primary objective of the campaign",
    "target_audience": "the target audience",
    "value_proposition": "the core value proposition or main features",
    "cta_url": "the call-to-action link (e.g. download or signup URL)",
    "category": "the campaign category",
    "campaign_start_date": "the campaign start date (validity window)",
    "campaign_end_date": "the campaign end date (validity window)",
    "event_date": "the event date",
    "venue": "the venue",
    "has_guest": "whether there is a guest speaker",
    "guest_name": "the guest speaker's name",
    "guest_title": "the guest speaker's title or designation",
    "curriculum_breakdown": "the curriculum or content breakdown",
    "outcome_deliverable": "the key outcome or deliverable for attendees",
    "is_free_or_paid": "whether it is free or paid",
    "registration_link": "the registration link",
}


_CAMPAIGN_TYPE_ALIASES: dict[str, str] = {
    "app": CampaignType.APP_LAUNCH.value,
    "application_launch": CampaignType.APP_LAUNCH.value,
    "launching_an_app": CampaignType.APP_LAUNCH.value,
    "mobile_app_launch": CampaignType.APP_LAUNCH.value,
    "product": CampaignType.PRODUCT_LAUNCH.value,
    "launching_a_product": CampaignType.PRODUCT_LAUNCH.value,
    "new_product_launch": CampaignType.PRODUCT_LAUNCH.value,
    "service": CampaignType.SERVICE_LAUNCH.value,
    "launching_a_service": CampaignType.SERVICE_LAUNCH.value,
    "new_service_launch": CampaignType.SERVICE_LAUNCH.value,
    "event": CampaignType.PHYSICAL_EVENT.value,
    "in_person_event": CampaignType.PHYSICAL_EVENT.value,
    "live_event": CampaignType.PHYSICAL_EVENT.value,
    "offline_event": CampaignType.PHYSICAL_EVENT.value,
    "online_webinar": CampaignType.WEBINAR.value,
    "virtual_webinar": CampaignType.WEBINAR.value,
    "promotion": CampaignType.GENERAL_PROMOTION.value,
    "brand_promotion": CampaignType.GENERAL_PROMOTION.value,
    "general_campaign": CampaignType.GENERAL_PROMOTION.value,
    "marketing_campaign": CampaignType.GENERAL_PROMOTION.value,
    "promotional_campaign": CampaignType.GENERAL_PROMOTION.value,
}


def _normalize_campaign_type(value: Any) -> str | None:
    """Convert human/LLM campaign-type wording to the canonical enum value."""
    if value is None:
        return None

    raw_value = value.value if isinstance(value, CampaignType) else str(value)
    normalized = raw_value.strip().lower()
    if not normalized:
        return None

    if "." in normalized:
        normalized = normalized.rsplit(".", maxsplit=1)[-1]
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")

    canonical_values = {campaign_type.value for campaign_type in CampaignType}
    if normalized in canonical_values:
        return normalized
    return _CAMPAIGN_TYPE_ALIASES.get(normalized)


# phrase (snake_case) -> canonical value, built only from the already-canonical
# enum and the existing alias table above — no new vocabulary is introduced.
_CAMPAIGN_TYPE_PHRASES: dict[str, str] = {
    campaign_type.value: campaign_type.value for campaign_type in CampaignType
} | _CAMPAIGN_TYPE_ALIASES

# Longer (more specific) phrases first, so "general_promotion" is preferred
# over the shorter "promotion" when a message contains both.
_CAMPAIGN_TYPE_PATTERNS: list[tuple[re.Pattern[str], str]] = sorted(
    (
        (
            re.compile(r"(?<!not )(?<!n't )\b" + phrase.replace("_", r"[\s_-]+") + r"\b"),
            canonical,
        )
        for phrase, canonical in _CAMPAIGN_TYPE_PHRASES.items()
    ),
    key=lambda pair: pair[0].pattern.count(r"[\s_-]+"),
    reverse=True,
)


def _detect_explicit_campaign_type(message: str) -> str | None:
    """Deterministically read a campaign type the user stated in their own words.

    Built entirely from the canonical CampaignType enum and the existing
    alias table — no campaign-specific or otherwise new vocabulary. This
    exists because small/local LLMs are unreliable at classifying a
    closed-vocabulary field embedded in a longer free-text message (proven by
    repeated live reproduction), even though a deterministic text match finds
    it correctly. A single "not "/"n't " immediately before a phrase excludes
    it; broader negation scope is intentionally not attempted here.
    """
    lower_msg = message.lower()
    for pattern, canonical in _CAMPAIGN_TYPE_PATTERNS:
        if pattern.search(lower_msg):
            return canonical
    return None


_DEFAULT_INTAKE_REPLY = "Great! Could you share the next detail for your campaign?"

_EXTRACTED_FIELD_NAMES: frozenset[str] = frozenset(ExtractedData.model_fields)

_NULL_SENTINELS = ("", "null", "none", "n/a", "undefined")


def _strip_null_sentinels(extracted: dict[str, Any]) -> dict[str, Any]:
    """Map the string placeholders small models emit for "no value" onto None.

    Local models routinely answer with "null"/"n/a" strings — including for
    boolean fields. These have always meant "absent" here, so they are
    normalised before validation rather than failing the whole turn.
    """
    return {
        k: (None if isinstance(v, str) and v.strip().lower() in _NULL_SENTINELS else v)
        for k, v in extracted.items()
    }


def _coerce_unified_intake_response(payload: Any) -> UnifiedIntakeResponse:
    """Validate an intake LLM payload into the canonical UnifiedIntakeResponse.

    Accepts the canonical wrapped shape and the backward-compatible flat shape
    where known extraction fields sit at the top level. Any other shape is a
    structured-extraction failure: the turn must not acknowledge state it could
    not safely interpret.
    """
    if not isinstance(payload, dict):
        raise IntakeProcessingError("Intake LLM response was not a JSON object.")

    raw_extracted = payload.get("extracted")
    if isinstance(raw_extracted, dict):
        extracted_payload: dict[str, Any] = raw_extracted
    elif raw_extracted is not None:
        raise IntakeProcessingError("Intake LLM response had a malformed 'extracted' object.")
    else:
        flat = {k: v for k, v in payload.items() if k in _EXTRACTED_FIELD_NAMES}
        if not flat:
            raise IntakeProcessingError(
                "Intake LLM response contained no recognizable extraction object."
            )
        extracted_payload = flat

    reply = payload.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        reply = _DEFAULT_INTAKE_REPLY

    working = _strip_null_sentinels(extracted_payload)

    # A weak/local provider can get one field's shape wrong (a mismatched
    # literal, a wrong type) while every other field it sent is fine. Failing
    # the whole turn over one bad field would throw away genuinely correct
    # state (campaign_type, campaign_name, ...) and surface as a 502 for
    # nothing that field caused. Drop only the offending top-level field(s)
    # and retry; only fail the turn if nothing was extractable at all.
    for _ in range(len(working) + 1):
        try:
            return UnifiedIntakeResponse.model_validate({"extracted": working, "reply": reply})
        except ValidationError as exc:
            bad_keys = {
                err["loc"][1]
                for err in exc.errors()
                if len(err["loc"]) > 1 and err["loc"][0] == "extracted" and err["loc"][1] in working
            }
            if not bad_keys:
                raise IntakeProcessingError(
                    "Intake LLM response failed structured validation."
                ) from exc
            for bad_key in bad_keys:
                logger.warning(
                    "Dropping intake field with invalid shape from provider payload: %r", bad_key
                )
                working.pop(bad_key, None)

    raise IntakeProcessingError("Intake LLM response failed structured validation.")


def _is_ticket_negated_or_unknown(message: str) -> bool:
    lower_msg = message.lower()

    explicit_unknown_phrases = [
        "not been supplied",
        "not supplied",
        "hasn't been supplied",
        "hasnt been supplied",
        "haven't been supplied",
        "havent been supplied",
        "not available",
        "isn't available",
        "isnt available",
        "not yet available",
        "not decided",
        "hasn't been decided",
        "hasnt been decided",
        "haven't decided",
        "havent decided",
        "not yet decided",
        "yet to be decided",
        "to be decided",
        "no ticket price",
        "no ticket details",
        "no price yet",
        "no price set",
        "price not set",
        "tickets not set",
        "ticket price unknown",
        "ticket price is unknown",
        "price is unknown",
        "admission is unknown",
        "ticket unknown",
        "tickets unknown",
        "ticket tbd",
        "tickets tbd",
        "price tbd",
        "ticket price tbd",
        "ticket price: tbd",
        "ticket price: unknown",
        "ticket price: n/a",
        "ticket price: none",
        "tickets: tbd",
        "tickets: unknown",
        "tickets: n/a",
        "tickets: none",
        "undecided ticket",
        "ticket undecided",
        "tickets undecided",
        "admission undecided",
        "admission not available",
        "admission information is not available",
        "not announced yet",
        "ticket not announced",
        "tickets not announced",
        "price not announced",
        "don't know the ticket price",
        "dont know the ticket price",
        "not sure about ticket",
        "not sure about the ticket",
        "not finalized",
        "not finalised",
    ]
    if any(p in lower_msg for p in explicit_unknown_phrases):
        return True

    ticket_term = r"(?:ticket|tickets|admission|entry\s+fee|ticket\s+price|price|fee)"
    negation_or_unknown = (
        r"(?:not\s+(?:yet\s+)?(?:been\s+)?(?:supplied|decided|available|announced|set|finalized|finalised|known|fixed)"
        r"|unknown|undecided|tbd|tba|n/?a|none|unclear)"
    )

    if re.search(rf"\b{ticket_term}\b.*?\b{negation_or_unknown}\b", lower_msg):
        return True
    if re.search(rf"\b{negation_or_unknown}\b.*?\b{ticket_term}\b", lower_msg):
        return True
    if re.search(
        rf"\b(?:haven't|havent|hasn't|hasnt|have\s+not|has\s+not)\s+decided\b.*?\b{ticket_term}\b",
        lower_msg,
    ):
        return True
    return bool(re.search(rf"\bno\s+{ticket_term}\s*(?:yet|decided|set|available)?\b", lower_msg))


_DATE_INPUT_FORMATS = (
    "%Y-%m-%d",
    "%d %B %Y",
    "%B %d, %Y",
    "%B %d %Y",
    "%d %b %Y",
    "%b %d, %Y",
    "%b %d %Y",
    "%d/%m/%Y",
    "%d-%m-%Y",
)


def _parse_iso_date(value: Any) -> date | None:
    """Parse a date from ISO or common human formats, or return None.

    Truthful: an unparseable value yields None (treated as "not provided")
    rather than a fabricated date.
    """
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s or s.lower() in _NULL_SENTINELS:
        return None
    # Full ISO datetime (schedule columns store tz-aware datetimes).
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for fmt in _DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


# One date token in ISO, numeric, or spelled-month form.
_MONTH = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
_DATE_TOKEN = (
    r"(?:\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    rf"|\d{{1,2}}\s+{_MONTH}\s+\d{{4}}"
    rf"|{_MONTH}\s+\d{{1,2}},?\s+\d{{4}})"
)
# A start date, a range connector, then an end date. "from"/"between" are allowed
# but optional so a bare "X to Y" still matches. The connector must be a genuine
# range word (or dash) so a single date is never mistaken for a range.
_WINDOW_RE = re.compile(
    rf"(?P<start>{_DATE_TOKEN})\s*(?:to|until|till|through|thru|and|[-–—])\s*(?P<end>{_DATE_TOKEN})",
    re.IGNORECASE,
)


def _detect_campaign_window(message: str) -> tuple[date | None, date | None]:
    """Deterministically read a campaign date RANGE from free text.

    Returns ``(start, end)`` in the order the two dates appear (never swapped, so
    a reversed range is surfaced downstream rather than silently corrected), or
    ``(None, None)`` when the text is not an unambiguous two-date range. Small
    models proved unreliable at splitting a range into two ISO bounds (they place
    the whole phrase into event_date); a deterministic match handles it and keeps
    the range out of event_date.
    """
    if not message:
        return None, None
    m = _WINDOW_RE.search(message)
    if not m:
        return None, None
    return _parse_iso_date(m.group("start")), _parse_iso_date(m.group("end"))


def _date_to_schedule_iso(day: date, timezone: str) -> str:
    """Render a date as a tz-aware ISO datetime at day-start in the campaign tz.

    Only the date component is authoritative downstream (SchedulePlan compares
    dates), but the schedule column stores tz-aware datetimes, so we match that
    shape and preserve the campaign's own timezone.
    """
    try:
        tz = ZoneInfo(timezone or "UTC")
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime(day.year, day.month, day.day, tzinfo=tz).isoformat()


def _extract_explicit_objective(message: str) -> str | None:
    patterns = [
        r"(?:^|\n|\r|;)\s*(?:campaign\s+)?(?:primary\s+)?(?:objective|goal|purpose)\s*[:\-]\s*([^\n\r]+)",
        r"\b(?:our\s+)?(?:primary\s+)?(?:objective|goal|purpose)\s+is\s+(?:to\s+)?([^\n\r.]+)",
    ]
    for pat in patterns:
        m = re.search(pat, message, re.IGNORECASE)
        if m:
            val = m.group(1).strip().strip("\"'").rstrip(".").strip()
            if val and len(val) > 3 and val.lower() not in ("null", "none", "n/a", "undefined"):
                return val
    return None


class IntakeChatService:
    """Service driving the intake chat conversation and parameter accumulation."""

    def _get_required_fields(self, checklist_dict: dict[str, Any]) -> list[str]:
        campaign_type = checklist_dict.get("campaign_type")
        if not campaign_type:
            return ["campaign_type"]

        profile = checklist_dict.get("audience_profile") or {}
        inferred_audience_is_usable = bool(profile.get("summary")) and profile.get("confidence") in {
            "medium", "high"
        }
        common = ["campaign_name", "objective"]
        if not checklist_dict.get("target_audience") and not inferred_audience_is_usable:
            common.append("target_audience")

        if campaign_type in ("app_launch", "product_launch", "service_launch", "general_promotion"):
            return common + ["value_proposition"]

        elif campaign_type in ("physical_event", "webinar"):
            return common + ["event_date", "venue", "has_guest"]

        return common

    def _get_all_relevant_fields(self, checklist_dict: dict[str, Any]) -> list[str]:
        """Every field relevant to this campaign type, collected or not.

        Distinct from ``_get_required_fields``, which drops already-known fields
        (notably ``campaign_type``) and therefore cannot be used to decide what
        the assistant must stop asking about.
        """
        relevant = ["campaign_type", "campaign_name", "objective", "target_audience"]
        campaign_type = checklist_dict.get("campaign_type")

        if campaign_type in ("app_launch", "product_launch", "service_launch", "general_promotion"):
            relevant.append("value_proposition")
        elif campaign_type in ("physical_event", "webinar"):
            relevant += ["event_date", "venue", "has_guest"]
            if checklist_dict.get("has_guest") is True:
                relevant += ["guest_name", "guest_title"]

        return relevant

    def __init__(self, llm: LLMRouterService | None = None) -> None:
        if llm is not None:
            # Caller-injected (tests or explicit override) — use as-is.
            self.llm = llm
        else:
            # Build the dedicated intake remote chain: gemini → openrouter → groq.
            # Ollama is intentionally excluded — intake must never contend with
            # planning GPU queues (proven production root cause).
            intake_llm = LLMService.intake_remote_chain()
            logger.info(
                "IntakeChatService: using intake remote chain [%s]",
                ", ".join(name for name, _, _ in intake_llm._chain),
            )
            self.llm = LLMRouterService(llm=intake_llm)
        self._local_history: dict[str, list[dict[str, Any]]] = {}
        self._local_checklists: dict[str, IntakeChecklist] = {}

    async def process_chat_turn(
        self,
        campaign_id: UUID,
        user_message: str,
        history: list[dict[str, str]],
        current_checklist: IntakeChecklist | None = None,
        *,
        owner_id: UUID,
    ) -> dict[str, Any]:
        """Process one conversational intake turn, save to DB, and return reply + checklist."""
        checklist = current_checklist or IntakeChecklist()
        checklist_dict = checklist.model_dump()
        lower_msg = user_message.lower().strip()

        def _has_value(val: Any) -> bool:
            if val is None:
                return False
            if isinstance(val, bool):
                return True
            if isinstance(val, str):
                return val.strip().lower() not in ("", "null", "none", "n/a", "undefined")
            return True

        # ── Deterministic pre-extraction ──
        url_match = re.search(r"https?://[^\s]+", user_message)
        if url_match and not checklist_dict.get("registration_link"):
            checklist_dict["registration_link"] = url_match.group(0)

        # campaign_type is a closed-vocabulary field the LLM proved unreliable
        # at classifying when it is embedded in a longer message (repeated
        # live reproduction: omitted or null on 3/5 turns where the user
        # stated it plainly). A deterministic match only fires when nothing
        # is set yet, so it never overrides an explicit correction, which
        # still flows through the LLM extraction below as before.
        if not checklist_dict.get("campaign_type"):
            detected_campaign_type = _detect_explicit_campaign_type(user_message)
            if detected_campaign_type:
                checklist_dict["campaign_type"] = detected_campaign_type

        explicit_objective = _extract_explicit_objective(user_message)
        if explicit_objective and not checklist_dict.get("objective"):
            checklist_dict["objective"] = explicit_objective

        # Campaign validity window: a date RANGE the user states in the current
        # message is an explicit instruction, so it overrides any prior window
        # (this is what makes an explicit correction take effect). Local/remote
        # models proved unreliable at splitting a range, so a deterministic match
        # captures both bounds and keeps the range out of event_date. The bounds
        # are kept in the order stated (never swapped); a reversed range is
        # rejected truthfully after the merge below.
        win_start, win_end = _detect_campaign_window(user_message)
        if win_start and win_end:
            checklist_dict["campaign_start_date"] = win_start.isoformat()
            checklist_dict["campaign_end_date"] = win_end.isoformat()

        is_negative_or_unknown_ticket = _is_ticket_negated_or_unknown(user_message)

        if is_negative_or_unknown_ticket:
            checklist_dict["is_free_or_paid"] = None
        elif not checklist_dict.get("is_free_or_paid"):
            if any(
                w in lower_msg
                for w in [
                    "free",
                    "no fee",
                    "free of cost",
                    "free entry",
                    "0$",
                    "0 pkr",
                    "free ticket",
                    "free of charge",
                    "no cost",
                    "kharcha nahi",
                    "koi fee nahi",
                    "admission is free",
                ]
            ):
                checklist_dict["is_free_or_paid"] = "Free"
            elif (
                any(
                    w in lower_msg
                    for w in [
                        "paid",
                        "ticketed",
                        "fee hai",
                        "kharcha hai",
                        "admission fee",
                        "tickets cost",
                        "ticket costs",
                    ]
                )
                or re.search(r"(?:pkr|usd|\$|rs\.?|eur|gbp)\s*\d+", lower_msg)
                or re.search(r"\b\d+\s*(?:pkr|usd|rs|rupees|dollars|euros)\b", lower_msg)
                or re.search(r"\bprice\s+is\s+\d+", lower_msg)
            ):
                checklist_dict["is_free_or_paid"] = "Paid"

        is_negative_guest = any(
            w in lower_msg
            for w in [
                "no guest",
                "no speakers",
                "no speaker",
                "none",
                "nobody",
                "just me",
                "solo",
                "internal team",
                "no external",
                "guest nahi",
                "speaker nahi",
                "koi guest nahi",
                "without guest",
                "without speaker",
                "there is no guest",
                "no keynote",
                "did not add any guest",
                "didnot add any guest",
                "didn't add any guest",
                "not adding any guest",
                "no any guest",
                "not having any guest",
                "no guest speaker",
                "said no guest",
                "dont have guest",
                "don't have guest",
                "no guest hai",
                "there isn't a guest",
            ]
        ) or lower_msg in ["no", "nope", "nah", "none", "n/a"]

        if is_negative_guest:
            checklist_dict["has_guest"] = False
            checklist_dict["guest_name"] = None
            checklist_dict["guest_title"] = None
            checklist_dict["guest_confirmed"] = False
            checklist_dict["guest_profile"] = None
        elif checklist_dict.get("has_guest") is None:
            if any(
                w in lower_msg
                for w in [
                    "guest is",
                    "speaker is",
                    "keynote by",
                    "dr.",
                    "mr.",
                    "ms.",
                    "featuring",
                    "guest speaker",
                ]
            ):
                checklist_dict["has_guest"] = True

        if not checklist_dict.get("category"):
            text_to_check = f"{user_message} {checklist_dict.get('campaign_name') or ''}".lower()

            def _has_word(*words: str) -> bool:
                return any(re.search(rf"\b{w}\b", text_to_check) for w in words)

            if _has_word(
                "seminar", "conference", "workshop", "bootcamp", "webinar", "meetup", "session"
            ):
                checklist_dict["category"] = "seminar"
            elif _has_word("launch", "product"):
                checklist_dict["category"] = "product_launch"
            elif _has_word("demo", "trial"):
                checklist_dict["category"] = "saas_demo"
            elif _has_word("sale", "discount", "offer", "deal"):
                checklist_dict["category"] = "ecommerce_sale"
            elif _has_word("course", "training", "enrollment", "enrolment", "class"):
                checklist_dict["category"] = "course_enrollment"

        if not checklist_dict.get("venue"):
            if any(
                w in lower_msg
                for w in ["online", "zoom", "google meet", "teams", "virtual", "remote"]
            ):
                checklist_dict["venue"] = "Online (Virtual)"
        if not checklist_dict.get("venue") and any(
            w in lower_msg
            for w in ["online", "zoom", "google meet", "teams", "virtual", "remote"]
        ):
            checklist_dict["venue"] = "Online (Virtual)"

        checklist = IntakeChecklist.model_validate(checklist_dict)

        history_formatted = "\n".join(
            f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in history[-8:]
        )

        # ── Pre-LLM Check: If already complete, bypass LLM entirely ──
        if checklist.is_complete():
            reply = "Thank you! All required details are gathered. You can now generate the plan."
            self._save_message(campaign_id, owner_id, "user", user_message, "en")
            self._save_message(campaign_id, owner_id, "assistant", reply, "en")
            return {
                "campaign_id": str(campaign_id),
                "reply": reply,
                "language": "en",
                "checklist": checklist,
                "is_complete": True,
                "guest_confirmation_needed": False,
                "guest_detected": None,
            }

        try:
            # ── DETERMINE COLLECTED AND MISSING FIELDS FOR PROMPT ──
            collected_labels = []
            for f, label in _FIELD_LABELS.items():
                val = checklist_dict.get(f)
                if _has_value(val):
                    collected_labels.append(f"- '{f}' ({label}): \"{val}\"")
            collected_text = "\n".join(collected_labels) if collected_labels else "None yet"

            missing_for_prompt = []
            for f in self._get_required_fields(checklist_dict):
                if f == "has_guest" and checklist_dict.get("has_guest") is False:
                    continue
                if not _has_value(checklist_dict.get(f)):
                    missing_for_prompt.append(f)

            if checklist_dict.get("has_guest") is True:
                if not _has_value(checklist_dict.get("guest_name")):
                    missing_for_prompt.insert(0, "guest_name")
                if not _has_value(checklist_dict.get("guest_title")):
                    missing_for_prompt.append("guest_title")

            missing_labels = [f"'{f}' ({_FIELD_LABELS.get(f, f)})" for f in missing_for_prompt]
            missing_text = (
                "\n".join(f"- {label}" for label in missing_labels) if missing_labels else "None"
            )

            # ── UNIFIED LLM CALL ──
            user_prompt = f"""
Recent Conversation:
{history_formatted}

User's Latest Message:
"{user_message}"

ALREADY COLLECTED INFORMATION (DO NOT ASK FOR THESE AGAIN!):
{collected_text}

CURRENTLY MISSING REQUIRED FIELDS (ONLY ASK FROM THIS LIST):
{missing_text}

Instructions:
1. Extract any newly provided info from the User's Latest Message into the 'extracted' JSON object.
2. NEVER ask for any information that is ALREADY COLLECTED or that the user just provided.
3. Write a friendly, conversational 'reply' that acknowledges what the user just provided and asks ONLY for the next 1 or 2 fields from the missing list.
"""

            logger.info("=== [INTAKE CHAT] Unified LLM Call Starting ===")
            logger.info("User Message: '%s'", user_message)
            logger.info("Missing Fields before extraction: %s", missing_for_prompt)

            llm_result = await self.llm.generate_json(
                _UNIFIED_INTAKE_PROMPT,
                user_prompt,
                # This is field extraction, not creative writing: live testing
                # showed the default temperature (0.7) makes the SAME message
                # extract different fields on different calls. Low, not zero,
                # so the natural-language 'reply' still reads conversationally.
                temperature=0.2,
                prefer_gemini=True,
            )

            logger.info("[INTAKE CHAT] Raw LLM Output: %s", json.dumps(llm_result))

            lang = llm_result.get("language", "en") if isinstance(llm_result, dict) else "en"

            unified = _coerce_unified_intake_response(llm_result)
            # Omitted fields must never erase confirmed state, so only values the
            # provider actually supplied are considered for the merge.
            extracted = unified.extracted.model_dump(exclude_none=True)
            reply = unified.reply

            logger.info("[INTAKE CHAT] Parsed Extracted Data: %s", json.dumps(extracted))

            campaign_type_unresolved: str | None = None

            for k, v in extracted.items():
                if v is not None and k in checklist_dict:
                    if isinstance(v, str):
                        v_clean = v.strip()
                        if v_clean.lower() in ("null", "none", "n/a", "undefined", ""):
                            continue
                        v = v_clean

                    if k == "campaign_type":
                        normalized_campaign_type = _normalize_campaign_type(v)
                        if normalized_campaign_type is None:
                            # Truthful: the value is not stored, and the reply below
                            # must not claim the campaign type was captured.
                            logger.warning("Unresolved campaign type from LLM: %r", v)
                            campaign_type_unresolved = str(v)
                            continue
                        v = normalized_campaign_type

                    if k == "objective":
                        # Preserve existing objective unless user explicitly requested changing it
                        if _has_value(checklist_dict.get("objective")) and not re.search(
                            r"\b(objective|goal|purpose|aim)\b", lower_msg
                        ):
                            continue

                        if explicit_objective:
                            v = explicit_objective
                        elif isinstance(v, str):
                            idx = user_message.lower().find(v.lower())
                            if idx != -1:
                                v = user_message[idx : idx + len(v)].strip()
                            elif (
                                not checklist.objective
                                and len(user_message.split()) <= 15
                                and not any(c in user_message for c in [":", "\n"])
                                and any(
                                    kw in history_formatted.lower()[-200:]
                                    for kw in ["objective", "goal", "trying to achieve"]
                                )
                            ):
                                v = user_message.strip()

                    if (
                        k == "guest_name"
                        and checklist.guest_name
                        and checklist.guest_name.lower() != str(v).lower()
                    ):
                        checklist_dict["guest_confirmed"] = False
                    checklist_dict[k] = v

            # Strictly enforce: if no guest, guest fields must remain None
            if checklist_dict.get("has_guest") is False or is_negative_guest:
                checklist_dict["has_guest"] = False
                checklist_dict["guest_name"] = None
                checklist_dict["guest_title"] = None
                checklist_dict["guest_confirmed"] = False
                checklist_dict["guest_profile"] = None

            # Strictly enforce: if ticket details are negated, unknown, or undecided, remains None
            if is_negative_or_unknown_ticket:
                checklist_dict["is_free_or_paid"] = None

            # No more fake fallbacks for outcome_deliverable

            # ── CAMPAIGN VALIDITY WINDOW: keep ranges out of event_date ──
            # A date range misfiled into event_date (a common small-model error,
            # and the proven production root cause) is moved to the validity
            # window and cleared from event_date.
            ed = checklist_dict.get("event_date")
            if isinstance(ed, str):
                ed_start, ed_end = _detect_campaign_window(ed)
                if ed_start and ed_end:
                    checklist_dict["campaign_start_date"] = ed_start.isoformat()
                    checklist_dict["campaign_end_date"] = ed_end.isoformat()
                    checklist_dict["event_date"] = None

            validity_error: str | None = None
            win_start_d = _parse_iso_date(checklist_dict.get("campaign_start_date"))
            win_end_d = _parse_iso_date(checklist_dict.get("campaign_end_date"))
            if win_start_d and win_end_d and win_start_d > win_end_d:
                # Reversed range: never silently persist or swap. Drop the invalid
                # pair so it is not treated as confirmed and ask for a correction.
                validity_error = (
                    "The campaign start date must be on or before the end date. "
                    "Could you re-share the campaign start and end dates?"
                )
                checklist_dict["campaign_start_date"] = None
                checklist_dict["campaign_end_date"] = None
                win_start_d = win_end_d = None
            else:
                # Normalize confirmed bounds to ISO strings in the checklist.
                if win_start_d:
                    checklist_dict["campaign_start_date"] = win_start_d.isoformat()
                if win_end_d:
                    checklist_dict["campaign_end_date"] = win_end_d.isoformat()

            updated_checklist = IntakeChecklist.model_validate(checklist_dict)
            updated_dict = updated_checklist.model_dump()

            # Authoritative scheduling bounds live on the campaign, not the
            # checklist: sync any confirmed window into campaign.schedule so the
            # existing PlanBrief path receives the correct start/end. Best-effort,
            # and only touches the schedule's start/end (timezone/recurrence and
            # other metadata are preserved).
            if win_start_d or win_end_d:
                self._sync_campaign_schedule_window(
                    campaign_id, owner_id, win_start_d, win_end_d
                )

            # ── COMPUTE REMAINING MISSING FIELDS AFTER EXTRACTION ──
            still_missing = []
            for f in self._get_required_fields(updated_dict):
                if f == "has_guest" and updated_dict.get("has_guest") is False:
                    continue
                if not _has_value(updated_dict.get(f)):
                    still_missing.append(f)

            if updated_dict.get("has_guest") is True:
                if not _has_value(updated_dict.get("guest_name")):
                    still_missing.insert(0, "guest_name")
                if not _has_value(updated_dict.get("guest_title")):
                    still_missing.append("guest_title")

            # ── DATA LOGGING AFTER EXTRACTION ──
            collected_state = {k: v for k, v in updated_dict.items() if _has_value(v)}
            logger.info("[INTAKE CHAT] Cumulative Checklist State: %s", json.dumps(collected_state))
            logger.info("[INTAKE CHAT] Still missing: %s", still_missing)
            logger.info("[INTAKE CHAT] Checklist Complete: %s", updated_checklist.is_complete())
            logger.info("=== [INTAKE CHAT] Unified LLM Call Finished ===")

            # ── POST-EXTRACTION OVERRIDE & ANTI-REPETITION GUARANTEE ──
            if validity_error is not None:
                # A reversed/invalid campaign window was rejected; ask truthfully.
                reply = validity_error
            elif campaign_type_unresolved is not None:
                # The provider supplied a campaign type we cannot map to a supported
                # value. Nothing was saved, so nothing may be acknowledged.
                reply = (
                    f"I could not match \"{campaign_type_unresolved}\" to a supported campaign "
                    f"type. Could you please share {_FIELD_LABELS['campaign_type']}?"
                )
            elif updated_checklist.is_complete() or len(still_missing) == 0:
                if is_negative_guest:
                    reply = "Understood! I have confirmed there is no guest speaker (solo host / team session). All required campaign details are gathered. You can now generate your campaign strategy and content!"
                else:
                    reply = "Thank you! All required campaign details have been gathered. You can now generate your campaign strategy and content!"
            else:
                # Check if the generated reply re-asks for any already collected field
                already_collected_keys = [
                    k
                    for k in self._get_all_relevant_fields(updated_dict)
                    if _has_value(updated_dict.get(k))
                ]
                reply_lower = reply.lower()
                field_question_keywords = {
                    "campaign_type": [
                        "type of campaign",
                        "campaign type",
                        "what kind of campaign",
                        "is it an app launch",
                    ],
                    "objective": [
                        "primary objective",
                        "campaign objective",
                        "what are you trying to achieve",
                        "what is the goal",
                    ],
                    "value_proposition": [
                        "value proposition",
                        "main features",
                        "core value",
                        "what makes it unique",
                    ],
                    "cta_url": [
                        "call to action",
                        "download link",
                        "signup url",
                        "where should we send them",
                    ],
                    "campaign_name": [
                        "name of the event",
                        "event name",
                        "name of your event",
                        "campaign name",
                        "what is the event",
                        "name of this event",
                    ],
                    "category": ["category of the event", "event category", "type of event"],
                    "target_audience": [
                        "target audience",
                        "who is this for",
                        "who is your audience",
                        "target demographic",
                    ],
                    "event_date": [
                        "what date",
                        "event date",
                        "when will it take place",
                        "when is the event",
                        "what time",
                        "date of the event",
                    ],
                    "venue": [
                        "where is the venue",
                        "what venue",
                        "location of the event",
                        "where will it be held",
                        "what is the venue",
                        "held at",
                    ],
                    "has_guest": [
                        "guest speaker",
                        "who is the speaker",
                        "is there a speaker",
                        "is there a guest",
                    ],
                    "is_free_or_paid": [
                        "is it free",
                        "ticket price",
                        "free or paid",
                        "admission fee",
                        "cost of admission",
                        "cost to attend",
                    ],
                    "curriculum_breakdown": [
                        "curriculum",
                        "topics covered",
                        "agenda of the event",
                        "topics will be",
                    ],
                }
                re_asking = False
                for key in already_collected_keys:
                    for kw in field_question_keywords.get(key, []):
                        if kw in reply_lower:
                            re_asking = True
                            break
                    if re_asking:
                        break

                if re_asking:
                    # Dynamically replace question so it asks ONLY for the actual next missing fields
                    next_items = still_missing[:2]
                    next_labels = [_FIELD_LABELS.get(f, f) for f in next_items]
                    if len(next_labels) == 1:
                        q_text = f"Could you please share {next_labels[0]}?"
                    else:
                        q_text = f"Could you please share {next_labels[0]} and {next_labels[1]}?"

                    if is_negative_guest:
                        reply = f"Understood, no guest speaker! Noted that this will be a solo host / internal team session. {q_text}"
                    elif any(_has_value(extracted.get(k)) for k in extracted):
                        reply = f"Got it, noted! {q_text}"
                    else:
                        reply = f"Thanks! {q_text}"

            guest_confirmation_needed = False
            guest_detected = None
            if (
                updated_checklist.has_guest is True
                and updated_checklist.guest_name
                and not updated_checklist.guest_confirmed
            ):
                guest_confirmation_needed = True
                guest_detected = {
                    "name": updated_checklist.guest_name,
                    "title": updated_checklist.guest_title or "",
                }

            self._save_message(campaign_id, owner_id, "user", user_message, lang)
            self._save_message(campaign_id, owner_id, "assistant", reply, lang)
            self._save_checklist(campaign_id, owner_id, updated_checklist)

            return {
                "campaign_id": str(campaign_id),
                "reply": reply,
                "language": lang,
                "checklist": updated_checklist,
                "is_complete": updated_checklist.is_complete(),
                "guest_confirmation_needed": guest_confirmation_needed,
                "guest_detected": guest_detected,
            }
        except IntakePersistenceError:
            raise
        except IntakeProcessingError:
            raise
        except Exception as e:
            logger.exception("Intake chat processing failed")
            raise IntakeProcessingError("Intake AI processing failed.") from e

    async def confirm_guest(
        self, campaign_id: UUID, owner_id: UUID, checklist: IntakeChecklist
    ) -> IntakeChecklist:
        checklist_dict = checklist.model_dump()
        checklist_dict["guest_confirmed"] = True
        updated = IntakeChecklist.model_validate(checklist_dict)
        self._save_checklist(campaign_id, owner_id, updated)
        return updated

    def _save_message(
        self,
        campaign_id: UUID,
        owner_id: UUID,
        role: str,
        content: str,
        language: str,
    ) -> None:
        cid = str(campaign_id)
        row = {
            "campaign_id": cid,
            "owner_id": str(owner_id),
            "role": role,
            "content": content,
            "language": language,
        }

        try:
            repo = BaseRepository("intake_messages")
            repo.client.table(repo.table_name).insert(row).execute()
        except Exception as e:
            raise IntakePersistenceError("Could not persist intake message.") from e

        self._local_history.setdefault(cid, []).append(row)

    def _sync_campaign_schedule_window(
        self,
        campaign_id: UUID,
        owner_id: UUID,
        start_day: date | None,
        end_day: date | None,
    ) -> None:
        """Write a confirmed validity window into the campaign's schedule bounds.

        Only ``start_date`` / ``end_date`` are changed; the existing timezone,
        recurrence_rule, and any other schedule metadata are preserved. If no
        real campaign row exists yet (e.g. a temporary intake session id), this
        is a no-op. Never raises — a validity-window sync failure must not fail
        the intake turn (the checklist still records the dates).
        """
        if start_day is None and end_day is None:
            return
        try:
            repo = BaseRepository("campaigns")
            res = (
                repo.client.table(repo.table_name)
                .select("schedule")
                .eq("id", str(campaign_id))
                .eq("organization_id", str(owner_id))
                .execute()
            )
        except Exception as e:
            logger.warning("Validity-window sync: could not load campaign schedule: %s", e)
            return

        if not res.data:
            # No persisted campaign row for this id yet — nothing authoritative
            # to update; the checklist still carries the confirmed window.
            return

        schedule = dict(res.data[0].get("schedule") or {})
        timezone = schedule.get("timezone") or "UTC"

        if start_day is not None:
            schedule["start_date"] = _date_to_schedule_iso(start_day, timezone)
        if end_day is not None:
            schedule["end_date"] = _date_to_schedule_iso(end_day, timezone)

        # Defensive: never persist a reversed window even after merging with an
        # existing bound; never silently swap.
        merged_start = _parse_iso_date(schedule.get("start_date"))
        merged_end = _parse_iso_date(schedule.get("end_date"))
        if merged_start and merged_end and merged_start > merged_end:
            logger.warning(
                "Validity-window sync: refusing reversed bounds start=%s end=%s",
                merged_start,
                merged_end,
            )
            return

        try:
            repo.client.table(repo.table_name).update({"schedule": schedule}).eq(
                "id", str(campaign_id)
            ).eq("organization_id", str(owner_id)).execute()
            logger.info(
                "Validity-window sync: campaign %s schedule start=%s end=%s (tz=%s preserved)",
                campaign_id,
                schedule.get("start_date"),
                schedule.get("end_date"),
                timezone,
            )
        except Exception as e:
            logger.warning("Validity-window sync: could not persist schedule: %s", e)

    def _save_checklist(
        self, campaign_id: UUID, owner_id: UUID, checklist: IntakeChecklist
    ) -> None:
        cid = str(campaign_id)
        try:
            repo = BaseRepository("intake_checklists")
            row = checklist.model_dump(mode="json")
            row["campaign_id"] = cid
            row["owner_id"] = str(owner_id)
            row["is_complete"] = checklist.is_complete()
            repo.client.table(repo.table_name).upsert(row, on_conflict="campaign_id").execute()
        except Exception as e:
            raise IntakePersistenceError("Could not persist intake checklist.") from e

        self._local_checklists[cid] = checklist

    async def get_history(self, campaign_id: UUID, owner_id: UUID) -> list[dict[str, Any]]:
        try:
            repo = BaseRepository("intake_messages")
            res = (
                repo.client.table(repo.table_name)
                .select("*")
                .eq("campaign_id", str(campaign_id))
                .eq("owner_id", str(owner_id))
                .order("created_at")
                .execute()
            )
            return res.data if res.data else []
        except Exception as e:
            logger.warning("DB failed, returning local history for %s: %s", campaign_id, e)
            return self._local_history.get(str(campaign_id), [])

    async def get_checklist(self, campaign_id: UUID, owner_id: UUID) -> IntakeChecklist:
        try:
            repo = BaseRepository("intake_checklists")
            res = (
                repo.client.table(repo.table_name)
                .select("*")
                .eq("campaign_id", str(campaign_id))
                .eq("owner_id", str(owner_id))
                .execute()
            )
            if res.data and len(res.data) > 0:
                return IntakeChecklist.model_validate(res.data[0])
            if str(campaign_id) in self._local_checklists:
                return self._local_checklists[str(campaign_id)]
        except Exception as e:
            logger.warning("DB failed, returning local checklist for %s: %s", campaign_id, e)
            if str(campaign_id) in self._local_checklists:
                return self._local_checklists[str(campaign_id)]

        return IntakeChecklist()

    def clear_session(self, campaign_id: UUID, owner_id: UUID) -> None:
        try:
            msg_repo = BaseRepository("intake_messages")
            msg_repo.client.table(msg_repo.table_name).delete().eq(
                "campaign_id", str(campaign_id)
            ).eq("owner_id", str(owner_id)).execute()
            chk_repo = BaseRepository("intake_checklists")
            chk_repo.client.table(chk_repo.table_name).delete().eq(
                "campaign_id", str(campaign_id)
            ).eq("owner_id", str(owner_id)).execute()
            logger.info("Cleared intake session for %s", campaign_id)
        except Exception as e:
            raise IntakePersistenceError("Could not clear intake session.") from e

        self._local_history.pop(str(campaign_id), None)
        self._local_checklists.pop(str(campaign_id), None)
