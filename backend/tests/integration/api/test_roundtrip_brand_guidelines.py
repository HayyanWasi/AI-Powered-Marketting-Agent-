import json
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import AuthenticatedUser, get_authenticated_user
from src.main import app
from src.models.company import CompanyProfile
from src.repositories.company_repository import CompanyRepository

client = TestClient(app)


def mock_user_a() -> AuthenticatedUser:
    return AuthenticatedUser(
        id="00000000-0000-0000-0000-00000000000A", roles=["user"], permissions=[]
    )


@pytest.fixture
def mock_repo(monkeypatch) -> MagicMock:
    repo_mock = MagicMock(spec=CompanyRepository)

    # Store the profiles in memory to simulate DB
    store = {}

    def mock_create(company_name, brand_guidelines, brand_tone=None):
        profile = CompanyProfile(
            company_name=company_name, brand_guidelines=brand_guidelines, brand_tone=brand_tone
        )
        store[profile.id] = profile
        return profile

    def mock_get_by_id(profile_id):
        return store[profile_id]

    def mock_update(profile_id, data):
        profile = store[profile_id]
        if "brand_guidelines" in data:
            profile.brand_guidelines = data["brand_guidelines"]
        if "company_name" in data:
            profile.company_name = data["company_name"]
        return profile

    repo_mock.create.side_effect = mock_create
    repo_mock.get_by_id.side_effect = mock_get_by_id
    repo_mock.update.side_effect = mock_update

    # Patch the owned_profiles dependency
    from src.api.v1.company import _get_create_service, _get_get_service, _get_update_service
    from src.services.company.create_company_service import CreateCompanyService
    from src.services.company.get_company_service import GetCompanyService
    from src.services.company.update_company_service import UpdateCompanyService

    app.dependency_overrides[_get_create_service] = lambda: CreateCompanyService(
        repository=repo_mock
    )
    app.dependency_overrides[_get_update_service] = lambda: UpdateCompanyService(
        repository=repo_mock
    )
    app.dependency_overrides[_get_get_service] = lambda: GetCompanyService(repository=repo_mock)

    return repo_mock


@pytest.fixture
def user_a_client() -> Generator[TestClient]:
    app.dependency_overrides[get_authenticated_user] = mock_user_a
    yield client
    app.dependency_overrides.clear()


def test_update_company_preserves_unknown_fields(user_a_client, mock_repo):
    # Set initial JSON
    initial_guidelines = {"website": "https://test.com", "unknownField123": "preserve me!"}

    # 1. Create company profile
    resp = user_a_client.post(
        "/api/v1/company",
        json={"company_name": "RoundTrip Test", "brand_guidelines": json.dumps(initial_guidelines)},
    )
    assert resp.status_code == 201
    profile_id = resp.json()["id"]

    # 2. Load
    resp = user_a_client.get(f"/api/v1/company/{profile_id}")
    assert resp.status_code == 200
    guidelines_str = resp.json()["brand_guidelines"]
    loaded = json.loads(guidelines_str)
    assert loaded["website"] == "https://test.com"
    assert loaded["unknownField123"] == "preserve me!"

    # 3. Edit one field
    edit_guidelines = {"website": "https://new.com"}

    # 4. Save
    save_resp = user_a_client.put(
        f"/api/v1/company/{profile_id}", json={"brand_guidelines": json.dumps(edit_guidelines)}
    )
    assert save_resp.status_code == 200

    # 5. Verify unrelated guidelines remain intact
    saved_str = save_resp.json()["brand_guidelines"]
    saved_json = json.loads(saved_str)
    assert saved_json["website"] == "https://new.com"
    assert saved_json["unknownField123"] == "preserve me!"
    assert saved_json["schemaVersion"] == 2
