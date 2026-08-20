"""Supabase client wrapper with connection management."""

from functools import lru_cache

from supabase import create_client

from src.config.settings import settings


@lru_cache
def get_supabase_client():
    """Create and return Supabase client singleton."""
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_KEY must be set")

    return create_client(url, key)
