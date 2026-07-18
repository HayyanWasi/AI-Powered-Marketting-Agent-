"""Test User Story 1 implementation against live Supabase DB."""

import sys

sys.path.insert(0, "backend")

from supabase import create_client
from src.config.settings import settings
from src.services.company.create_company_service import CreateCompanyService
from src.repositories.company_repository import CompanyRepository

# Clean any existing test data
client = create_client(settings.supabase_url, settings.supabase_key)
r = client.table("company_profiles").select("id, company_name").execute()
for row in r.data or []:
    print(f"Cleaning: {row['company_name']}")
    client.table("company_profiles").delete().eq("id", row["id"]).execute()

svc = CreateCompanyService()
repo = CompanyRepository()

# Test FR-001: Successful creation
profile = svc.execute("US1 Test Corp", "Professional tone, blue #0055FF", "Professional")
assert profile.company_name == "US1 Test Corp"
assert profile.brand_guidelines == "Professional tone, blue #0055FF"
assert profile.brand_tone == "Professional"
assert profile.is_complete is True
assert profile.reference_image_urls == []
print("FR-001: PASS - Company profile created with all fields")

# Test FR-003: Required fields
try:
    svc.execute("No Guide Corp", "")
    assert False, "Should have rejected empty guidelines"
except ValueError:
    print("FR-003: PASS - Empty brand_guidelines rejected")

try:
    svc.execute("", "Some guidelines")
    assert False, "Should have rejected empty name"
except ValueError:
    print("FR-003: PASS - Empty company_name rejected")

# Test FR-002: Unique company name
try:
    svc.execute("US1 Test Corp", "Duplicate guidelines")
    assert False, "Should have rejected duplicate"
except ValueError:
    print("FR-002: PASS - Duplicate company name rejected")

# Cleanup
repo.delete(profile.id)
print("Cleanup OK")
print("\n=== US1 ALL TESTS PASSED ===")
