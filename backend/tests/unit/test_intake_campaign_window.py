"""Campaign validity window — intake extraction, merge, validation, persistence.

Covers the intake side of the fix: the phrase "from 20 September 2026 to 1
October 2026" must populate campaign_start_date/campaign_end_date (NOT
event_date), survive merges, resist erasure by later null output, honor explicit
corrections, reject reversed ranges truthfully, and sync into campaign.schedule
while preserving timezone/recurrence.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.models.intake import IntakeChecklist
from src.services.intake_chat_service import IntakeChatService


class _FakeLLM:
    """Router double: returns a fixed unified-intake payload."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    async def generate_json(self, system_prompt, user_prompt, *args, **kwargs) -> dict:
        return self.payload


def _service(payload: dict) -> tuple[IntakeChatService, list]:
    """An IntakeChatService with persistence stubbed and schedule-sync recorded."""
    svc = IntakeChatService(llm=_FakeLLM(payload))
    svc._save_message = lambda *a, **k: None  # type: ignore[method-assign]
    svc._save_checklist = lambda *a, **k: None  # type: ignore[method-assign]
    sync_calls: list = []
    svc._sync_campaign_schedule_window = lambda cid, oid, s, e: sync_calls.append((s, e))  # type: ignore[method-assign]
    return svc, sync_calls


async def _run(svc: IntakeChatService, message: str, checklist: IntakeChecklist | None = None):
    return await svc.process_chat_turn(
        campaign_id=uuid4(),
        user_message=message,
        history=[],
        current_checklist=checklist,
        owner_id=uuid4(),
    )


_EMPTY_PAYLOAD = {"extracted": {}, "reply": "Thanks!"}


@pytest.mark.asyncio
async def test_1_and_2_range_extracts_window_not_event_date() -> None:
    svc, sync_calls = _service(_EMPTY_PAYLOAD)
    res = await _run(svc, "from 20 September 2026 to 1 October 2026")
    checklist = res["checklist"]
    # 1. Both bounds extracted as ISO.
    assert checklist.campaign_start_date == "2026-09-20"
    assert checklist.campaign_end_date == "2026-10-01"
    # 2. Range is NOT stored in event_date.
    assert checklist.event_date is None
    # Confirmed window synced to authoritative schedule bounds.
    assert sync_calls == [(date(2026, 9, 20), date(2026, 10, 1))]


@pytest.mark.asyncio
async def test_2b_range_misfiled_into_event_date_is_moved_out() -> None:
    # A weak model puts the whole range into event_date — the sanitizer rescues it.
    payload = {"extracted": {"event_date": "20 September 2026 to 1 October 2026"}, "reply": "ok"}
    svc, _ = _service(payload)
    # Use a message with no detectable range so only the LLM payload drives this.
    res = await _run(svc, "here are the dates")
    checklist = res["checklist"]
    assert checklist.event_date is None
    assert checklist.campaign_start_date == "2026-09-20"
    assert checklist.campaign_end_date == "2026-10-01"


@pytest.mark.asyncio
async def test_3_merge_preserves_both_dates() -> None:
    svc, _ = _service(_EMPTY_PAYLOAD)
    existing = IntakeChecklist(
        campaign_type="general_promotion",
        campaign_name="Autumn Sale",
        objective="Drive signups",
        target_audience="SMB owners",
    )
    res = await _run(svc, "from 20 September 2026 to 1 October 2026", existing)
    checklist = res["checklist"]
    assert checklist.campaign_start_date == "2026-09-20"
    assert checklist.campaign_end_date == "2026-10-01"
    # Prior fields survive the merge.
    assert checklist.campaign_name == "Autumn Sale"
    assert checklist.objective == "Drive signups"


@pytest.mark.asyncio
async def test_4_later_null_output_does_not_erase_confirmed_dates() -> None:
    # A subsequent turn whose message has no range and whose LLM returns nulls
    # must not wipe the previously confirmed window.
    svc, _ = _service({"extracted": {"campaign_start_date": None, "campaign_end_date": None}, "reply": "ok"})
    prior = IntakeChecklist(
        campaign_type="general_promotion",
        campaign_start_date="2026-09-20",
        campaign_end_date="2026-10-01",
    )
    res = await _run(svc, "the audience is small business owners", prior)
    checklist = res["checklist"]
    assert checklist.campaign_start_date == "2026-09-20"
    assert checklist.campaign_end_date == "2026-10-01"


@pytest.mark.asyncio
async def test_5_explicit_correction_updates_dates() -> None:
    svc, sync_calls = _service(_EMPTY_PAYLOAD)
    prior = IntakeChecklist(
        campaign_type="general_promotion",
        campaign_start_date="2026-09-20",
        campaign_end_date="2026-10-01",
    )
    res = await _run(svc, "actually run it from 21 September 2026 to 2 October 2026", prior)
    checklist = res["checklist"]
    assert checklist.campaign_start_date == "2026-09-21"
    assert checklist.campaign_end_date == "2026-10-02"
    assert sync_calls[-1] == (date(2026, 9, 21), date(2026, 10, 2))


