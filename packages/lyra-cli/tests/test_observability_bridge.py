"""Phase E.3 — LifecycleBus events fan out to HIR JSONL + OTel.

The Phase D.3 work added typed lifecycle events emitted from
``session._chat_with_llm``. By v2.7 those events are observable
end-to-end through the same HIR JSONL log that already journals
``user.prompt``, ``slash.dispatch``, and friends — and an optional
OTel collector when ``LYRA_OTEL_COLLECTOR`` is set.

We don't drive the prompt_toolkit loop here; instead we exercise the
bridge function ``_wire_observability_to_lifecycle`` directly with a
freshly-created :class:`HIRLogger` and a stub
:class:`InteractiveSession`. That keeps the test fast and offline
(no real OTel SDK required) while still pinning the contract every
real REPL boot relies on.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


def _make_session(tmp_path: Path):
    from lyra_cli.interactive.session import InteractiveSession

    sess = InteractiveSession(repo_root=tmp_path)
    return sess


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        out.append(json.loads(line))
    return out


def test_lifecycle_events_hit_hir_jsonl(tmp_path: Path) -> None:
    """Every typed bus event must end up as a HIR JSONL row."""
    from lyra_cli.interactive.driver import _wire_observability_to_lifecycle
    from lyra_cli.interactive.hir import HIRLogger, default_event_path
    from lyra_cli.interactive.session import _ensure_lifecycle_bus
    from lyra_core.hooks.lifecycle import LifecycleEvent

    sess = _make_session(tmp_path)
    hir = HIRLogger(default_event_path(tmp_path))
    try:
        _wire_observability_to_lifecycle(sess, hir)

        bus = _ensure_lifecycle_bus(sess)
        assert bus is not None

        bus.emit(LifecycleEvent.SESSION_START, {"model": "mock"})
        bus.emit(LifecycleEvent.TURN_START, {"turn": 1, "input": "hi"})
        bus.emit(
            LifecycleEvent.TOOL_CALL,
            {"name": "Read", "args": {"path": "x"}},
        )
        bus.emit(LifecycleEvent.TURN_COMPLETE, {"turn": 1, "cost_usd": 0.001})
        bus.emit(LifecycleEvent.TURN_REJECTED, {"reason": "budget"})
        bus.emit(LifecycleEvent.SESSION_END, {"turns": 1})
    finally:
        hir.close()

    records = _read_jsonl(default_event_path(tmp_path))
    kinds = [r["kind"] for r in records]

    assert "chat.session_start" in kinds
    assert "chat.turn_start" in kinds
    assert "chat.tool_call" in kinds
    assert "chat.turn_complete" in kinds
    assert "chat.turn_rejected" in kinds
    assert "chat.session_end" in kinds


def test_otel_in_memory_collector_receives_spans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``LYRA_OTEL_COLLECTOR=in-memory`` installs the in-memory bridge."""
    monkeypatch.setenv("LYRA_OTEL_COLLECTOR", "in-memory")

    from lyra_cli.interactive.driver import _wire_observability_to_lifecycle
    from lyra_cli.interactive.hir import HIRLogger, default_event_path
    from lyra_cli.interactive.session import _ensure_lifecycle_bus
    from lyra_core.hooks.lifecycle import LifecycleEvent

    sess = _make_session(tmp_path)
    hir = HIRLogger(default_event_path(tmp_path))
    try:
        _wire_observability_to_lifecycle(sess, hir)

        bus = _ensure_lifecycle_bus(sess)
        bus.emit(LifecycleEvent.TURN_START, {"turn": 7, "input": "ping"})
        bus.emit(LifecycleEvent.TURN_COMPLETE, {"turn": 7, "cost_usd": 0.002})

        collector = getattr(sess, "_otel_collector", None)
        assert collector is not None, "in-memory collector must attach"
        spans = list(getattr(collector, "spans", []))
        assert any(s["kind"] == "chat.turn_start" for s in spans)
        assert any(s["kind"] == "chat.turn_complete" for s in spans)
        # Attributes must round-trip the bus payload verbatim.
        start = next(s for s in spans if s["kind"] == "chat.turn_start")
        assert start["attributes"]["turn"] == 7
        assert start["attributes"]["input"] == "ping"
    finally:
        hir.close()


def test_observability_bridge_survives_buggy_subscribers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing collector must not break the HIR journal path."""
    monkeypatch.setenv("LYRA_OTEL_COLLECTOR", "in-memory")

    from lyra_cli.interactive.driver import _wire_observability_to_lifecycle
    from lyra_cli.interactive.hir import HIRLogger, default_event_path
    from lyra_cli.interactive.session import _ensure_lifecycle_bus
    from lyra_core.hooks.lifecycle import LifecycleEvent

    sess = _make_session(tmp_path)
    hir = HIRLogger(default_event_path(tmp_path))
    try:
        _wire_observability_to_lifecycle(sess, hir)
        collector = getattr(sess, "_otel_collector", None)
        assert collector is not None

        def _explode(_span: dict) -> None:
            raise RuntimeError("collector down")

        collector.submit = _explode  # type: ignore[assignment]

        bus = _ensure_lifecycle_bus(sess)
        bus.emit(LifecycleEvent.TURN_START, {"turn": 1, "input": "still ok"})
    finally:
        hir.close()

    records = _read_jsonl(default_event_path(tmp_path))
    kinds = [r["kind"] for r in records]
    assert "chat.turn_start" in kinds


def test_disabled_collector_keeps_journal_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No env var → no OTel object on the session."""
    monkeypatch.delenv("LYRA_OTEL_COLLECTOR", raising=False)

    from lyra_cli.interactive.driver import _wire_observability_to_lifecycle
    from lyra_cli.interactive.hir import HIRLogger, default_event_path
    from lyra_cli.interactive.session import _ensure_lifecycle_bus
    from lyra_core.hooks.lifecycle import LifecycleEvent

    sess = _make_session(tmp_path)
    hir = HIRLogger(default_event_path(tmp_path))
    try:
        _wire_observability_to_lifecycle(sess, hir)
        bus = _ensure_lifecycle_bus(sess)
        bus.emit(LifecycleEvent.TURN_START, {"turn": 1})
    finally:
        hir.close()

    assert getattr(sess, "_otel_collector", None) is None
    records = _read_jsonl(default_event_path(tmp_path))
    assert any(r["kind"] == "chat.turn_start" for r in records)


