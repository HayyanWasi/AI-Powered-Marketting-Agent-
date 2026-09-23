from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.api.dependencies import AuthenticatedUser
from src.api.v1 import intake as intake_api
from src.models.intake import GuestConfirmRequest, IntakeChatRequest
from src.services import intake_access_service as access_module

USER_A = UUID("aaaaaaaa-0000-0000-0000-000000000001")
USER_B = UUID("bbbbbbbb-0000-0000-0000-000000000002")
SESSION_A = UUID("aaaaaaaa-1111-1111-1111-111111111111")
SESSION_B = UUID("bbbbbbbb-2222-2222-2222-222222222222")
CAMPAIGN_A = UUID("aaaaaaaa-3333-3333-3333-333333333333")
CAMPAIGN_B = UUID("bbbbbbbb-4444-4444-4444-444444444444")


class FakeQuery:
    calls: list[dict] = []

    def __init__(self, database: dict[str, list[dict]], table_name: str) -> None:
        self.database = database
        self.table_name = table_name
        self.operation = ""
        self.columns = ""
        self.payload = None
        self.filters: dict[str, str] = {}
        self.limit_count: int | None = None
        self.conflict_column: str | None = None

    def select(self, columns: str):
        self.operation = "select"
        self.columns = columns
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def upsert(self, payload, on_conflict: str):
        self.operation = "upsert"
        self.payload = payload
        self.conflict_column = on_conflict
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def eq(self, column: str, value: str):
        self.filters[column] = value
        return self

    def limit(self, count: int):
        self.limit_count = count
        return self

    def order(self, _column: str):
        return self

    def execute(self):
        self.calls.append(
            {
                "table": self.table_name,
                "operation": self.operation,
                "columns": self.columns,
                "filters": dict(self.filters),
            }
        )
        rows = self.database.setdefault(self.table_name, [])

        if self.operation == "select":
            selected = [
                dict(row)
                for row in rows
                if all(str(row.get(key)) == value for key, value in self.filters.items())
            ]
            if self.limit_count is not None:
                selected = selected[: self.limit_count]
            if self.columns != "*":
                fields = [field.strip() for field in self.columns.split(",")]
                selected = [{field: row.get(field) for field in fields} for row in selected]
            return SimpleNamespace(data=selected)

        if self.operation == "insert":
            inserted = self.payload if isinstance(self.payload, list) else [self.payload]
            for incoming in inserted:
                if self.table_name == "intake_checklists" and any(
                    row.get("campaign_id") == incoming.get("campaign_id") for row in rows
                ):
                    raise RuntimeError("duplicate campaign_id")
                rows.append(dict(incoming))
            return SimpleNamespace(data=[dict(row) for row in inserted])

        if self.operation == "upsert":
            key = self.conflict_column
            rows[:] = [row for row in rows if row.get(key) != self.payload.get(key)]
            rows.append(dict(self.payload))
            return SimpleNamespace(data=[dict(self.payload)])

        if self.operation == "delete":
            deleted = [
                row
                for row in rows
                if all(str(row.get(key)) == value for key, value in self.filters.items())
            ]
            rows[:] = [row for row in rows if row not in deleted]
            return SimpleNamespace(data=deleted)

        raise AssertionError(f"Unsupported operation {self.operation}")


class FakeRepository:
    database: dict[str, list[dict]] = {}

    def __init__(self, table_name: str) -> None:
        self.table_name = table_name
        self.client = self

    def table(self, table_name: str) -> FakeQuery:
        return FakeQuery(self.database, table_name)


class FakeCampaignRepository:
    async def get_by_id(self, campaign_id: UUID, organization_id: UUID | None = None):
        rows = FakeRepository.database.get("campaigns", [])
        for row in rows:
            if row["id"] != str(campaign_id):
                continue
            if organization_id is not None and row["organization_id"] != str(organization_id):
                return None
            return SimpleNamespace(
                id=campaign_id,
                organization_id=UUID(row["organization_id"]),
            )
        return None


@pytest.fixture
def two_user_data(monkeypatch):
    FakeQuery.calls = []
    FakeRepository.database = {
        "campaigns": [
            {"id": str(CAMPAIGN_A), "organization_id": str(USER_A)},
            {"id": str(CAMPAIGN_B), "organization_id": str(USER_B)},
        ],
        "intake_checklists": [
            {
                "campaign_id": str(SESSION_A),
                "owner_id": str(USER_A),
                "campaign_name": "USER_A_PRIVATE_INTAKE",
                "is_complete": False,
            },
            {
                "campaign_id": str(SESSION_B),
                "owner_id": str(USER_B),
                "campaign_name": "USER_B_PRIVATE_INTAKE",
                "is_complete": False,
            },
        ],
        "intake_messages": [
            {
                "campaign_id": str(SESSION_A),
                "owner_id": str(USER_A),
                "role": "user",
                "content": "USER_A_PRIVATE_MESSAGE",
                "language": "en",
            },
            {
                "campaign_id": str(SESSION_B),
                "owner_id": str(USER_B),
                "role": "user",
                "content": "USER_B_PRIVATE_MESSAGE",
                "language": "en",
            },
        ],
    }
    monkeypatch.setattr(access_module, "BaseRepository", FakeRepository)
    monkeypatch.setattr(access_module, "CampaignRepository", FakeCampaignRepository)
    monkeypatch.setattr(intake_api, "BaseRepository", FakeRepository)
    return FakeRepository.database


