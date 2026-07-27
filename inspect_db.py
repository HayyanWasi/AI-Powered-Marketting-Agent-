import json
from supabase import create_client

url = "https://jmlreuqfwxymugglrsxu.supabase.co"
service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImptbHJldXFmd3h5bXVnZ2xyc3h1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDEyOTQxMCwiZXhwIjoyMDk5NzA1NDEwfQ.7iCoNcGOuOhp5GWkyxRQVEOZpItIlW-F4GXv6l7Pqq8"

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
