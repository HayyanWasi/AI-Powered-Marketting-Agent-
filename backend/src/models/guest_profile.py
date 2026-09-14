from enum import StrEnum

from pydantic import BaseModel, Field


class ConfidenceLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class GuestEvidence(BaseModel):
    url: str = Field(..., description="Source URL")
    title: str = Field(default="", description="Page title")
    highlights: list[str] = Field(
        default_factory=list, description="Extracted relevant text chunks"
    )


class GuestProfile(BaseModel):
    full_name: str = Field(..., description="Guest's full name")
    current_position: str = Field(default="", description="Current professional role/title")
    organization: str = Field(default="", description="Current company/organization")
    professional_biography: str = Field(default="", description="Concise summary of background")
    areas_of_expertise: list[str] = Field(default_factory=list, description="Areas of expertise")
    confidence_level: ConfidenceLevel = Field(
        default=ConfidenceLevel.LOW, description="Overall confidence"
    )
    evidence: list[GuestEvidence] = Field(default_factory=list, description="Supporting evidence")


class GuestSearchRequest(BaseModel):
    guest_name: str = Field(..., min_length=1, description="Full name of the guest/speaker")
    company_name: str | None = Field(default=None, description="Company/organization name")
    session_id: str | None = Field(default=None, description="Existing session ID")


class GuestSearchResponse(BaseModel):
    profile: GuestProfile | None = Field(default=None)
    needs_manual_input: bool = Field(default=False)
    error: str = Field(default="")
