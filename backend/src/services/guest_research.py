from typing import Protocol

from exa_py import Exa

from src.models.guest_profile import GuestEvidence


class GuestResearchProvider(Protocol):
    async def search(self, query: str) -> list[GuestEvidence]: ...


class ExaGuestResearchProvider:
    def __init__(self, api_key: str):
        self.exa = Exa(api_key=api_key)

    async def search(self, query: str) -> list[GuestEvidence]:
        # Perform semantic web retrieval using Exa search endpoint
        # Use highlights for extracting facts
        result = self.exa.search(query=query, type="auto", contents={"highlights": True})

        evidence_list = []
        for item in result.results:
            evidence = GuestEvidence(
                url=item.url,
                title=item.title or "",
                highlights=(
                    item.highlights if hasattr(item, "highlights") and item.highlights else []
                ),
            )
            evidence_list.append(evidence)

        return evidence_list
