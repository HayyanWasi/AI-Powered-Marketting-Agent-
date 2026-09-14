import json
import logging

from src.cache.cache import SessionCache
from src.models.guest_profile import GuestEvidence, GuestProfile
from src.services.guest_research import GuestResearchProvider
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class GuestProfileService:
    def __init__(
        self,
        research_provider: GuestResearchProvider,
        llm_service: LLMService,
        cache: SessionCache,
    ):
        self.research_provider = research_provider
        self.llm_service = llm_service
        self.cache = cache

    def _get_cache_key(self, guest_name: str, company_name: str | None = None) -> str:
        base = guest_name.lower().strip()
        if company_name:
            base += f"_{company_name.lower().strip()}"
        return f"guest_profile_{base}"

    async def get_fresh_profile(
        self,
        session_id: str,
        guest_name: str,
        company_name: str | None = None,
        force_refresh: bool = False,
    ) -> GuestProfile:
        # 1. Check cache
        cache_key = self._get_cache_key(guest_name, company_name)
        if not force_refresh:
            cached_data, found = self.cache.get_data(session_id, cache_key)
            if found and isinstance(cached_data, dict):
                # Try to parse from cache
                try:
                    profile = GuestProfile(**cached_data)
                    logger.info(f"Cache hit for guest {guest_name}")
                    return profile
                except Exception as e:
                    logger.warning(f"Failed to parse cached profile for {guest_name}: {e}")

        # 2. Research with Exa
        logger.info(f"Cache miss for guest {guest_name}, starting research")
        # Optimized query for finding professional profiles and skills, even for less famous individuals
        query = f"professional profile, biography, and areas of expertise for {guest_name}"
        if company_name:
            query += f" at {company_name}"

        try:
            evidence_list = await self.research_provider.search(query)
        except Exception as e:
            logger.error(f"Research provider failed: {e}")
            evidence_list = []

        # 3. Synthesize with LLM
        if not evidence_list:
            # Fallback if no evidence found
            profile = GuestProfile(
                full_name=guest_name,
                organization=company_name or "",
                professional_biography="No information found.",
                confidence_level="LOW",
            )
        else:
            profile = self._synthesize_profile(guest_name, company_name, evidence_list)

        # 4. Save to cache
        self.cache.store_data(session_id, cache_key, profile.model_dump())

        return profile

    def _synthesize_profile(
        self, guest_name: str, company_name: str | None, evidence: list[GuestEvidence]
    ) -> GuestProfile:
        # Build strict structured JSON prompt
        MAX_EVIDENCE_CHARS = 10000
        evidence_text = "\n\n".join(
            f"Source URL: {e.url}\nTitle: {e.title}\nHighlights:\n"
            + "\n".join(f"- {h}" for h in e.highlights)
            for e in evidence[:5]  # Limit to 5 sources
        )
        if len(evidence_text) > MAX_EVIDENCE_CHARS:
            evidence_text = evidence_text[:MAX_EVIDENCE_CHARS] + "\n...[TRUNCATED]"

        # We enforce JSON output
        system_prompt = (
            "You are a strict data extraction assistant. "
            "You must extract information about the requested person ONLY from the provided evidence. "
            "DO NOT invent facts, credentials, or history not present in the evidence. "
            "Output valid JSON matching this schema:\n"
            "{\n"
            '  "full_name": "string",\n'
            '  "current_position": "string",\n'
            '  "organization": "string",\n'
            '  "professional_biography": "string (concise summary)",\n'
            '  "areas_of_expertise": ["string", "string"],\n'
            '  "confidence_level": "HIGH" | "MEDIUM" | "LOW"\n'
            "}"
        )

        user_prompt = (
            f"Person: {guest_name}\n"
            f"Company: {company_name or 'N/A'}\n\n"
            f"Evidence:\n{evidence_text}"
        )

        try:
            from src.models.llm import LLMRequest

            # Assume LLMService has generate method
            response = self.llm_service.generate(
                LLMRequest(system_prompt=system_prompt, user_prompt=user_prompt)
            )

            # Parse response.text as JSON
            # Clean possible markdown block
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            data = json.loads(text.strip())

            # Attach evidence back
            profile = GuestProfile(**data, evidence=evidence)
            return profile
        except Exception as e:
            logger.error(f"Failed to synthesize profile for {guest_name}: {e}")
            # Fallback profile
            return GuestProfile(
                full_name=guest_name,
                organization=company_name or "",
                professional_biography="Error parsing synthesis.",
                confidence_level="LOW",
                evidence=evidence,
            )
