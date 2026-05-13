"""Unit tests for EventStore."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from lyra_core.transparency.event_store import EventStore, make_event


@pytest.fixture
def store(tmp_path: Path) -> EventStore:
    return EventStore(tmp_path / "test.db")


@pytest.mark.unit
def test_append_and_tail(store: EventStore) -> None:
    ev = make_event("PreToolUse", session_id="s1", tool_name="Bash")
    store.append(ev)
    events = store.tail(10)
    assert len(events) == 1
    assert events[0].hook_type == "PreToolUse"
    assert events[0].tool_name == "Bash"


@pytest.mark.unit
def test_tail_respects_limit(store: EventStore) -> None:
    for i in range(20):
        store.append(make_event("PostToolUse", session_id="s1", tool_name=f"t{i}"))
    assert len(store.tail(5)) == 5


@pytest.mark.unit
def test_tail_filters_by_session(store: EventStore) -> None:
    store.append(make_event("PreToolUse", session_id="s1", tool_name="Bash"))
    store.append(make_event("PreToolUse", session_id="s2", tool_name="Edit"))
    assert len(store.tail(10, session_id="s1")) == 1
    assert store.tail(10, session_id="s1")[0].tool_name == "Bash"


@pytest.mark.unit
def test_since_returns_new_events(store: EventStore) -> None:
    ts_before = time.time()
    time.sleep(0.01)
    store.append(make_event("PostToolUse", session_id="s1"))
    events = store.since(ts_before)
    assert len(events) == 1


@pytest.mark.unit
def test_duplicate_event_id_ignored(store: EventStore) -> None:
    ev = make_event("PreToolUse", session_id="s1")
    store.append(ev)
    store.append(ev)  # same event_id — must be silently deduplicated
    assert len(store.tail(10)) == 1


@pytest.mark.unit
def test_active_sessions(store: EventStore) -> None:
    store.append(make_event("SessionStart", session_id="active"))
    sessions = store.active_sessions()
    assert "active" in sessions


@pytest.mark.unit
def test_payload_round_trips(store: EventStore) -> None:
    payload = {"tool": "Bash", "args": {"command": "ls"}}
    ev = make_event("PreToolUse", session_id="s1", payload=payload)
    store.append(ev)
    retrieved = store.tail(1)[0]
    assert json.loads(retrieved.payload_json) == payload
