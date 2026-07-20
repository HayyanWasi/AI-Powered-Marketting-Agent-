from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class CompanyProfileCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255, pattern=r".*\S.*")
    brand_guidelines: str = Field(..., min_length=1, max_length=5000, pattern=r".*\S.*")
    brand_tone: str | None = Field(default=None, min_length=1, max_length=1000, pattern=r".*\S.*")


class CompanyProfileUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=255, pattern=r".*\S.*")
    brand_guidelines: str | None = Field(
        default=None, min_length=1, max_length=5000, pattern=r".*\S.*"
    )
    brand_tone: str | None = Field(default=None, min_length=1, max_length=1000, pattern=r".*\S.*")


class CompanyProfileResponse(BaseModel):
    id: str
    company_name: str
    brand_guidelines: str
    brand_tone: str | None = None
    reference_image_urls: list[str]
    created_at: str
    updated_at: str


class CompanyProfileListResponse(BaseModel):
    id: str
    company_name: str
    is_complete: bool
    image_count: int
    updated_at: str


@dataclass
class CompanyProfile:
    id: str = field(default_factory=lambda: str(uuid4()))
    company_name: str = ""
    brand_guidelines: str = ""
    brand_tone: str | None = None
    reference_image_urls: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_response(self) -> CompanyProfileResponse:
        return CompanyProfileResponse(
            id=self.id,
            company_name=self.company_name,
            brand_guidelines=self.brand_guidelines,
            brand_tone=self.brand_tone,
            reference_image_urls=self.reference_image_urls,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @property
    def is_complete(self) -> bool:
        return bool(self.company_name and self.brand_guidelines)
