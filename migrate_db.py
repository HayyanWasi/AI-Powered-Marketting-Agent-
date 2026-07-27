"""
Create the database schema for Company Profile Service.
"""

import httpx
from supabase import create_client

SUPABASE_URL = "https://jmlreuqfwxymugglrsxu.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImptbHJldXFmd3h5bXVnZ2xyc3h1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDEyOTQxMCwiZXhwIjoyMDk5NzA1NDEwfQ.7iCoNcGOuOhp5GWkyxRQVEOZpItIlW-F4GXv6l7Pqq8"

client = create_client(SUPABASE_URL, SERVICE_KEY)

SQL = """
CREATE TABLE IF NOT EXISTS public.company_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name TEXT NOT NULL,
    brand_guidelines TEXT NOT NULL,
    brand_tone TEXT,
    reference_image_urls TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_company_profiles_name ON public.company_profiles (company_name);

CREATE TABLE IF NOT EXISTS public.brand_reference_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_profile_id UUID NOT NULL REFERENCES public.company_profiles(id) ON DELETE CASCADE,
    storage_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    uploaded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_brand_images_company ON public.brand_reference_images (company_profile_id);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_company_profiles_updated_at ON public.company_profiles;
CREATE TRIGGER update_company_profiles_updated_at
    BEFORE UPDATE ON public.company_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}

with httpx.Client() as http:
    resp = http.post(
        f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
        json={"query": SQL},
        headers=headers,
    )
    print(f"exec_sql RPC: {resp.status_code}")
    if resp.status_code == 200:
        print("Tables created!")
    else:
        # Try pg query endpoint
        resp2 = http.post(
            f"{SUPABASE_URL}/pg/postgres/v1/sql",
            content=SQL,
            headers=headers,
        )
        print(f"pg SQL: {resp2.status_code} - {resp2.text[:300]}")

# Create storage bucket using REST API
with httpx.Client() as http:
    # Use the management-style API call
    resp3 = http.post(
        f"{SUPABASE_URL}/storage/v1/bucket",
        json={"name": "brand-images", "public": True},
        headers=headers,
    )
    print(f"Create bucket: {resp3.status_code} - {resp3.text[:200]}")

print("Migration attempt complete!")
