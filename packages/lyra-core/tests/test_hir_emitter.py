"""Red tests for the HIR (Harness IR) event emitter.

Contract from docs/blocks/13-observability-hir.md:
    - Each event carries: kind, ts, trace_id, span_id, parent_span_id, session_id, actor.
    - JSONL append to .lyra/<session>/events.jsonl.
    - Event kinds used in Phase 1:
        AgentLoop.start, AgentLoop.step, AgentLoop.end,
        Tool.call, Tool.result,
        PermissionBridge.decision,
        Hook.start, Hook.end,
        TDD.state_change.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.observability.hir import (
    HIREmitter,
    HIREvent,
    HIREventKind,
)


def test_emit_writes_jsonl(repo: Path) -> None:
    emitter = HIREmitter(events_path=repo / ".lyra" / "events.jsonl")
    ev = HIREvent(
        kind=HIREventKind.AGENT_LOOP_START,
        session_id="sess-1",
        trace_id="t1",
        span_id="s1",
        actor="generator",
        attrs={"task": "do thing"},
    )
    emitter.emit(ev)
    emitter.close()

    out = (repo / ".lyra" / "events.jsonl").read_text().splitlines()
    assert len(out) == 1
    parsed = json.loads(out[0])
    assert parsed["kind"] == "AgentLoop.start"
    assert parsed["session_id"] == "sess-1"
    assert parsed["trace_id"] == "t1"
    assert parsed["span_id"] == "s1"
    assert parsed["actor"] == "generator"
    assert parsed["attrs"]["task"] == "do thing"
    assert "ts" in parsed


def test_emit_preserves_order(repo: Path) -> None:
    emitter = HIREmitter(events_path=repo / ".lyra" / "events.jsonl")
    for i in range(5):
        emitter.emit(
            HIREvent(
                kind=HIREventKind.AGENT_LOOP_STEP,
                session_id="s",
                trace_id="t",
                span_id=f"sp{i}",
                actor="generator",
                attrs={"step": i},
            )
        )
    emitter.close()

    lines = (repo / ".lyra" / "events.jsonl").read_text().splitlines()
    assert [json.loads(line)["attrs"]["step"] for line in lines] == [0, 1, 2, 3, 4]


def test_emit_parent_span_relationship(repo: Path) -> None:
    emitter = HIREmitter(events_path=repo / ".lyra" / "events.jsonl")
    emitter.emit(
        HIREvent(
            kind=HIREventKind.TOOL_CALL,
            session_id="s",
            trace_id="t",
            span_id="sp2",
            parent_span_id="sp1",
            actor="generator",
            attrs={"tool": "Read"},
        )
    )
    emitter.close()
    parsed = json.loads((repo / ".lyra" / "events.jsonl").read_text())
    assert parsed["parent_span_id"] == "sp1"


def test_emit_redacts_secret_looking_values(repo: Path) -> None:
    """Event attrs that look like secrets are redacted at emit time (see block 13)."""
    emitter = HIREmitter(events_path=repo / ".lyra" / "events.jsonl")
    emitter.emit(
        HIREvent(
            kind=HIREventKind.TOOL_CALL,
            session_id="s",
            trace_id="t",
            span_id="sp1",
            actor="generator",
            attrs={
                "args": {
                    "command": "export AWS_ACCESS=AKIAIOSFODNN7EXAMPLE && echo ok"
                }
            },
        )
    )
    emitter.close()
    parsed = json.loads((repo / ".lyra" / "events.jsonl").read_text())
    # Secret value must not leak verbatim
    assert "AKIAIOSFODNN7EXAMPLE" not in json.dumps(parsed)
    # But a masked indicator should be present
    serialized = json.dumps(parsed)
    assert "[REDACTED" in serialized or "***" in serialized


def test_emit_creates_parent_directories(repo: Path) -> None:
    path = repo / "deep" / "nested" / "events.jsonl"
    emitter = HIREmitter(events_path=path)
    emitter.emit(
        HIREvent(
            kind=HIREventKind.AGENT_LOOP_END,
            session_id="s",
            trace_id="t",
            span_id="sp1",
            actor="generator",
            attrs={"status": "ok"},
        )
    )
    emitter.close()
    assert path.exists()


def test_hir_event_kinds_complete() -> None:
    """Phase 1 kinds must exist; block-13 spec."""
    required = {
        "AGENT_LOOP_START",
        "AGENT_LOOP_STEP",
        "AGENT_LOOP_END",
        "TOOL_CALL",
        "TOOL_RESULT",
        "PERMISSION_DECISION",
        "HOOK_START",
        "HOOK_END",
        "TDD_STATE_CHANGE",
    }
    have = {e.name for e in HIREventKind}
    missing = required - have
    assert not missing, f"missing HIR event kinds: {missing}"


def test_emit_default_ts_is_monotonic(repo: Path) -> None:
    emitter = HIREmitter(events_path=repo / ".lyra" / "events.jsonl")
    for i in range(3):
        emitter.emit(
            HIREvent(
                kind=HIREventKind.AGENT_LOOP_STEP,
                session_id="s",
                trace_id="t",
                span_id=f"sp{i}",
                actor="generator",
                attrs={},
            )
        )
    emitter.close()
    ts = [json.loads(line)["ts"] for line in (repo / ".lyra" / "events.jsonl").read_text().splitlines()]
    assert ts == sorted(ts)


@pytest.mark.parametrize("bad_kind", ["", None, "unknown"])
def test_emit_rejects_invalid_kind(repo: Path, bad_kind) -> None:
    emitter = HIREmitter(events_path=repo / ".lyra" / "events.jsonl")
    with pytest.raises((ValueError, TypeError)):
        emitter.emit(
            HIREvent(
                kind=bad_kind,
                session_id="s",
                trace_id="t",
                span_id="sp",
                actor="generator",
                attrs={},
            )
        )
