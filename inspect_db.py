import json
from supabase import create_client

import os

url = "https://jmlreuqfwxymugglrsxu.supabase.co"
service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not service_key:
    print("Error: SUPABASE_SERVICE_ROLE_KEY not set")
    exit(1)

client = create_client(url, service_key)

# Check existing tables
tables_to_check = [
    "company_profiles",
    "brand_reference_images",
    "campaigns",
    "guest_profiles",
    "sessions",
]
for tbl in tables_to_check:
    try:
        r = client.table(tbl).select("*").limit(1).execute()
        print(f"{tbl}: EXISTS (data: {bool(r.data)})")
        if r.data:
            row = r.data[0]
            print(f"  Columns: {list(row.keys())}")
    except Exception as e:
        err_msg = str(e)
        if "Could not find the table" in err_msg:
            print(f"{tbl}: NOT FOUND")
        else:
            print(f"{tbl}: ERROR - {err_msg}")

# Check storage buckets
print("\n=== Storage Buckets ===")
try:
    buckets = client.storage.list_buckets()
    for b in buckets:
        print(f"  {b.name} (public: {b.public})")
except Exception as e:
    print(f"  Error: {e}")