def _user_a() -> AuthenticatedUser:
    return AuthenticatedUser(id=str(USER_A), roles=["user"], permissions=[])


@pytest.mark.asyncio
async def test_user_a_session_a_to_campaign_a_passes(two_user_data) -> None:
    response = await intake_api.migrate_intake_session(
        intake_api.MigrateIntakeRequest(session_id=SESSION_A, campaign_id=CAMPAIGN_A),
        _user_a(),
    )

    assert response["status"] == "success"
    destination = next(
        row
        for row in two_user_data["intake_checklists"]
        if row["campaign_id"] == str(CAMPAIGN_A)
    )
    assert destination["owner_id"] == str(USER_A)
    assert destination["campaign_name"] == "USER_A_PRIVATE_INTAKE"
    assert any(
        row["campaign_id"] == str(CAMPAIGN_A)
        and row["content"] == "USER_A_PRIVATE_MESSAGE"
        for row in two_user_data["intake_messages"]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source_id", "destination_id"),
    [
        (SESSION_B, CAMPAIGN_A),
        (SESSION_A, CAMPAIGN_B),
        (SESSION_B, CAMPAIGN_B),
    ],
)
async def test_cross_user_migration_is_denied_before_source_contents_are_read(
    two_user_data,
    source_id: UUID,
    destination_id: UUID,
) -> None:
    with pytest.raises(HTTPException) as error:
        await intake_api.migrate_intake_session(
            intake_api.MigrateIntakeRequest(
                session_id=source_id,
                campaign_id=destination_id,
            ),
            _user_a(),
        )

    assert error.value.status_code == 404
    assert "USER_B_PRIVATE_INTAKE" not in str(error.value.detail)
    assert not any(
        call["operation"] == "select"
        and call["columns"] == "*"
        and call["filters"].get("campaign_id") == str(source_id)
        for call in FakeQuery.calls
    )
    assert not any(
        row.get("campaign_id") == str(CAMPAIGN_A)
        and row.get("campaign_name") == "USER_B_PRIVATE_INTAKE"
        for row in two_user_data["intake_checklists"]
    )


@pytest.mark.asyncio
async def test_foreign_intake_read_and_update_are_denied_before_service_use(
    two_user_data,
    monkeypatch,
) -> None:
    get_history = AsyncMock()
    process_turn = AsyncMock()
    monkeypatch.setattr(intake_api.intake_service, "get_history", get_history)
    monkeypatch.setattr(intake_api.intake_service, "process_chat_turn", process_turn)

    with pytest.raises(HTTPException) as read_error:
        await intake_api.get_intake_history(CAMPAIGN_B, _user_a())
    with pytest.raises(HTTPException) as update_error:
        await intake_api.chat_turn(
            IntakeChatRequest(campaign_id=CAMPAIGN_B, user_message="steal or overwrite"),
            _user_a(),
        )

    assert read_error.value.status_code == 404
    assert update_error.value.status_code == 404
    get_history.assert_not_awaited()
    process_turn.assert_not_awaited()


@pytest.mark.asyncio
async def test_foreign_reset_and_guest_confirmation_are_denied_before_service_use(
    two_user_data,
    monkeypatch,
) -> None:
    clear_session = MagicMock()
    get_checklist = AsyncMock()
    monkeypatch.setattr(intake_api.intake_service, "clear_session", clear_session)
    monkeypatch.setattr(intake_api.intake_service, "get_checklist", get_checklist)

    with pytest.raises(HTTPException) as reset_error:
        await intake_api.reset_intake_session(CAMPAIGN_B, _user_a())
    with pytest.raises(HTTPException) as guest_error:
        await intake_api.confirm_guest(
            GuestConfirmRequest(
                campaign_id=CAMPAIGN_B,
                guest_name="Foreign Guest",
                confirmed=True,
            ),
            _user_a(),
        )

    assert reset_error.value.status_code == 404
    assert guest_error.value.status_code == 404
    clear_session.assert_not_called()
    get_checklist.assert_not_awaited()


@pytest.mark.asyncio
async def test_new_pre_campaign_session_is_claimed_by_authenticated_user(two_user_data) -> None:
    session_id = uuid4()

    await intake_api.intake_access.authorize(session_id, USER_A, claim_if_missing=True)

    claimed = next(
        row
        for row in two_user_data["intake_checklists"]
        if row["campaign_id"] == str(session_id)
    )
    assert claimed["owner_id"] == str(USER_A)


def test_forward_migration_binds_campaign_intake_without_claiming_legacy_sessions() -> None:
    migration = (
        Path(__file__).resolve().parents[3]
        / "migrations"
        / "014_add_intake_ownership.up.sql"
    ).read_text(encoding="utf-8").lower()

    assert "add column if not exists owner_id uuid" in migration
    assert "checklist.campaign_id = campaign.id" in migration
    assert "message.campaign_id = campaign.id" in migration
    assert "drop " not in migration
    assert "delete " not in migration
    assert "truncate " not in migration
    assert "create policy" not in migration
