from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class CompanyProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, pattern=r".*\S.*")
    tone: str = Field(..., min_length=1, max_length=1000, pattern=r".*\S.*")


class CompanyProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255, pattern=r".*\S.*")
    tone: str | None = Field(default=None, min_length=1, max_length=1000, pattern=r".*\S.*")


class CompanyProfileResponse(BaseModel):
    id: str
    name: str
    tone: str
    reference_image_urls: list[str]
    created_at: str
    updated_at: str


@dataclass
class CompanyProfile:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    tone: str = ""
    reference_image_urls: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_response(self) -> CompanyProfileResponse:
        return CompanyProfileResponse(
            id=self.id,
            name=self.name,
            tone=self.tone,
            reference_image_urls=self.reference_image_urls,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
