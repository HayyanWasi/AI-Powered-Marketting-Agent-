from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import BaseModel, Field


class ConfidenceLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SearchResultData(BaseModel):
    website_name: str = Field(default="", description="Name of the website hosting the result")
    page_title: str = Field(default="", description="Title of the search result page")
    snippet: str = Field(default="", description="Search description/snippet")
    source_url: str = Field(default="", description="Full URL of the search result")


@dataclass
class SearchResult:
    website_name: str = ""
    page_title: str = ""
    snippet: str = ""
    source_url: str = ""

    def to_data(self) -> SearchResultData:
        return SearchResultData(
            website_name=self.website_name,
            page_title=self.page_title,
            snippet=self.snippet,
            source_url=self.source_url,
        )


class GuestProfileData(BaseModel):
    full_name: str = Field(default="", description="Guest's full name")
    current_position: str = Field(default="", description="Current professional role/title")
    organization: str = Field(default="", description="Current company/organization")
    professional_biography: str = Field(default="", description="Concise summary of background")
    areas_of_expertise: list[str] = Field(default_factory=list, description="Areas of expertise")
    confidence_level: ConfidenceLevel = Field(
        default=ConfidenceLevel.LOW, description="Overall confidence"
    )
    sources_used: list[SearchResultData] = Field(
        default_factory=list, description="Search results used"
    )


@dataclass
class GuestProfile:
    full_name: str = ""
    current_position: str = ""
    organization: str = ""
    professional_biography: str = ""
    areas_of_expertise: list[str] = field(default_factory=list)
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    sources_used: list[SearchResult] = field(default_factory=list)

    def to_response(self) -> GuestProfileData:
        return GuestProfileData(
            full_name=self.full_name,
            current_position=self.current_position,
            organization=self.organization,
            professional_biography=self.professional_biography,
            areas_of_expertise=list(self.areas_of_expertise),
            confidence_level=self.confidence_level,
            sources_used=[s.to_data() for s in self.sources_used],
        )


class GuestSearchRequest(BaseModel):
    guest_name: str = Field(..., min_length=1, description="Full name of the guest/speaker")
    company_name: str | None = Field(default=None, description="Company/organization name")
    session_id: str | None = Field(default=None, description="Existing session ID")


class GuestSearchResponse(BaseModel):
    profile: GuestProfileData = Field(default_factory=GuestProfileData)
    needs_manual_input: bool = Field(default=False)
    error: str = Field(default="")
