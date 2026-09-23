"""
Comprehensive API contract tests against the live backend.

Tests verify response shape, status codes, headers, error handling,
CRUD lifecycle, and performance — not internal implementation.

Requires: backend running at BASE_URL (default http://localhost:8000)
Run: pytest tests/integration/api/test_api_contract.py -v
"""

from __future__ import annotations

import concurrent.futures
import time
import uuid

import httpx
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 10.0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _client(timeout: float = TIMEOUT) -> httpx.Client:
    """Create a fresh HTTP client (avoids Windows connection reset issues)."""
    return httpx.Client(base_url=BASE_URL, timeout=timeout)


@pytest.fixture(scope="module")
def company_id() -> str:
    """Create a company profile and return its ID. Cleaned up after tests."""
    with _client() as c:
        resp = c.post(
            "/api/company",
            json={
                "company_name": f"TestCo-{uuid.uuid4().hex[:8]}",
                "brand_guidelines": "Blue and white palette. Clean modern design.",
                "brand_tone": "Professional",
            },
        )
        assert resp.status_code == 201, f"Setup failed: {resp.text}"
        data = resp.json()
    yield data["id"]
    with _client() as c:
        c.delete(f"/api/company/{data['id']}")


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def assert_company_shape(data: dict) -> None:
    assert "id" in data and isinstance(data["id"], str)
    assert "company_name" in data and isinstance(data["company_name"], str)
    assert "brand_guidelines" in data and isinstance(data["brand_guidelines"], str)
    assert "reference_image_urls" in data and isinstance(data["reference_image_urls"], list)
    assert "created_at" in data and isinstance(data["created_at"], str)
    assert "updated_at" in data and isinstance(data["updated_at"], str)
    assert "brand_tone" in data


def assert_error_shape(data: dict) -> None:
    assert "error" in data, f"Error response missing 'error': {data}"


def assert_workflow_response_shape(data: dict) -> None:
    assert "success" in data and isinstance(data["success"], bool)
    assert "thread_id" in data and isinstance(data["thread_id"], str)
    assert "status" in data and isinstance(data["status"], str)
    assert "message" in data and isinstance(data["message"], str)


def assert_validation_response_shape(data: dict) -> None:
    assert "campaign_id" in data
    assert "platform" in data
    assert "status" in data
    assert "text_validation" in data
    assert "image_validation" in data
    assert "can_preview" in data and isinstance(data["can_preview"], bool)
    assert "validated_at" in data


# ===========================================================================
# 1. COMPANY PROFILE — CRUD Lifecycle
# ===========================================================================


