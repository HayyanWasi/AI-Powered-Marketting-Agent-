from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class GuestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, pattern=r".*\S.*")
    title: str | None = Field(default=None, max_length=1000)
    company: str | None = Field(default=None, max_length=1000)
    bio: str | None = Field(default=None, max_length=1000)


class GuestUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    title: str | None = Field(default=None, max_length=1000)
    company: str | None = Field(default=None, max_length=1000)
    bio: str | None = Field(default=None, max_length=1000)


class GuestResponse(BaseModel):
    id: str
    name: str
    title: str | None = None
    company: str | None = None
    bio: str | None = None
    created_at: str
    updated_at: str


@dataclass
class Guest:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    title: str = ""
    company: str = ""
    bio: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_response(self) -> GuestResponse:
        return GuestResponse(
            id=self.id,
            name=self.name,
            title=self.title or None,
            company=self.company or None,
            bio=self.bio or None,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
