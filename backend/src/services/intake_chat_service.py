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
You are a campaign requirements gathering agent and data extractor.

Your job is to read the user's latest message, extract any provided campaign details into JSON, and then write a conversational reply asking for the NEXT missing fields.

RULES:
1. Extract data accurately. If the user answered a question, extract it into the relevant field. Leave unmentioned fields as null.
2. After extracting, look at the required fields list provided below. Determine which fields are STILL MISSING.
3. Your `reply` must be a friendly, conversational question asking the user to provide the next 2 or 3 missing fields. Do not ask for more than 3 things at once.
4. If all required fields are collected, your `reply` should confirm that all requirements are gathered and invite the user to proceed.
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
  "reply": "Your friendly conversational question asking for 2-3 missing fields."
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
        "event_name", "category", "target_audience", "event_date", "venue",
        "has_guest", "curriculum_breakdown", "outcome_deliverable",
        "is_free_or_paid", "registration_link",
    ]

    def __init__(self, llm: LLMRouterService | None = None) -> None:
        self.llm = llm or LLMRouterService()




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
        lower_msg = user_message.lower()

        # ── Deterministic pre-extraction (unchanged from before) ──
        url_match = re.search(r'https?://[^\s]+', user_message)
        if url_match and not checklist_dict.get("registration_link"):
            checklist_dict["registration_link"] = url_match.group(0)

        if not checklist_dict.get("is_free_or_paid"):
            if any(w in lower_msg for w in ["free", "no fee", "kharcha nahi", "koi fee nahi", "free of cost"]):
                checklist_dict["is_free_or_paid"] = "Free"
            elif any(w in lower_msg for w in ["paid", "ticketed", "ticket", "fee hai", "kharcha hai"]):
                checklist_dict["is_free_or_paid"] = "Paid"

        if checklist_dict.get("has_guest") is None:
            if any(w in lower_msg for w in ["no guest", "guest nahi", "no speaker", "speaker nahi", "koi guest nahi"]):
                checklist_dict["has_guest"] = False

        if not checklist_dict.get("category"):
            text_to_check = f"{user_message} {checklist_dict.get('event_name') or ''}".lower()

            def _has_word(*words: str) -> bool:
                return any(re.search(rf"\b{w}\b", text_to_check) for w in words)

            if _has_word("seminar", "conference", "workshop", "bootcamp", "webinar"):
                checklist_dict["category"] = "seminar"
            elif _has_word("launch"):
                checklist_dict["category"] = "product_launch"
            elif _has_word("demo", "trial"):
                checklist_dict["category"] = "saas_demo"
            elif _has_word("sale", "discount", "offer"):
                checklist_dict["category"] = "ecommerce_sale"
            elif _has_word("course", "training", "enrollment", "enrolment"):
                checklist_dict["category"] = "course_enrollment"

        checklist = IntakeChecklist.model_validate(checklist_dict)

        def _has_value(val: Any) -> bool:
            if val is None:
                return False
            if isinstance(val, bool):
                return True
            if isinstance(val, str):
                return val.strip().lower() not in ("", "null", "none", "n/a", "undefined")
            return True

        history_formatted = "\n".join(
            f"{m.get('role', 'user').upper()}: {m.get('content', '')}"
            for m in history[-8:]
        )

        try:
            # ── DETERMINE MISSING FIELDS FOR PROMPT ──
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
            missing_text = "\n".join(f"- {label}" for label in missing_labels) if missing_labels else "None"

            # ── UNIFIED LLM CALL ──
            user_prompt = f"""
Recent Conversation:
{history_formatted}

User's Latest Message:
"{user_message}"

Currently Missing Required Fields:
{missing_text}

Instructions:
1. Extract any newly provided info from the user's latest message into the 'extracted' JSON object.
2. Look at what is STILL missing after your extraction.
3. Generate a conversational 'reply' asking the user to provide the NEXT 2 or 3 missing fields.
"""

            logger.info("=== [INTAKE CHAT] Unified LLM Call Starting ===")
            logger.info("User Message: '%s'", user_message)
            logger.info("Missing Fields before extraction: %s", missing_for_prompt)

            llm_result = await self.llm.generate_json(_UNIFIED_INTAKE_PROMPT, user_prompt, prefer_gemini=True)

            logger.info("[INTAKE CHAT] Raw LLM Output: %s", json.dumps(llm_result))

            lang = llm_result.get("language", "en")
            extracted = llm_result.get("extracted", {})
            reply = llm_result.get("reply", "Great! Could you share the next detail for your campaign?")

            logger.info("[INTAKE CHAT] Parsed Extracted Data: %s", json.dumps(extracted))
            logger.info("[INTAKE CHAT] LLM Generated Reply: '%s'", reply)

            for k, v in extracted.items():
                if v is not None and k in checklist_dict:
                    if isinstance(v, str):
                        v_clean = v.strip()
                        if v_clean.lower() in ("null", "none", "n/a", "undefined", ""):
                            continue
                        v = v_clean
                    if k == "guest_name" and checklist.guest_name and checklist.guest_name.lower() != str(v).lower():
                        checklist_dict["guest_confirmed"] = False
                    checklist_dict[k] = v

            if checklist_dict.get("curriculum_breakdown") and not _has_value(checklist_dict.get("outcome_deliverable")):
                checklist_dict["outcome_deliverable"] = f"Mastery in {checklist_dict['curriculum_breakdown']}"

            updated_checklist = IntakeChecklist.model_validate(checklist_dict)
            updated_dict = updated_checklist.model_dump()

            # ── DATA LOGGING AFTER EXTRACTION ──
            collected_state = {k: v for k, v in updated_dict.items() if _has_value(v)}
            logger.info("[INTAKE CHAT] Cumulative Checklist State: %s", json.dumps(collected_state))
            logger.info("[INTAKE CHAT] Checklist Complete: %s", updated_checklist.is_complete())
            logger.info("=== [INTAKE CHAT] Unified LLM Call Finished ===")

            guest_confirmation_needed = False
            guest_detected = None
            if updated_checklist.has_guest is True and updated_checklist.guest_name and not updated_checklist.guest_confirmed:
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
            fallback_reply = (
                "Got it! Could you please share the target audience for this event?"
            )
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
        try:
            repo = BaseRepository("intake_messages")
            row = {"campaign_id": str(campaign_id), "role": role, "content": content, "language": language}
            repo.client.table(repo.table_name).insert(row).execute()
        except Exception as e:
            logger.warning("Could not save intake message to DB: %s", e)

    def _save_checklist(self, campaign_id: UUID, checklist: IntakeChecklist) -> None:
        try:
            repo = BaseRepository("intake_checklists")
            row = checklist.model_dump()
            row["campaign_id"] = str(campaign_id)
            row["is_complete"] = checklist.is_complete()
            repo.client.table(repo.table_name).upsert(row, on_conflict="campaign_id").execute()
        except Exception as e:
            logger.warning("Could not save intake checklist to DB: %s", e)

    async def get_history(self, campaign_id: UUID) -> list[dict[str, Any]]:
        repo = BaseRepository("intake_messages")
        res = repo.client.table(repo.table_name).select("*").eq("campaign_id", str(campaign_id)).order("created_at").execute()
        return res.data if res.data else []

    async def get_checklist(self, campaign_id: UUID) -> IntakeChecklist:
        repo = BaseRepository("intake_checklists")
        res = repo.client.table(repo.table_name).select("*").eq("campaign_id", str(campaign_id)).execute()
        if res.data and len(res.data) > 0:
            return IntakeChecklist.model_validate(res.data[0])
        return IntakeChecklist()

    def clear_session(self, campaign_id: UUID) -> None:
        try:
            msg_repo = BaseRepository("intake_messages")
            msg_repo.client.table(msg_repo.table_name).delete().eq("campaign_id", str(campaign_id)).execute()
            chk_repo = BaseRepository("intake_checklists")
            chk_repo.client.table(chk_repo.table_name).delete().eq("campaign_id", str(campaign_id)).execute()
            logger.info("Cleared intake session for %s", campaign_id)
        except Exception as e:
            logger.warning("Could not clear session DB records: %s", e)