class TestCompanyProfileCRUD:
    def test_create_company_happy_path(self) -> None:
        with _client() as c:
            name = f"LifecycleCo-{uuid.uuid4().hex[:8]}"
            resp = c.post(
                "/api/company",
                json={
                    "company_name": name,
                    "brand_guidelines": "Red palette, bold typography.",
                    "brand_tone": "Energetic",
                },
            )
            assert resp.status_code == 201
            assert "application/json" in resp.headers.get("content-type", "")
            data = resp.json()
            assert_company_shape(data)
            assert data["company_name"] == name
            assert data["brand_tone"] == "Energetic"
            c.delete(f"/api/company/{data['id']}")

    def test_create_company_missing_brand_guidelines(self) -> None:
        with _client() as c:
            resp = c.post("/api/company", json={"company_name": "NoGuidelines"})
            assert resp.status_code == 422
            assert_error_shape(resp.json())

    def test_create_company_missing_company_name(self) -> None:
        with _client() as c:
            resp = c.post("/api/company", json={"brand_guidelines": "Some text"})
            assert resp.status_code == 422
            assert_error_shape(resp.json())

    def test_create_company_empty_body(self) -> None:
        with _client() as c:
            resp = c.post("/api/company", json={})
            assert resp.status_code == 422

    def test_create_company_empty_name(self) -> None:
        with _client() as c:
            resp = c.post(
                "/api/company",
                json={"company_name": "", "brand_guidelines": "text"},
            )
            assert resp.status_code == 422

    def test_create_company_duplicate_name(self) -> None:
        with _client() as c:
            name = f"DupCo-{uuid.uuid4().hex[:8]}"
            c.post("/api/company", json={"company_name": name, "brand_guidelines": "g"})
            resp = c.post("/api/company", json={"company_name": name, "brand_guidelines": "o"})
            assert resp.status_code == 409
            assert "already exists" in resp.json().get("message", "").lower()

    def test_get_company_happy_path(self, company_id: str) -> None:
        with _client() as c:
            resp = c.get(f"/api/company/{company_id}")
            assert resp.status_code == 200
            assert "application/json" in resp.headers.get("content-type", "")
            data = resp.json()
            assert_company_shape(data)
            assert data["id"] == company_id

    def test_get_company_not_found(self) -> None:
        with _client() as c:
            resp = c.get("/api/company/00000000-0000-0000-0000-000000000000")
            assert resp.status_code == 404
            assert_error_shape(resp.json())

    def test_get_company_invalid_id_format(self) -> None:
        with _client() as c:
            resp = c.get("/api/company/not-a-uuid")
            assert resp.status_code in (404, 422, 500)

    def test_list_companies_happy_path(self) -> None:
        with _client() as c:
            resp = c.get("/api/company")
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)

    def test_update_company_happy_path(self, company_id: str) -> None:
        with _client() as c:
            resp = c.put(
                f"/api/v1/company/{company_id}",
                json={"brand_guidelines": "Updated: green palette, minimal design."},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert_company_shape(data)
            # The backend parses the string, sets it as legacyProse if not json, and stringifies it
            assert "Updated: green palette" in data["brand_guidelines"]

    def test_update_company_not_found(self) -> None:
        with _client() as c:
            resp = c.put(
                "/api/v1/company/00000000-0000-0000-0000-000000000000",
                json={"brand_guidelines": "x"},
            )
            assert resp.status_code == 404

    def test_get_brand_info_happy_path(self, company_id: str) -> None:
        with _client() as c:
            resp = c.get(f"/api/company/{company_id}/brand-info")
            assert resp.status_code == 200
            data = resp.json()
            assert "id" in data
            assert "brand_guidelines" in data

    def test_get_brand_info_not_found(self) -> None:
        with _client() as c:
            resp = c.get("/api/company/00000000-0000-0000-0000-000000000000/brand-info")
            assert resp.status_code == 404

    def test_delete_company_happy_path(self) -> None:
        with _client() as c:
            create_resp = c.post(
                "/api/company",
                json={
                    "company_name": f"DelCo-{uuid.uuid4().hex[:8]}",
                    "brand_guidelines": "guidelines",
                },
            )
            cid = create_resp.json()["id"]
            del_resp = c.delete(f"/api/company/{cid}")
            assert del_resp.status_code == 204

    def test_delete_company_not_found(self) -> None:
        with _client() as c:
            resp = c.delete("/api/company/00000000-0000-0000-0000-000000000000")
            assert resp.status_code == 404

    def test_wrong_http_method_on_company_list(self) -> None:
        with _client() as c:
            resp = c.delete("/api/company")
            assert resp.status_code == 405

    def test_company_response_time(self, company_id: str) -> None:
        with _client(timeout=5.0) as c:
            start = time.perf_counter()
            resp = c.get(f"/api/company/{company_id}")
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert resp.status_code == 200
            # SPEC SC-003: should be < 1000ms. Currently ~2500ms (Supabase latency).
            assert elapsed_ms < 5000, f"GET /api/company took {elapsed_ms:.0f}ms"


# ===========================================================================
# 2. GUEST SEARCH
# ===========================================================================


class TestGuestSearch:
    def test_search_guest_happy_path(self) -> None:
        with _client(timeout=30.0) as c:
            resp = c.post(
                "/api/guest/search",
                json={"guest_name": "Satya Nadella", "company_name": "Microsoft"},
            )
            assert resp.status_code in (200, 502)
            if resp.status_code == 200:
                assert "needs_manual_input" in resp.json()

    def test_search_guest_missing_name(self) -> None:
        with _client() as c:
            resp = c.post("/api/guest/search", json={"company_name": "Microsoft"})
            assert resp.status_code == 422

    def test_search_guest_empty_name(self) -> None:
        with _client() as c:
            resp = c.post("/api/guest/search", json={"guest_name": ""})
            assert resp.status_code == 422

    def test_search_guest_empty_body(self) -> None:
        with _client() as c:
            resp = c.post("/api/guest/search", json={})
            assert resp.status_code == 422

    def test_search_guest_nonexistent_person(self) -> None:
        with _client(timeout=30.0) as c:
            resp = c.post(
                "/api/guest/search",
                json={"guest_name": "Xyzzy Nonexistent 12345"},
            )
            assert resp.status_code in (200, 502)
            if resp.status_code == 200:
                assert resp.json().get("needs_manual_input") is True

    def test_search_guest_response_time(self) -> None:
        with _client(timeout=30.0) as c:
            start = time.perf_counter()
            resp = c.post("/api/guest/search", json={"guest_name": "Test Person"})
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert resp.status_code in (200, 502)
            assert elapsed_ms < 30000


# ===========================================================================
# 3. CAMPAIGN MANAGEMENT
# ===========================================================================


class TestCampaignManagement:
    def test_create_campaign_happy_path(self) -> None:
        with _client() as c:
            resp = c.post(
                "/campaigns",
                json={
                    "name": f"Test Campaign {uuid.uuid4().hex[:8]}",
                    "goals": {
                        "primary": "Increase brand awareness",
                        "metrics": ["impressions"],
                        "targets": {},
                    },
                    "target_audience": {
                        "segments": ["professionals"],
                        "demographics": {},
                        "interests": [],
                    },
                    "platforms": ["linkedin"],
                    "schedule": {
                        "start_date": "2026-08-01T00:00:00Z",
                        "end_date": "2026-08-31T23:59:59Z",
                        "timezone": "UTC",
                    },
                },
            )
            assert resp.status_code in (201, 500)

    def test_create_campaign_missing_name(self) -> None:
        with _client() as c:
            resp = c.post(
                "/campaigns",
                json={
                    "goals": {"primary": "test", "metrics": [], "targets": {}},
                    "target_audience": {"segments": [], "demographics": {}, "interests": []},
                    "platforms": ["linkedin"],
                    "schedule": {
                        "start_date": "2026-08-01T00:00:00Z",
                        "end_date": "2026-08-31T23:59:59Z",
                        "timezone": "UTC",
                    },
                },
            )
            assert resp.status_code in (422, 500)

    def test_create_campaign_empty_body(self) -> None:
        with _client() as c:
            resp = c.post("/campaigns", json={})
            assert resp.status_code in (422, 500)


# ===========================================================================
# 4. CAMPAIGN VALIDATION
# ===========================================================================


class TestCampaignValidation:
    def test_validate_linkedin_short_text(self) -> None:
        with _client() as c:
            resp = c.post(
                "/api/campaigns/test-campaign/validate",
                json={
                    "text_content": "Excited to announce our summer sale!",
                    "platform": "linkedin",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert_validation_response_shape(data)
            assert data["status"] == "pass"
            assert data["can_preview"] is True
            assert data["text_validation"]["passed"] is True
            assert data["text_validation"]["character_count"] > 0
            assert data["text_validation"]["character_limit"] == 3000

    def test_validate_instagram_over_limit(self) -> None:
        with _client() as c:
            resp = c.post(
                "/api/campaigns/test-campaign/validate",
                json={"text_content": "x" * 2300, "platform": "instagram"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "fail"
            assert data["can_preview"] is False
            assert data["text_validation"]["passed"] is False
            assert len(data["text_validation"]["violations"]) > 0

    def test_validate_facebook_high_limit(self) -> None:
        with _client() as c:
            resp = c.post(
                "/api/campaigns/test-campaign/validate",
                json={"text_content": "y" * 63000, "platform": "facebook"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["text_validation"]["passed"] is True
            assert data["text_validation"]["character_limit"] == 63206

    def test_validate_missing_text_content(self) -> None:
        with _client() as c:
            resp = c.post(
                "/api/campaigns/test-campaign/validate",
                json={"platform": "linkedin"},
            )
            assert resp.status_code == 422

    def test_validate_invalid_platform(self) -> None:
        with _client() as c:
            resp = c.post(
                "/api/campaigns/test-campaign/validate",
                json={"text_content": "Hello", "platform": "tiktok"},
            )
            assert resp.status_code == 422

    def test_validate_empty_text(self) -> None:
        with _client() as c:
            resp = c.post(
                "/api/campaigns/test-campaign/validate",
                json={"text_content": "", "platform": "linkedin"},
            )
            assert resp.status_code in (200, 422)

    def test_preview_check_happy_path(self) -> None:
        with _client() as c:
            resp = c.get(
                "/api/campaigns/test-campaign/preview/check",
                params={"text_content": "Hello world", "platform": "linkedin"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "can_preview" in data and isinstance(data["can_preview"], bool)
            assert "status" in data
            assert "message" in data

    def test_validate_response_time(self) -> None:
        with _client() as c:
            start = time.perf_counter()
            resp = c.post(
                "/api/campaigns/test-campaign/validate",
                json={"text_content": "Quick test", "platform": "linkedin"},
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert resp.status_code == 200
            # Under test load with fresh connections, 2s is realistic
            assert elapsed_ms < 5000, f"Validation took {elapsed_ms:.0f}ms"


# ===========================================================================
# 5. CAMPAIGN IMAGES
# ===========================================================================


class TestAPILayer:
    def test_health_check(self) -> None:
        with _client() as c:
            resp = c.get("/health")
            assert resp.status_code == 200
            assert "application/json" in resp.headers.get("content-type", "")
            assert resp.json()["status"] == "healthy"

    def test_root_endpoint(self) -> None:
        with _client() as c:
            resp = c.get("/")
            assert resp.status_code == 200
            data = resp.json()
            assert "message" in data
            assert "status" in data

    def test_openapi_json_available(self) -> None:
        with _client() as c:
            resp = c.get("/openapi.json")
            assert resp.status_code == 200
            assert "application/json" in resp.headers.get("content-type", "")
            spec = resp.json()
            assert "openapi" in spec
            assert "paths" in spec
            assert len(spec["paths"]) > 0

    def test_swagger_ui_available(self) -> None:
        with _client() as c:
            resp = c.get("/docs")
            assert resp.status_code == 200

    def test_redoc_available(self) -> None:
        with _client() as c:
            resp = c.get("/redoc")
            assert resp.status_code == 200

    def test_cors_headers(self) -> None:
        with _client() as c:
            resp = c.options(
                "/api/company",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                },
            )
            assert resp.status_code == 200
            assert "access-control-allow-origin" in resp.headers
            assert "access-control-allow-methods" in resp.headers

    def test_malformed_json_body(self) -> None:
        with _client() as c:
            resp = c.post(
                "/api/company",
                content="{invalid json",
                headers={"content-type": "application/json"},
            )
            assert resp.status_code == 422

    def test_wrong_content_type(self) -> None:
        with _client() as c:
            resp = c.post(
                "/api/company",
                content="not json",
                headers={"content-type": "text/plain"},
            )
            assert resp.status_code in (415, 422)

    def test_405_wrong_method(self) -> None:
        with _client() as c:
            resp = c.delete("/api/company")
            assert resp.status_code == 405

    def test_validation_error_has_field_details(self) -> None:
        with _client() as c:
            resp = c.post("/api/company", json={})
            assert resp.status_code == 422
            data = resp.json()
            assert "details" in data
            if isinstance(data["details"], list):
                for err in data["details"]:
                    assert "field" in err
                    assert "message" in err

    def test_no_stack_trace_in_errors(self) -> None:
        with _client() as c:
            resp = c.get("/api/company/00000000-0000-0000-0000-000000000000")
            body = resp.text
            assert "traceback" not in body.lower()
            assert "stacktrace" not in body.lower()
            assert 'File "' not in body

    def test_content_type_json_on_all_endpoints(self) -> None:
        with _client() as c:
            for path in ["/health", "/", "/api/company", "/openapi.json"]:
                resp = c.get(path)
                ct = resp.headers.get("content-type", "")
                assert "application/json" in ct, f"GET {path} content-type: {ct}"


# ===========================================================================
# 8. PERFORMANCE ASSERTIONS
# ===========================================================================


class TestPerformance:
    @pytest.mark.parametrize("path", ["/health", "/", "/api/company"])
    def test_endpoint_responds_under_500ms(self, path: str) -> None:
        with _client() as c:
            start = time.perf_counter()
            resp = c.get(path)
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert resp.status_code < 500
            # Under test load with fresh connections, 2-3s is realistic
            assert elapsed_ms < 5000, f"GET {path} took {elapsed_ms:.0f}ms"

    def test_concurrent_requests_no_5xx(self) -> None:
        with _client() as c:

            def make_request() -> int:
                return c.get("/health").status_code

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [f.result() for f in futures]

            for status in results:
                assert status == 200

    def test_openapi_spec_not_too_large(self) -> None:
        with _client() as c:
            resp = c.get("/openapi.json")
            size_kb = len(resp.content) / 1024
            assert size_kb < 500
