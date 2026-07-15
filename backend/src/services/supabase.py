import logging
import time
from pathlib import Path
from typing import Any

from supabase import Client, create_client

from src.config.settings import settings

logger = logging.getLogger(__name__)

STORAGE_BUCKET = "brand-images"
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_IMAGES = 6
MAX_RETRIES = 3


class SupabaseServiceError(Exception):
    pass


class DuplicateCompanyError(SupabaseServiceError):
    pass


class NotFoundError(SupabaseServiceError):
    pass


class ValidationError(SupabaseServiceError):
    pass


class RetryExhaustedError(SupabaseServiceError):
    pass


def _retry(func: Any) -> Any:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        last_exception = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except SupabaseServiceError:
                raise
            except Exception as e:
                last_exception = e
                if attempt < MAX_RETRIES:
                    wait = 2**attempt
                    logger.warning("Retry %d/%d after error: %s", attempt, MAX_RETRIES, e)
                    time.sleep(wait)
        raise RetryExhaustedError(f"Failed after {MAX_RETRIES} attempts") from last_exception

    return wrapper


class SupabaseService:
    def __init__(self, client: Client | None = None):
        if client is not None:
            self.client = client
        else:
            self.client = create_client(settings.supabase_url, settings.supabase_key)

    def _table(self) -> Any:
        return self.client.table("company_profiles")

    def _storage(self) -> Any:
        return self.client.storage.from_(STORAGE_BUCKET)

    @_retry
    def create_profile(self, name: str, tone: str) -> dict[str, Any]:
        existing = self._table().select("id").execute()
        if existing.data:
            raise DuplicateCompanyError("Company name already exists")
        result = self._table().insert({"name": name, "tone": tone}).execute()
        if not result.data:
            raise SupabaseServiceError("Failed to create profile")
        return dict(result.data[0])

    @_retry
    def get_profile(self, profile_id: str) -> dict[str, Any]:
        result = self._table().select("*").eq("id", profile_id).execute()
        if not result.data:
            raise NotFoundError("Profile not found")
        return dict(result.data[0])

    @_retry
    def update_profile(self, profile_id: str, data: dict[str, Any]) -> dict[str, Any]:
        result = self._table().update(data).eq("id", profile_id).execute()
        if not result.data:
            raise NotFoundError("Profile not found")
        return dict(result.data[0])

    @_retry
    def delete_profile(self, profile_id: str) -> None:
        result = self._table().delete().eq("id", profile_id).execute()
        if not result.data:
            raise NotFoundError("Profile not found")

    @_retry
    def upload_image(self, file_path: Path, content_type: str) -> str:
        if content_type not in IMAGE_TYPES:
            raise ValidationError(f"Unsupported format: {content_type}")
        file_size = file_path.stat().st_size
        if file_size > MAX_IMAGE_SIZE:
            raise ValidationError(f"File too large: {file_size} bytes (max {MAX_IMAGE_SIZE})")
        with open(file_path, "rb") as f:
            self._storage().upload(file_path.name, f, {"content-type": content_type})
        return self.get_image_url(file_path.name)

    def get_image_url(self, path: str) -> str:
        return str(self._storage().get_public_url(path))
