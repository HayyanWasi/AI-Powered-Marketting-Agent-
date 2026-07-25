import json
import logging
from typing import Any

from openai import OpenAI

from src.config.settings import settings
from src.models.guest_profile import GuestProfileData

logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM_PROMPT = """You are a research assistant that analyzes web search result metadata to build structured guest/speaker profiles.

Given a list of search results (each with page title, snippet, and URL), extract the following information about the person being searched:

- full_name: The person's full name
- current_position: Their current professional role or title
- organization: The company or organization they currently work for
- professional_biography: A concise 2-4 sentence biography summarizing only information supported by the provided search results
- areas_of_expertise: A list of topics or fields they are knowledgeable in
- confidence_level: HIGH if information is consistent across multiple (>=3) sources and corroborated, MEDIUM if some corroboration exists (2 sources), LOW if only a single source or conflicting information
- sources_used: The search results that contributed to the profile (include those used for each piece of information)

Rules:
1. Only use information present in the provided search results. NEVER invent or assume missing information.
2. If a field cannot be determined from the provided results, leave it as an empty string or empty list.
3. If results contain conflicting information, prefer information appearing consistently across multiple results.
4. If conflicts cannot be resolved, lower the confidence level.
5. Duplicate information from multiple sources should be merged into a single coherent entry."""


class LLMError(Exception):
    pass


class LLMService:
    def __init__(self, client: OpenAI | None = None):
        if client is not None:
            self._client = client
        else:
            self._client = OpenAI(
                api_key=settings.grok_api_key,
                base_url="https://api.groq.com/openai/v1",
            )

    def analyze_search_results(self, results: list[dict[str, Any]]) -> GuestProfileData:
        context = json.dumps(results, indent=2)
        user_message = (
            f"Analyze the following search results and build a guest profile:\n\n{context}"
        )

        try:
            completion = self._client.chat.completions.parse(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                response_format=GuestProfileData,
            )

            message = completion.choices[0].message
            if message.parsed is not None:
                return message.parsed
            if message.refusal:
                raise LLMError(f"LLM refused to analyze results: {message.refusal}")

            raise LLMError("LLM returned no parsed data and no refusal")
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"LLM analysis failed: {e}") from e
