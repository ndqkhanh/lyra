"""Tests for observability/event_bus.py (Phase 1 — Process Transparency)."""
from __future__ import annotations

import asyncio
import json
import threading

import pytest

from lyra_core.observability.event_bus import (
    CronJobFired,
    CostThreshold,
    DaemonIteration,
    EventBus,
    LLMCallFinished,
    LLMCallStarted,
    LLMTokenChunk,
    PermissionDecision,
    ProcessStateWriter,
    StopHookFired,
    SubagentSpawned,
    ToolCallBlocked,
    ToolCallFinished,
    ToolCallStarted,
    get_event_bus,
    reset_event_bus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bus() -> EventBus:
    return EventBus()


def _tool_started(session="s1", tool="bash") -> ToolCallStarted:
    return ToolCallStarted(session_id=session, tool_name=tool, args_preview="ls -la")


# ---------------------------------------------------------------------------
# Event dataclass smoke tests
# ---------------------------------------------------------------------------


def test_llm_call_started_fields():
    e = LLMCallStarted(session_id="s1", model="claude-sonnet", prompt_tokens=100, turn=1)
    assert e.session_id == "s1"
    assert e.model == "claude-sonnet"
    assert e.prompt_tokens == 100
    assert "T" in e.ts  # ISO timestamp


def test_llm_call_finished_fields():
    e = LLMCallFinished(
        session_id="s1", input_tokens=500, output_tokens=200,
        cache_read_tokens=300, duration_ms=1200.0,
    )
    assert e.cache_read_tokens == 300
    assert e.duration_ms == 1200.0


def test_tool_call_started_preview():
    e = ToolCallStarted(session_id="s1", tool_name="read", args_preview="path=/foo.py")
    assert e.args_preview == "path=/foo.py"


def test_subagent_spawned_defaults():
    e = SubagentSpawned(session_id="s1", agent_id="a1", agent_role="planner")
    assert e.worktree == ""
    assert e.parent_agent_id == ""


def test_daemon_iteration_defaults():
    e = DaemonIteration(iteration=42)
    assert e.budget_remaining_usd == 0.0
    assert e.wall_clock_elapsed_s == 0.0


def test_events_are_frozen():
    e = _tool_started()
    with pytest.raises((AttributeError, TypeError)):
        e.tool_name = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# EventBus — sync listener
# ---------------------------------------------------------------------------


def test_sync_listener_receives_event():
    bus = _bus()
    received = []
    bus.add_listener(received.append)
    bus.emit(_tool_started())
    assert len(received) == 1
    assert isinstance(received[0], ToolCallStarted)


def test_sync_listener_receives_multiple_events():
    bus = _bus()
    received = []
    bus.add_listener(received.append)
    bus.emit(_tool_started())
    bus.emit(LLMCallStarted(session_id="s1", model="m", prompt_tokens=10, turn=1))
    assert len(received) == 2


def test_sync_listener_not_duplicated():
    bus = _bus()
    received = []
    fn = received.append
    bus.add_listener(fn)
    bus.add_listener(fn)  # adding same fn twice → only one
    bus.emit(_tool_started())
    assert len(received) == 1


def test_remove_listener():
    bus = _bus()
    received = []
    bus.add_listener(received.append)
    bus.remove_listener(received.append)
    bus.emit(_tool_started())
    assert received == []


def test_failing_listener_does_not_crash_bus():
    bus = _bus()
    received = []

    def bad(_): raise RuntimeError("boom")

    bus.add_listener(bad)
    bus.add_listener(received.append)
    bus.emit(_tool_started())  # must not raise
    assert len(received) == 1


def test_subscriber_count_listeners():
    bus = _bus()
    assert bus.subscriber_count() == 0
    bus.add_listener(lambda _: None)
    bus.add_listener(lambda _: None)
    assert bus.subscriber_count() == 2


# ---------------------------------------------------------------------------
# EventBus — async queue
# ---------------------------------------------------------------------------


def test_async_queue_receives_event():
    bus = _bus()
    q: asyncio.Queue = asyncio.Queue()
    bus.subscribe(q)
    bus.emit(_tool_started())
    assert not q.empty()
    item = q.get_nowait()
    assert isinstance(item, ToolCallStarted)


def test_unsubscribe_stops_delivery():
    bus = _bus()
    q: asyncio.Queue = asyncio.Queue()
    bus.subscribe(q)
    bus.unsubscribe(q)
    bus.emit(_tool_started())
    assert q.empty()


def test_subscribe_not_duplicated():
    bus = _bus()
    q: asyncio.Queue = asyncio.Queue()
    bus.subscribe(q)
    bus.subscribe(q)
    bus.emit(_tool_started())
    assert q.qsize() == 1


def test_subscriber_count_queues():
    bus = _bus()
    q1: asyncio.Queue = asyncio.Queue()
    q2: asyncio.Queue = asyncio.Queue()
    bus.subscribe(q1)
    bus.subscribe(q2)
    assert bus.subscriber_count() == 2


def test_full_queue_does_not_crash():
    bus = _bus()
    q: asyncio.Queue = asyncio.Queue(maxsize=1)
    bus.subscribe(q)
    bus.emit(_tool_started())
    bus.emit(_tool_started())  # second emit → queue full → logged, no exception


# ---------------------------------------------------------------------------
# EventBus — thread safety
# ---------------------------------------------------------------------------


def test_concurrent_emit_is_safe():
    bus = _bus()
    received = []
    lock = threading.Lock()

    def listener(e):
        with lock:
            received.append(e)

    bus.add_listener(listener)

    def emitter():
        for _ in range(50):
            bus.emit(_tool_started())

    threads = [threading.Thread(target=emitter) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(received) == 200


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------


def test_get_event_bus_returns_singleton():
    reset_event_bus()
    b1 = get_event_bus()
    b2 = get_event_bus()
    assert b1 is b2


def test_reset_event_bus_creates_fresh():
    reset_event_bus()
    b1 = get_event_bus()
    reset_event_bus()
    b2 = get_event_bus()
    assert b1 is not b2


# ---------------------------------------------------------------------------
# ProcessStateWriter
# ---------------------------------------------------------------------------


def test_writer_creates_state_file(tmp_path):
    writer = ProcessStateWriter(lyra_dir=tmp_path, session_id="sess-1")
    bus = _bus()
    writer.attach(bus)
    bus.emit(_tool_started("sess-1"))
    state_path = tmp_path / "process_state.json"
    assert state_path.exists()
    data = json.loads(state_path.read_text())
    assert data["session_id"] == "sess-1"
    assert data["last_tool"]["name"] == "bash"
    assert data["last_tool"]["status"] == "running"


def test_writer_updates_on_tool_finished(tmp_path):
    writer = ProcessStateWriter(lyra_dir=tmp_path, session_id="s")
    bus = _bus()
    writer.attach(bus)
    bus.emit(ToolCallFinished(session_id="s", tool_name="bash", duration_ms=420.0, is_error=False))
    data = json.loads((tmp_path / "process_state.json").read_text())
    assert data["last_tool"]["status"] == "done"
    assert data["last_tool"]["duration_ms"] == pytest.approx(420.0)


def test_writer_updates_on_tool_blocked(tmp_path):
    writer = ProcessStateWriter(lyra_dir=tmp_path, session_id="s")
    bus = _bus()
    writer.attach(bus)
    bus.emit(ToolCallBlocked(session_id="s", tool_name="rm", reason="destructive_pattern"))
    data = json.loads((tmp_path / "process_state.json").read_text())
    assert data["last_tool"]["status"] == "blocked"


def test_writer_accumulates_tokens(tmp_path):
    writer = ProcessStateWriter(lyra_dir=tmp_path, session_id="s")
    bus = _bus()
    writer.attach(bus)
    bus.emit(LLMCallFinished(session_id="s", input_tokens=1000, output_tokens=200,
                              cache_read_tokens=800, duration_ms=500.0))
    bus.emit(LLMCallFinished(session_id="s", input_tokens=500, output_tokens=100,
                              cache_read_tokens=400, duration_ms=300.0))
    data = json.loads((tmp_path / "process_state.json").read_text())
    assert data["token_in"] == 1500
    assert data["token_out"] == 300
    assert data["cache_hit_tokens"] == 1200


def test_writer_updates_on_subagent_spawned(tmp_path):
    writer = ProcessStateWriter(lyra_dir=tmp_path, session_id="s")
    bus = _bus()
    writer.attach(bus)
    bus.emit(SubagentSpawned(session_id="s", agent_id="a1", agent_role="planner",
                              worktree="feat/x"))
    data = json.loads((tmp_path / "process_state.json").read_text())
    assert data["agent_role"] == "planner"
    assert data["worktree"] == "feat/x"


def test_writer_updates_on_daemon_iteration(tmp_path):
    writer = ProcessStateWriter(lyra_dir=tmp_path, session_id="s")
    bus = _bus()
    writer.attach(bus)
    bus.emit(DaemonIteration(iteration=7, budget_remaining_usd=0.42))
    data = json.loads((tmp_path / "process_state.json").read_text())
    assert data["daemon_iteration"] == 7


def test_writer_status_stopped_on_stop_hook(tmp_path):
    writer = ProcessStateWriter(lyra_dir=tmp_path, session_id="s")
    bus = _bus()
    writer.attach(bus)
    bus.emit(StopHookFired(session_id="s", reason="budget_exceeded"))
    data = json.loads((tmp_path / "process_state.json").read_text())
    assert data["status"] == "stopped"


def test_writer_permission_mode_updated(tmp_path):
    writer = ProcessStateWriter(lyra_dir=tmp_path, session_id="s")
    bus = _bus()
    writer.attach(bus)
    bus.emit(PermissionDecision(session_id="s", tool_name="bash",
                                 decision="ALLOWED", mode="plan"))
    data = json.loads((tmp_path / "process_state.json").read_text())
    assert data["permission_mode"] == "plan"


def test_writer_detach_stops_writes(tmp_path):
    writer = ProcessStateWriter(lyra_dir=tmp_path, session_id="s")
    bus = _bus()
    writer.attach(bus)
    writer.detach(bus)
    bus.emit(_tool_started("s"))
    state_path = tmp_path / "process_state.json"
    assert not state_path.exists()


def test_writer_read_state_returns_dict(tmp_path):
    writer = ProcessStateWriter(lyra_dir=tmp_path, session_id="sess-99")
    s = writer.read_state()
    assert s["session_id"] == "sess-99"
    assert isinstance(s, dict)


def test_writer_skips_non_state_bearing_events(tmp_path):
    writer = ProcessStateWriter(lyra_dir=tmp_path, session_id="s")
    bus = _bus()
    writer.attach(bus)
    bus.emit(LLMTokenChunk(session_id="s", delta_text="hi", cumulative_tokens=5, turn=1))
    bus.emit(CostThreshold(session_id="s", cost_usd=0.01, budget_usd=1.0, pct_consumed=0.01))
    bus.emit(CronJobFired(job_name="daily_retro"))
    # None of these are state-bearing → no file written
    assert not (tmp_path / "process_state.json").exists()
