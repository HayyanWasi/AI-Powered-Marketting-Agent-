from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl


class CampaignCreate(BaseModel):
    type: str = Field(..., min_length=1)
    caption: str = Field(..., min_length=1, pattern=r".*\S.*")
    image_url: HttpUrl | None = None
    status: str = Field(default="draft", pattern=r"^(draft|published|archived)$")


class CampaignUpdate(BaseModel):
    type: str | None = Field(default=None, min_length=1)
    caption: str | None = Field(default=None, min_length=1)
    image_url: HttpUrl | None = None
    status: str | None = Field(default=None, pattern=r"^(draft|published|archived)$")


class CampaignResponse(BaseModel):
    id: str
    type: str
    caption: str
    image_url: str | None = None
    status: str
    created_at: str
    updated_at: str


@dataclass
class Campaign:
    id: str = field(default_factory=lambda: str(uuid4()))
    type: str = ""
    caption: str = ""
    image_url: str = ""
    status: str = "draft"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_response(self) -> CampaignResponse:
        return CampaignResponse(
            id=self.id,
            type=self.type,
            caption=self.caption,
            image_url=self.image_url or None,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
