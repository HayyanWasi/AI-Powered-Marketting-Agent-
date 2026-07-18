from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class BrandImageResponse(BaseModel):
    id: str
    url: str
    filename: str
    content_type: str
    file_size: int
    sort_order: int
    uploaded_at: str


@dataclass
class BrandReferenceImage:
    id: str = field(default_factory=lambda: str(uuid4()))
    company_profile_id: str = ""
    storage_path: str = ""
    filename: str = ""
    content_type: str = ""
    file_size: int = 0
    sort_order: int = 0
    uploaded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_response(self, url: str) -> BrandImageResponse:
        return BrandImageResponse(
            id=self.id,
            url=url,
            filename=self.filename,
            content_type=self.content_type,
            file_size=self.file_size,
            sort_order=self.sort_order,
            uploaded_at=self.uploaded_at,
        )
