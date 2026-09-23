"""LLM service for guest profile analysis.

Talks to the same OpenAI-compatible endpoint as the rest of the app
(LLM_BASE_URL / LLM_MODEL / LLM_API_KEY). JSON is extracted from the
completion text rather than requested via the `json_schema` response format,
so small local models that lack that extension still work.
"""

import json
import logging
import re
from typing import Any

from openai import OpenAI

from src.config.settings import settings
from src.models.guest_profile import ConfidenceLevel, GuestProfile

logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM_PROMPT = """\
You are a research assistant that analyzes web search result metadata to build structured guest/speaker profiles.

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

IMPORTANT: Respond with ONLY a valid JSON object — no markdown, no code fences, no extra text. The JSON must have these exact keys:
{
  "full_name": "",
  "current_position": "",
  "organization": "",
  "professional_biography": "",
  "areas_of_expertise": [],
  "confidence_level": "LOW"
}"""


class LLMError(Exception):
    pass


def _extract_json(text: str) -> dict[str, Any]:
    """Extract a JSON object from LLM output, stripping markdown fences if present."""
    # Strip <think> tags and their contents (used by reasoning models)
    text = re.sub(r"<think>[\s\S]*?</think>", "", text)

    # Strip ```json ... ``` or ``` ... ``` fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        text = fenced.group(1)

    # Find the outermost { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMError(f"No JSON object found in LLM response: {text[:300]!r}")
    return json.loads(text[start : end + 1])


class LLMService:
    def __init__(self, client: OpenAI | None = None):
        if client is not None:
            self._client = client
        else:
            self._client = OpenAI(
                api_key=settings.llm_api_key or "ollama",
                base_url=(settings.llm_base_url or "").strip().rstrip("/"),
            )

        self._model = settings.llm_model

    def analyze_search_results(
        self, results: list[dict[str, Any]], campaign_context: str = ""
    ) -> GuestProfile:
        context = json.dumps(results, indent=2)
        ctx_prompt = f"Event/Campaign Context: {campaign_context}\n\n" if campaign_context else ""
        user_message = f"{ctx_prompt}Analyze the following search results and build a guest profile:\n\n{context}"

        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=4000,
            )
        except Exception as e:
            raise LLMError(f"LLM analysis failed: {e}") from e

        try:
            raw_text = completion.choices[0].message.content or ""
            if not raw_text.strip():
                raise LLMError(
                    "Model returned an empty response. "
                    "Try a different model or check your OpenRouter API key/quota."
                )
            data = _extract_json(raw_text)
        except (json.JSONDecodeError, LLMError) as e:
            raise LLMError(f"Could not parse LLM JSON response: {e}") from e

        # Normalise confidence_level — accept any capitalisation
        raw_conf = str(data.get("confidence_level", "LOW")).upper()
        try:
            conf = ConfidenceLevel(raw_conf)
        except ValueError:
            conf = ConfidenceLevel.LOW

        return GuestProfile(
            full_name=str(data.get("full_name") or ""),
            current_position=str(data.get("current_position") or ""),
            organization=str(data.get("organization") or ""),
            professional_biography=str(data.get("professional_biography") or ""),
            areas_of_expertise=list(data.get("areas_of_expertise") or []),
            confidence_level=conf,
        )
