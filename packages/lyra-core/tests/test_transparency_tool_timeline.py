"""Unit tests for tool_timeline."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.transparency.event_store import EventStore, make_event
from lyra_core.transparency.tool_timeline import build_tool_timeline, _args_preview


@pytest.fixture
def store(tmp_path: Path) -> EventStore:
    return EventStore(tmp_path / "test.db")


@pytest.mark.unit
def test_pre_post_pair_creates_two_events(store: EventStore) -> None:
    pre = make_event("PreToolUse", session_id="s1", tool_name="Bash",
                     payload={"args": {"command": "ls"}})
    post = make_event("PostToolUse", session_id="s1", tool_name="Bash",
                      payload={"result": "file1.py\nfile2.py"})
    store.append(pre)
    store.append(post)
    timeline = build_tool_timeline(store, session_id="s1")
    assert len(timeline) == 2
    assert timeline[0].status == "pending"
    assert timeline[1].status == "success"


@pytest.mark.unit
def test_failure_event_shows_error_status(store: EventStore) -> None:
    store.append(make_event("PreToolUse", session_id="s1", tool_name="Edit"))
    store.append(make_event("PostToolUseFailure", session_id="s1", tool_name="Edit"))
    timeline = build_tool_timeline(store, session_id="s1")
    assert any(t.status == "error" for t in timeline)


@pytest.mark.unit
def test_permission_request_shows_blocked(store: EventStore) -> None:
    store.append(make_event("PermissionRequest", session_id="s1", tool_name="Bash",
                            payload={"args": {"command": "rm -rf /"}}))
    timeline = build_tool_timeline(store, session_id="s1")
    assert any(t.status == "blocked" for t in timeline)


@pytest.mark.unit
def test_args_preview_truncates() -> None:
    payload = json.dumps({"args": {"command": "a" * 200}})
    preview = _args_preview(payload)
    assert len(preview) <= 80


@pytest.mark.unit
def test_respects_n_limit(store: EventStore) -> None:
    for i in range(20):
        store.append(make_event("PostToolUse", session_id="s1", tool_name=f"T{i}"))
    timeline = build_tool_timeline(store, n=5, session_id="s1")
    assert len(timeline) <= 5
