"""One-shot Supabase setup: create public brand-images bucket + seed a company profile.

Run:
    cd backend && python -m scripts.setup_supabase

Idempotent — safe to re-run.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend/src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.supabase import get_supabase_client
from src.services.supabase import STORAGE_BUCKET

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

SEED_PROFILE = {
    "company_name": "Demo Corp",
    "brand_guidelines": "Modern, clean design with bold accent colors",
    "brand_tone": "Professional yet approachable",
    "reference_image_urls": [
        "https://image.pollinations.ai/prompt/minimal%20tech%20company%20logo%20blue%20gradient?width=512&height=512&nologo=true",
    ],
}


def _bucket_name(b) -> str | None:
    """Extract bucket name from SyncBucket object or dict."""
    if isinstance(b, dict):
        return b.get("name")
    return getattr(b, "name", None)


def _bucket_public(b) -> bool | None:
    """Extract public flag from SyncBucket object or dict."""
    if isinstance(b, dict):
        return b.get("public")
    return getattr(b, "public", None)


def ensure_bucket(client) -> None:
    """Create the brand-images bucket as public (skip if it already exists)."""
    storage = client.storage

    buckets = storage.list_buckets()
    existing_names = {_bucket_name(b) for b in buckets}

    if STORAGE_BUCKET in existing_names:
        print(f"  Bucket '{STORAGE_BUCKET}' already exists.")
    else:
        storage.create_bucket(
            STORAGE_BUCKET,
            options={"public": True},
        )
        print(f"  Created public bucket '{STORAGE_BUCKET}'.")

    # Verify it is public
    buckets = storage.list_buckets()
    bucket = next((b for b in buckets if _bucket_name(b) == STORAGE_BUCKET), None)
    is_public = _bucket_public(bucket)
    if is_public is False:
        print(f"  WARNING: Bucket '{STORAGE_BUCKET}' exists but is NOT public.")
        print(
            "  Set it to public via the Supabase Dashboard -> Storage -> brand-images -> Settings."
        )
    else:
        print(f"  Bucket '{STORAGE_BUCKET}' is public.")


def ensure_seed_profile(client) -> None:
    """Insert a demo company profile if none exists with reference_image_urls."""
    table = client.table("company_profiles")

    # Check if a profile already has reference_image_urls
    existing = table.select("id, reference_image_urls").execute()
    for row in existing.data or []:
        urls = row.get("reference_image_urls") or []
        if urls:
            print(
                f"  Profile '{row['id']}' already has {len(urls)} reference image(s). Skipping seed."
            )
            return

    # Insert seed profile
    result = table.insert(SEED_PROFILE).execute()
    if result.data:
        profile = result.data[0]
        print(
            f"  Seeded profile '{profile['id']}' with {len(SEED_PROFILE['reference_image_urls'])} reference image(s)."
        )
    else:
        print("  WARNING: Failed to insert seed profile.")


def main() -> None:
    print("Supabase setup")
    print("=" * 40)

    client = get_supabase_client()

    print("\n1. Ensuring storage bucket...")
    ensure_bucket(client)

    print("\n2. Ensuring seed company profile...")
    ensure_seed_profile(client)

    print("\nDone.")


if __name__ == "__main__":
    main()