@pytest.mark.asyncio
async def test_11_single_event_date_untouched() -> None:
    # An actual single event date is NOT a range → event_date preserved, no window.
    payload = {"extracted": {"event_date": "2026-09-25", "campaign_type": "webinar"}, "reply": "ok"}
    svc, sync_calls = _service(payload)
    res = await _run(svc, "the webinar is on 25 September 2026")
    checklist = res["checklist"]
    assert checklist.event_date == "2026-09-25"
    assert checklist.campaign_start_date is None
    assert checklist.campaign_end_date is None
    assert sync_calls == []


@pytest.mark.asyncio
async def test_12_reversed_range_not_silently_persisted() -> None:
    svc, sync_calls = _service(_EMPTY_PAYLOAD)
    res = await _run(svc, "from 1 October 2026 to 20 September 2026")
    checklist = res["checklist"]
    # No silent persistence and no silent swap.
    assert checklist.campaign_start_date is None
    assert checklist.campaign_end_date is None
    assert sync_calls == []
    # Truthful correction surfaced to the user.
    assert "on or before" in res["reply"].lower()


# ── TASK 2: schedule sync preserves timezone / recurrence ─────────────────────


class _FluentQuery:
    def __init__(self, store: dict, table: str) -> None:
        self._store = store
        self._table = table
        self._update_payload = None

    def select(self, *a, **k):
        return self

    def update(self, payload):
        self._update_payload = payload
        return self

    def eq(self, *a, **k):
        return self

    def execute(self):
        if self._update_payload is not None:
            self._store["updated"] = self._update_payload
            return SimpleNamespace(data=[{}])
        return SimpleNamespace(data=self._store["rows"])


class _FakeClient:
    def __init__(self, store: dict) -> None:
        self._store = store

    def table(self, name):
        return _FluentQuery(self._store, name)


def test_6_and_7_sync_updates_bounds_and_preserves_metadata(monkeypatch) -> None:
    existing_schedule = {
        "start_date": "2026-09-19T00:00:00+00:00",
        "end_date": "2026-10-19T00:00:00+00:00",
        "timezone": "Asia/Karachi",
        "recurrence_rule": "FREQ=WEEKLY",
    }
    store = {"rows": [{"schedule": existing_schedule}], "updated": None}

    def _fake_repo(table_name):
        return SimpleNamespace(client=_FakeClient(store), table_name=table_name)

    monkeypatch.setattr("src.services.intake_chat_service.BaseRepository", _fake_repo)

    svc = IntakeChatService(llm=_FakeLLM(_EMPTY_PAYLOAD))
    svc._sync_campaign_schedule_window(
        uuid4(), uuid4(), date(2026, 9, 20), date(2026, 10, 1)
    )

    updated = store["updated"]["schedule"]
    # 6. Bounds updated.
    assert updated["start_date"].startswith("2026-09-20")
    assert updated["end_date"].startswith("2026-10-01")
    # 7. Timezone + recurrence preserved.
    assert updated["timezone"] == "Asia/Karachi"
    assert updated["recurrence_rule"] == "FREQ=WEEKLY"


def test_sync_refuses_reversed_merged_bounds(monkeypatch) -> None:
    existing_schedule = {
        "start_date": "2026-09-25T00:00:00+00:00",
        "end_date": "2026-10-19T00:00:00+00:00",
        "timezone": "UTC",
    }
    store = {"rows": [{"schedule": existing_schedule}], "updated": None}
    monkeypatch.setattr(
        "src.services.intake_chat_service.BaseRepository",
        lambda t: SimpleNamespace(client=_FakeClient(store), table_name=t),
    )
    svc = IntakeChatService(llm=_FakeLLM(_EMPTY_PAYLOAD))
    # New end (2026-09-20) is before the existing start (2026-09-25): must not write.
    svc._sync_campaign_schedule_window(uuid4(), uuid4(), None, date(2026, 9, 20))
    assert store["updated"] is None


def test_sync_no_row_is_noop(monkeypatch) -> None:
    store = {"rows": [], "updated": None}
    monkeypatch.setattr(
        "src.services.intake_chat_service.BaseRepository",
        lambda t: SimpleNamespace(client=_FakeClient(store), table_name=t),
    )
    svc = IntakeChatService(llm=_FakeLLM(_EMPTY_PAYLOAD))
    svc._sync_campaign_schedule_window(uuid4(), uuid4(), date(2026, 9, 20), date(2026, 10, 1))
    assert store["updated"] is None
