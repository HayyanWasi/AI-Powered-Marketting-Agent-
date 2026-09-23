from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.models.intake import IntakeChecklist
from src.services import intake_chat_service as intake_module
from src.services.intake_chat_service import IntakeChatService, IntakePersistenceError


class FakeQuery:
    def __init__(self, database, table_name, fail_writes=False):
        self.database = database
        self.table_name = table_name
        self.fail_writes = fail_writes
        self.operation = None
        self.payload = None
        self.filters = {}

    def select(self, _columns):
        self.operation = "select"
        return self

    def upsert(self, payload, on_conflict=None):
        assert on_conflict == "campaign_id"
        self.operation = "upsert"
        self.payload = dict(payload)
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = dict(payload)
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def order(self, _column):
        return self

    def execute(self):
        if self.fail_writes and self.operation in {"upsert", "insert", "delete"}:
            raise RuntimeError("forced database write failure")

        rows = self.database.setdefault(self.table_name, [])
        if self.operation == "upsert":
            rows[:] = [r for r in rows if r["campaign_id"] != self.payload["campaign_id"]]
            rows.append(dict(self.payload))
            return SimpleNamespace(data=[dict(self.payload)])
        if self.operation == "insert":
            rows.append(dict(self.payload))
            return SimpleNamespace(data=[dict(self.payload)])
        if self.operation == "delete":
            rows[:] = [
                row
                for row in rows
                if any(row.get(key) != value for key, value in self.filters.items())
            ]
            return SimpleNamespace(data=[])
        if self.operation == "select":
            selected = [
                dict(row)
                for row in rows
                if all(row.get(key) == value for key, value in self.filters.items())
            ]
            return SimpleNamespace(data=selected)
        raise AssertionError(f"Unsupported operation: {self.operation}")


class FakeClient:
    def __init__(self, database, fail_writes=False):
        self.database = database
        self.fail_writes = fail_writes

    def table(self, table_name):
        return FakeQuery(self.database, table_name, self.fail_writes)


class FakeRepository:
    database = {}
    fail_writes = False

    def __init__(self, table_name):
        self.table_name = table_name
        self.client = FakeClient(self.database, self.fail_writes)


@pytest.fixture
def fake_repository(monkeypatch):
    FakeRepository.database = {}
    FakeRepository.fail_writes = False
    monkeypatch.setattr(intake_module, "BaseRepository", FakeRepository)
    return FakeRepository


def test_forward_migration_adds_all_model_columns_without_destructive_sql():
    migration = (
        (Path(__file__).parents[2] / "migrations" / "012_add_campaign_type_intake_fields.up.sql")
        .read_text(encoding="utf-8")
        .lower()
    )

    for column in {
        "campaign_type",
        "campaign_name",
        "objective",
        "value_proposition",
        "cta_url",
        "category",
        "guest_profile",
        "last_field_asked",
    }:
        assert f"add column if not exists {column}" in migration

    assert "drop " not in migration
    assert "delete " not in migration
    assert "truncate " not in migration


@pytest.mark.asyncio
async def test_app_launch_and_existing_fields_round_trip_through_service(fake_repository):
    campaign_id = uuid4()
    checklist = IntakeChecklist(
        campaign_type="app_launch",
        campaign_name="Schema Sentinel App",
        objective="Acquire early users",
        target_audience="People booking local services",
        value_proposition="Book verified services quickly",
        cta_url="https://sentinel.invalid/download",
        event_date="2026-10-20",
        venue="Online",
        has_guest=False,
        curriculum_breakdown="Discovery, booking, and verification",
        outcome_deliverable="A completed first booking",
        is_free_or_paid="Free",
        registration_link="https://sentinel.invalid/register",
        category="Marketplace",
        guest_profile={"source": "existing-field-sentinel"},
        last_field_asked="value_proposition",
    )
    writer = IntakeChatService()
    reader = IntakeChatService()
    owner_id = uuid4()

    writer._save_checklist(campaign_id, owner_id, checklist)
    loaded = await reader.get_checklist(campaign_id, owner_id)

    assert loaded.model_dump(mode="json") == checklist.model_dump(mode="json")
    stored = fake_repository.database["intake_checklists"][0]
    assert stored["campaign_type"] == "app_launch"
    assert stored["campaign_name"] == "Schema Sentinel App"
    assert stored["objective"] == "Acquire early users"
    assert stored["value_proposition"] == "Book verified services quickly"
    assert stored["cta_url"] == "https://sentinel.invalid/download"


def test_failed_database_write_raises_and_does_not_update_cache(fake_repository):
    FakeRepository.fail_writes = True
    campaign_id = uuid4()
    owner_id = uuid4()
    service = IntakeChatService()
    checklist = IntakeChecklist(
        campaign_type="app_launch",
        campaign_name="Failure Sentinel",
        objective="Verify failure",
        target_audience="Test operators",
        value_proposition="Truthful persistence",
    )

    with pytest.raises(IntakePersistenceError):
        service._save_checklist(campaign_id, owner_id, checklist)

    assert str(campaign_id) not in service._local_checklists
    assert fake_repository.database.get("intake_checklists", []) == []


@pytest.mark.asyncio
async def test_existing_record_without_new_columns_loads(fake_repository):
    campaign_id = uuid4()
    owner_id = uuid4()
    fake_repository.database["intake_checklists"] = [
        {
            "campaign_id": str(campaign_id),
            "owner_id": str(owner_id),
            "event_date": "2025-01-15",
            "venue": "Legacy Hall",
            "has_guest": False,
            "target_audience": "Legacy audience",
            "is_complete": False,
        }
    ]

    loaded = await IntakeChatService().get_checklist(campaign_id, owner_id)

    assert loaded.event_date == "2025-01-15"
    assert loaded.venue == "Legacy Hall"
    assert loaded.target_audience == "Legacy audience"
    assert loaded.campaign_type is None
    assert loaded.campaign_name is None
