"""Unit tests for ProcessRegistry."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from lyra_core.transparency.process_registry import ProcessRegistry
from lyra_core.transparency.event_store import EventStore
from lyra_core.transparency.models import AgentProcess


@pytest.fixture
def registry(tmp_path: Path) -> ProcessRegistry:
    store = EventStore(tmp_path / "test.db")
    return ProcessRegistry(store=store)


def _make_proc(session_id: str, state: str = "running") -> AgentProcess:
    return AgentProcess(
        pid=999,
        session_id=session_id,
        project_path="/tmp",
        state=state,
        current_tool="Bash",
        context_tokens=1000,
        context_limit=200000,
        context_pct=0.005,
        tokens_in=800,
        tokens_out=200,
        cost_usd=0.001,
        elapsed_s=10.0,
        parent_session_id="",
        children=(),
        last_event_at=time.time(),
    )


@pytest.mark.unit
def test_get_all_empty_before_refresh(registry: ProcessRegistry) -> None:
    assert registry.get_all() == []


@pytest.mark.unit
def test_subscribe_receives_update(registry: ProcessRegistry) -> None:
    received: list = []
    registry.subscribe(received.append)
    registry._processes["s1"] = _make_proc("s1")
    registry.update_from_event("s1", "PermissionRequest")
    assert len(received) == 1
    assert received[0].state == "blocked"


@pytest.mark.unit
def test_update_from_event_marks_done(registry: ProcessRegistry) -> None:
    registry._processes["s2"] = _make_proc("s2")
    registry.update_from_event("s2", "Stop")
    assert registry.get("s2").state == "done"
