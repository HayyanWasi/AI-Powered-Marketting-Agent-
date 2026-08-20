"""Verify Supabase setup: bucket + seed profile."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.supabase import get_supabase_client

client = get_supabase_client()

# Check bucket files
print("=== brand-images bucket files ===")
files = client.storage.from_("brand-images").list()
for f in files:
    name = f.get("name", "?") if isinstance(f, dict) else getattr(f, "name", "?")
    print(f"  {name}")
if not files:
    print("  (empty)")

# Check profile
print()
print("=== company_profiles ===")
result = client.table("company_profiles").select("id, company_name, reference_image_urls").execute()
for row in result.data or []:
    urls = row.get("reference_image_urls") or []
    print(f"  {row['id']}: {row['company_name']} ({len(urls)} image(s))")
    for u in urls:
        print(f"    -> {u}")
