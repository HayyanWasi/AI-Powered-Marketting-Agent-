"""Intake Chat Service — Conversational Campaign Requirement Gathering & Parameter Extraction."""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from uuid import UUID

from src.models.intake import IntakeChecklist
from src.modules.research.services.llm_router import LLMRouterService
from src.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

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

JSON OUTPUT SCHEMA:
{
  "extracted": {
    "event_name": string or null,
    "category": string or null,
    "event_date": string or null,
    "venue": string or null,
    "has_guest": boolean or null,
    "guest_name": string or null,
    "guest_title": string or null,
    "curriculum_breakdown": string or null,
    "outcome_deliverable": string or null,
    "is_free_or_paid": string or null,
    "registration_link": string or null,
    "target_audience": string or null
  },
  "reply": "Friendly response acknowledging newly provided info and asking ONLY for the next 1-2 still-missing fields."
}
"""


_FIELD_LABELS: dict[str, str] = {
    "event_name": "the event or campaign name",
    "category": "the event category (seminar, product launch, sale, demo, course)",
    "target_audience": "the target audience",
    "event_date": "the event date",
    "venue": "the venue",
    "has_guest": "whether there is a guest speaker",
    "guest_name": "the guest speaker's name",
    "guest_title": "the guest speaker's title or designation",
    "curriculum_breakdown": "the curriculum or content breakdown",
    "outcome_deliverable": "the key outcome or deliverable for attendees",
    "is_free_or_paid": "whether the event is free or paid",
    "registration_link": "the registration link",
}


class IntakeChatService:
    """Service driving the intake chat conversation and parameter accumulation."""

    # Order matters — this IS the question order. Python owns this decision.
    REQUIRED_FIELDS = [
        "event_name",
        "category",
        "target_audience",
        "event_date",
        "venue",
        "has_guest",
        "curriculum_breakdown",
        "outcome_deliverable",
        "is_free_or_paid",
        "registration_link",
    ]

    def __init__(self, llm: LLMRouterService | None = None) -> None:
        self.llm = llm or LLMRouterService()
        self._local_history: dict[str, list[dict[str, Any]]] = {}
        self._local_checklists: dict[str, IntakeChecklist] = {}

    async def process_chat_turn(
        self,
        campaign_id: UUID,
        user_message: str,
        history: list[dict[str, str]],
        current_checklist: IntakeChecklist | None = None,
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

        if not checklist_dict.get("is_free_or_paid"):
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
                ]
            ):
                checklist_dict["is_free_or_paid"] = "Free"
            elif any(
                w in lower_msg
                for w in [
                    "paid",
                    "ticketed",
                    "ticket",
                    "fee hai",
                    "kharcha hai",
                    "$",
                    "pkr",
                    "usd",
                    "rs.",
                    "price",
                    "admission fee",
                ]
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
            text_to_check = f"{user_message} {checklist_dict.get('event_name') or ''}".lower()

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

        checklist = IntakeChecklist.model_validate(checklist_dict)

        history_formatted = "\n".join(
            f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in history[-8:]
        )

        # ── Pre-LLM Check: If already complete, bypass LLM entirely ──
        if checklist.is_complete():
            reply = "Thank you! All required details are gathered. You can now generate the plan."
            self._save_message(campaign_id, "user", user_message, "en")
            self._save_message(campaign_id, "assistant", reply, "en")
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
            for f in self.REQUIRED_FIELDS:
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
                _UNIFIED_INTAKE_PROMPT, user_prompt, prefer_gemini=True
            )

            logger.info("[INTAKE CHAT] Raw LLM Output: %s", json.dumps(llm_result))

            lang = llm_result.get("language", "en")
            extracted = llm_result.get("extracted", {})
            reply = llm_result.get(
                "reply", "Great! Could you share the next detail for your campaign?"
            )

            logger.info("[INTAKE CHAT] Parsed Extracted Data: %s", json.dumps(extracted))

            for k, v in extracted.items():
                if v is not None and k in checklist_dict:
                    if isinstance(v, str):
                        v_clean = v.strip()
                        if v_clean.lower() in ("null", "none", "n/a", "undefined", ""):
                            continue
                        v = v_clean
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

            if checklist_dict.get("curriculum_breakdown") and not _has_value(
                checklist_dict.get("outcome_deliverable")
            ):
                checklist_dict["outcome_deliverable"] = (
                    f"Mastery in {checklist_dict['curriculum_breakdown']}"
                )

            updated_checklist = IntakeChecklist.model_validate(checklist_dict)
            updated_dict = updated_checklist.model_dump()

            # ── COMPUTE REMAINING MISSING FIELDS AFTER EXTRACTION ──
            still_missing = []
            for f in self.REQUIRED_FIELDS:
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
            if updated_checklist.is_complete() or len(still_missing) == 0:
                if is_negative_guest:
                    reply = "Understood! I have confirmed there is no guest speaker (solo host / team session). All required campaign details are gathered. You can now generate your campaign strategy and content!"
                else:
                    reply = "Thank you! All required campaign details have been gathered. You can now generate your campaign strategy and content!"
            else:
                # Check if the generated reply re-asks for any already collected field
                already_collected_keys = [
                    k for k in self.REQUIRED_FIELDS if _has_value(updated_dict.get(k))
                ]
                reply_lower = reply.lower()
                field_question_keywords = {
                    "event_name": [
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

            self._save_message(campaign_id, "user", user_message, lang)
            self._save_message(campaign_id, "assistant", reply, lang)
            self._save_checklist(campaign_id, updated_checklist)

            return {
                "campaign_id": str(campaign_id),
                "reply": reply,
                "language": lang,
                "checklist": updated_checklist,
                "is_complete": updated_checklist.is_complete(),
                "guest_confirmation_needed": guest_confirmation_needed,
                "guest_detected": guest_detected,
            }
        except Exception as e:
            logger.error("Intake chat processing failed: %s", e)
            still_missing = [
                f for f in self.REQUIRED_FIELDS if not _has_value(checklist_dict.get(f))
            ]
            if checklist_dict.get("has_guest") is False and "has_guest" in still_missing:
                still_missing.remove("has_guest")

            if not still_missing or checklist.is_complete():
                fallback_reply = "Thank you! All required details are gathered. You can now generate your campaign plan."
            else:
                next_label = _FIELD_LABELS.get(still_missing[0], still_missing[0])
                fallback_reply = f"Got it, noted! Could you please share {next_label}?"

            return {
                "campaign_id": str(campaign_id),
                "reply": fallback_reply,
                "language": "en",
                "checklist": checklist,
                "is_complete": checklist.is_complete(),
                "guest_confirmation_needed": False,
                "guest_detected": None,
            }

    async def confirm_guest(self, campaign_id: UUID, checklist: IntakeChecklist) -> IntakeChecklist:
        checklist_dict = checklist.model_dump()
        checklist_dict["guest_confirmed"] = True
        updated = IntakeChecklist.model_validate(checklist_dict)
        self._save_checklist(campaign_id, updated)
        return updated

    def _save_message(self, campaign_id: UUID, role: str, content: str, language: str) -> None:
        cid = str(campaign_id)
        if cid not in self._local_history:
            self._local_history[cid] = []

        row = {
            "campaign_id": cid,
            "role": role,
            "content": content,
            "language": language,
        }
        self._local_history[cid].append(row)

        try:
            repo = BaseRepository("intake_messages")
            repo.client.table(repo.table_name).insert(row).execute()
        except Exception as e:
            logger.warning("Could not save intake message to DB (using local cache): %s", e)

    def _save_checklist(self, campaign_id: UUID, checklist: IntakeChecklist) -> None:
        cid = str(campaign_id)
        self._local_checklists[cid] = checklist

        try:
            repo = BaseRepository("intake_checklists")
            row = checklist.model_dump()
            row["campaign_id"] = cid
            row["is_complete"] = checklist.is_complete()
            repo.client.table(repo.table_name).upsert(row, on_conflict="campaign_id").execute()
        except Exception as e:
            logger.warning("Could not save intake checklist to DB (using local cache): %s", e)

    async def get_history(self, campaign_id: UUID) -> list[dict[str, Any]]:
        try:
            repo = BaseRepository("intake_messages")
            res = (
                repo.client.table(repo.table_name)
                .select("*")
                .eq("campaign_id", str(campaign_id))
                .order("created_at")
                .execute()
            )
            return res.data if res.data else []
        except Exception as e:
            logger.warning("DB failed, returning local history for %s: %s", campaign_id, e)
            return self._local_history.get(str(campaign_id), [])

    async def get_checklist(self, campaign_id: UUID) -> IntakeChecklist:
        try:
            repo = BaseRepository("intake_checklists")
            res = (
                repo.client.table(repo.table_name)
                .select("*")
                .eq("campaign_id", str(campaign_id))
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

    def clear_session(self, campaign_id: UUID) -> None:
        try:
            msg_repo = BaseRepository("intake_messages")
            msg_repo.client.table(msg_repo.table_name).delete().eq(
                "campaign_id", str(campaign_id)
            ).execute()
            chk_repo = BaseRepository("intake_checklists")
            chk_repo.client.table(chk_repo.table_name).delete().eq(
                "campaign_id", str(campaign_id)
            ).execute()
            logger.info("Cleared intake session for %s", campaign_id)
        except Exception as e:
            logger.warning("Could not clear session DB records: %s", e)
