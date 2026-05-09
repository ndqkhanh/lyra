"""Auto-capture: bind LifecycleBus events to MemoryToolset writes."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.hooks.lifecycle import LifecycleBus, LifecycleEvent
from lyra_core.memory.auto_capture import (
    CaptureDirective,
    CapturePolicy,
    MemoryAutoCapture,
)
from lyra_core.memory.auto_memory import AutoMemory, MemoryKind
from lyra_core.memory.memory_tools import MemoryToolset


def _toolset(tmp_path: Path) -> MemoryToolset:
    return MemoryToolset(auto_memory=AutoMemory(root=tmp_path / "mem", project="demo"))


# --- default policy: failed tool call → feedback entry --------------


def test_failed_tool_call_captured_as_feedback(tmp_path: Path) -> None:
    bus = LifecycleBus()
    ts = _toolset(tmp_path)
    capture = MemoryAutoCapture(toolset=ts, bus=bus).bind()

    bus.emit(LifecycleEvent.TOOL_CALL, {
        "tool": "Bash",
        "args": {"command": "rm -rf /forbidden"},
        "result": {"is_error": True, "error": "permission denied"},
    })
    assert capture.captured_count == 1
    entries = ts.auto_memory.all()
    assert len(entries) == 1
    assert entries[0].kind is MemoryKind.FEEDBACK
    assert "Bash" in entries[0].title
    assert "permission denied" in entries[0].body
    assert entries[0].extra["source_event"] == "tool_call"


def test_successful_tool_call_not_captured_by_default(tmp_path: Path) -> None:
    bus = LifecycleBus()
    ts = _toolset(tmp_path)
    capture = MemoryAutoCapture(toolset=ts, bus=bus).bind()

    bus.emit(LifecycleEvent.TOOL_CALL, {
        "tool": "Bash",
        "args": {"command": "echo ok"},
        "result": {"is_error": False, "stdout": "ok\n"},
    })
    assert capture.captured_count == 0
    assert len(ts.auto_memory.all()) == 0


def test_session_end_summary_captured_as_project(tmp_path: Path) -> None:
    bus = LifecycleBus()
    ts = _toolset(tmp_path)
    MemoryAutoCapture(toolset=ts, bus=bus).bind()

    bus.emit(LifecycleEvent.SESSION_END, {
        "session_id": "s-123",
        "summary": "Refactored auth flow; added tests; CI green.",
    })
    entries = ts.auto_memory.all()
    assert len(entries) == 1
    assert entries[0].kind is MemoryKind.PROJECT
    assert "Refactored auth flow" in entries[0].body


def test_session_end_without_summary_skipped(tmp_path: Path) -> None:
    bus = LifecycleBus()
    ts = _toolset(tmp_path)
    MemoryAutoCapture(toolset=ts, bus=bus).bind()
    bus.emit(LifecycleEvent.SESSION_END, {"session_id": "s-x"})
    assert len(ts.auto_memory.all()) == 0


# --- bind / unbind / idempotency -------------------------------------


def test_unbind_stops_capture(tmp_path: Path) -> None:
    bus = LifecycleBus()
    ts = _toolset(tmp_path)
    capture = MemoryAutoCapture(toolset=ts, bus=bus).bind()
    capture.unbind()

    bus.emit(LifecycleEvent.TOOL_CALL, {
        "tool": "Bash", "args": {},
        "result": {"is_error": True, "error": "x"},
    })
    assert capture.captured_count == 0
    assert len(ts.auto_memory.all()) == 0


def test_bind_idempotent(tmp_path: Path) -> None:
    bus = LifecycleBus()
    ts = _toolset(tmp_path)
    capture = MemoryAutoCapture(toolset=ts, bus=bus)
    capture.bind()
    capture.bind()  # second bind is a no-op
    bus.emit(LifecycleEvent.TOOL_CALL, {
        "tool": "x", "args": {},
        "result": {"is_error": True, "error": "x"},
    })
    assert capture.captured_count == 1


# --- redactor still applies on auto-capture path --------------------


def test_auto_capture_redacts_secrets_in_failed_tool_call(tmp_path: Path) -> None:
    """A failure body containing a token must be redacted on persist."""
    bus = LifecycleBus()
    ts = _toolset(tmp_path)
    MemoryAutoCapture(toolset=ts, bus=bus).bind()

    bus.emit(LifecycleEvent.TOOL_CALL, {
        "tool": "GitPush",
        "args": {"token": "ghp_aBcDeF0123456789aBcDeF0123456789aBcD"},
        "result": {"is_error": True,
                   "error": "ghp_aBcDeF0123456789aBcDeF0123456789aBcD revoked"},
    })
    raw = ts.auto_memory.jsonl_path.read_text()
    assert "ghp_aBcDeF" not in raw
    assert "[REDACTED:github_token]" in raw


# --- custom policy ---------------------------------------------------


def test_custom_policy_captures_turn_complete(tmp_path: Path) -> None:
    bus = LifecycleBus()
    ts = _toolset(tmp_path)

    def my_filter(payload):
        return CaptureDirective(
            kind=MemoryKind.PROJECT,
            title=f"turn {payload.get('turn', '?')} done",
            body=str(payload.get("artefact", "")),
        )

    capture = MemoryAutoCapture(
        toolset=ts, bus=bus,
        policy=CapturePolicy(on_turn_complete=my_filter),
    ).bind()
    bus.emit(LifecycleEvent.TURN_COMPLETE,
             {"turn": 3, "artefact": "patched auth.py"})
    assert capture.captured_count == 1
    entries = ts.auto_memory.all()
    assert "turn 3 done" in entries[0].title


def test_custom_policy_skip_when_filter_returns_none(tmp_path: Path) -> None:
    bus = LifecycleBus()
    ts = _toolset(tmp_path)

    def maybe(payload):
        # Capture only when the payload says so.
        if payload.get("interesting"):
            return CaptureDirective(
                kind=MemoryKind.PROJECT, title="x", body="y",
            )
        return None

    capture = MemoryAutoCapture(
        toolset=ts, bus=bus,
        policy=CapturePolicy(on_turn_complete=maybe),
    ).bind()
    bus.emit(LifecycleEvent.TURN_COMPLETE, {"interesting": False})
    assert capture.captured_count == 0
    bus.emit(LifecycleEvent.TURN_COMPLETE, {"interesting": True})
    assert capture.captured_count == 1


# --- bright-line audit trail ----------------------------------------


def test_captured_entry_records_bright_line_in_extra(tmp_path: Path) -> None:
    bus = LifecycleBus()
    ts = _toolset(tmp_path)
    MemoryAutoCapture(toolset=ts, bus=bus).bind()
    bus.emit(LifecycleEvent.TOOL_CALL, {
        "tool": "x", "args": {},
        "result": {"is_error": True, "error": "x"},
    })
    entry = ts.auto_memory.all()[0]
    assert entry.extra.get("bright_line") == "LBL-MEMORY-AUTO-CAPTURE"