def test_skills_activated_event_journals_to_hir(tmp_path: Path) -> None:
    """v3.5 (Phase O.2): ``skills_activated`` lands in HIR JSONL.

    Plugins, ``/trace``, and CI pipelines all read events.jsonl for
    audit. Per-turn skill activation must be visible there alongside
    ``turn_start`` / ``turn_complete`` so a reviewer can correlate
    "which skills did the model see for turn N" with the eventual
    success/failure.
    """
    from lyra_cli.interactive.driver import _wire_observability_to_lifecycle
    from lyra_cli.interactive.hir import HIRLogger, default_event_path
    from lyra_cli.interactive.session import _ensure_lifecycle_bus
    from lyra_core.hooks.lifecycle import LifecycleEvent

    sess = _make_session(tmp_path)
    hir = HIRLogger(default_event_path(tmp_path))
    try:
        _wire_observability_to_lifecycle(sess, hir)
        bus = _ensure_lifecycle_bus(sess)
        assert bus is not None
        bus.emit(
            LifecycleEvent.SKILLS_ACTIVATED,
            {
                "session_id": "abc",
                "turn": 1,
                "activated_skills": [
                    {"skill_id": "tdd-guide", "reason": "keyword:test"},
                ],
            },
        )
    finally:
        hir.close()

    records = _read_jsonl(default_event_path(tmp_path))
    matches = [r for r in records if r["kind"] == "chat.skills.activated"]
    assert matches, f"expected chat.skills.activated row; got {records}"
    data = matches[0]["data"]
    assert data["session_id"] == "abc"
    assert data["turn"] == 1
    skills = data["activated_skills"]
    assert skills[0]["skill_id"] == "tdd-guide"
    assert skills[0]["reason"] == "keyword:test"


def test_skill_telemetry_wires_lifecycle_to_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_wire_skill_telemetry_to_lifecycle`` settles ledger on turn end.

    End-to-end: install the recorder, note an activation as the live
    REPL would, then emit ``turn_complete`` on the bus. The skill
    must be marked ``success`` in the ledger that the wiring helper
    persists to.
    """
    from lyra_cli.interactive.driver import _wire_skill_telemetry_to_lifecycle
    from lyra_cli.interactive.session import _ensure_lifecycle_bus
    from lyra_core.hooks.lifecycle import LifecycleEvent
    from lyra_skills.ledger import load_ledger

    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))

    sess = _make_session(tmp_path)
    sess.session_id = "tele-1"
    sess.turn = 4

    _wire_skill_telemetry_to_lifecycle(sess)
    recorder = getattr(sess, "_skill_activation_recorder", None)
    assert recorder is not None, "wiring must install a recorder"

    recorder.note_activation(
        session_id="tele-1",
        turn=4,
        skill_id="tdd-guide",
        reason="keyword:test",
    )

    bus = _ensure_lifecycle_bus(sess)
    assert bus is not None
    bus.emit(LifecycleEvent.TURN_COMPLETE, {"turn": 4, "cost_usd": 0.0})

    ledger = load_ledger()
    stats = ledger.get("tdd-guide")
    assert stats is not None
    assert stats.successes == 1
    assert stats.failures == 0


def test_skill_telemetry_marks_failure_on_turn_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``turn_rejected`` flips noted activations to ``failure`` in the ledger.

    The rejection ``reason`` must be persisted as
    ``last_failure_reason`` so ``lyra skill reflect`` can later
    surface *why* the skill underperformed.
    """
    from lyra_cli.interactive.driver import _wire_skill_telemetry_to_lifecycle
    from lyra_cli.interactive.session import _ensure_lifecycle_bus
    from lyra_core.hooks.lifecycle import LifecycleEvent
    from lyra_skills.ledger import load_ledger

    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))

    sess = _make_session(tmp_path)
    sess.session_id = "tele-2"
    sess.turn = 9

    _wire_skill_telemetry_to_lifecycle(sess)
    recorder = sess._skill_activation_recorder
    recorder.note_activation(
        session_id="tele-2",
        turn=9,
        skill_id="brainstorming",
        reason="keyword:design",
    )

    bus = _ensure_lifecycle_bus(sess)
    bus.emit(
        LifecycleEvent.TURN_REJECTED,
        {"reason": "secrets-scan: blocked"},
    )

    ledger = load_ledger()
    stats = ledger.get("brainstorming")
    assert stats is not None
    assert stats.failures == 1
    assert stats.successes == 0
    assert "secrets-scan: blocked" in stats.last_failure_reason
