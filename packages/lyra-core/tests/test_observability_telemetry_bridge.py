"""Tests for observability/telemetry_bridge.py (Phase 7 — OTel bridge)."""
from __future__ import annotations

import pytest

from lyra_core.observability.event_bus import (
    EventBus,
    LLMCallFinished,
    LLMCallStarted,
    SubagentFinished,
    SubagentSpawned,
    ToolCallFinished,
    ToolCallStarted,
)
from lyra_core.observability.telemetry_bridge import (
    TelemetryBridge,
    _NoopSpan,
    _NoopTracer,
    _is_enabled,
)


# ---------------------------------------------------------------------------
# _is_enabled
# ---------------------------------------------------------------------------


def test_is_enabled_default_false(monkeypatch):
    monkeypatch.delenv("LYRA_ENABLE_TELEMETRY", raising=False)
    assert not _is_enabled()


@pytest.mark.parametrize("val", ["1", "true", "yes"])
def test_is_enabled_truthy_values(monkeypatch, val):
    monkeypatch.setenv("LYRA_ENABLE_TELEMETRY", val)
    assert _is_enabled()


@pytest.mark.parametrize("val", ["0", "false", "", "no"])
def test_is_enabled_falsy_values(monkeypatch, val):
    monkeypatch.setenv("LYRA_ENABLE_TELEMETRY", val)
    assert not _is_enabled()


# ---------------------------------------------------------------------------
# _NoopSpan / _NoopTracer
# ---------------------------------------------------------------------------


def test_noop_span_all_methods_no_error():
    span = _NoopSpan()
    span.set_attribute("key", "value")
    span.set_status("ok")
    span.end()


def test_noop_span_context_manager():
    with _NoopSpan() as s:
        assert isinstance(s, _NoopSpan)


def test_noop_tracer_returns_noop_span():
    tracer = _NoopTracer()
    span = tracer.start_span("test")
    assert isinstance(span, _NoopSpan)


def test_noop_tracer_start_as_current_span():
    tracer = _NoopTracer()
    span = tracer.start_as_current_span("test")
    assert isinstance(span, _NoopSpan)


# ---------------------------------------------------------------------------
# TelemetryBridge — disabled (default)
# ---------------------------------------------------------------------------


def test_bridge_disabled_by_default():
    bridge = TelemetryBridge(enabled=False)
    assert not bridge.enabled


def test_bridge_from_env_disabled(monkeypatch):
    monkeypatch.delenv("LYRA_ENABLE_TELEMETRY", raising=False)
    bridge = TelemetryBridge.from_env()
    assert not bridge.enabled


def test_bridge_from_env_enabled(monkeypatch):
    monkeypatch.setenv("LYRA_ENABLE_TELEMETRY", "1")
    bridge = TelemetryBridge.from_env()
    assert bridge.enabled


def test_bridge_disabled_events_no_error():
    bridge = TelemetryBridge(enabled=False)
    bridge.on_event(LLMCallStarted(session_id="s1", model="claude", prompt_tokens=100, turn=1))
    bridge.on_event(LLMCallFinished(session_id="s1", input_tokens=500, output_tokens=100,
                                     cache_read_tokens=200, duration_ms=800.0))
    assert bridge.open_llm_spans == 0


# ---------------------------------------------------------------------------
# TelemetryBridge — enabled with NoopTracer (no SDK)
# ---------------------------------------------------------------------------


@pytest.fixture
def bridge_enabled():
    """A bridge that is 'enabled' but uses _NoopTracer (no OTel SDK needed)."""
    b = TelemetryBridge(enabled=True)
    b._tracer = _NoopTracer()  # force noop
    return b


def test_llm_span_lifecycle(bridge_enabled):
    b = bridge_enabled
    b.on_event(LLMCallStarted(session_id="s1", model="claude", prompt_tokens=100, turn=2))
    assert b.open_llm_spans == 1
    b.on_event(LLMCallFinished(session_id="s1", input_tokens=500, output_tokens=100,
                                cache_read_tokens=200, duration_ms=900.0))
    assert b.open_llm_spans == 0


def test_llm_finished_without_started_no_error(bridge_enabled):
    bridge_enabled.on_event(
        LLMCallFinished(session_id="orphan", input_tokens=100, output_tokens=50,
                        cache_read_tokens=0, duration_ms=500.0)
    )
    assert bridge_enabled.open_llm_spans == 0


def test_tool_span_lifecycle(bridge_enabled):
    b = bridge_enabled
    b.on_event(ToolCallStarted(session_id="s1", tool_name="bash", args_preview="ls"))
    assert b.open_tool_spans == 1
    b.on_event(ToolCallFinished(session_id="s1", tool_name="bash", duration_ms=420.0,
                                 is_error=False))
    assert b.open_tool_spans == 0


def test_tool_error_span(bridge_enabled):
    b = bridge_enabled
    b.on_event(ToolCallStarted(session_id="s1", tool_name="rm", args_preview="-rf /"))
    b.on_event(ToolCallFinished(session_id="s1", tool_name="rm", duration_ms=10.0,
                                 is_error=True))
    assert b.open_tool_spans == 0  # span ended


def test_tool_finished_without_started_no_error(bridge_enabled):
    bridge_enabled.on_event(
        ToolCallFinished(session_id="s1", tool_name="ghost", duration_ms=0.0, is_error=False)
    )


def test_subagent_span_lifecycle(bridge_enabled):
    b = bridge_enabled
    b.on_event(SubagentSpawned(session_id="s1", agent_id="a1", agent_role="planner"))
    assert b.open_tool_spans == 1  # stored under ("subagent", agent_id)
    b.on_event(SubagentFinished(session_id="s1", agent_id="a1", status="done", cost_usd=0.03))
    assert b.open_tool_spans == 0


def test_subagent_finished_without_spawned_no_error(bridge_enabled):
    bridge_enabled.on_event(
        SubagentFinished(session_id="s1", agent_id="ghost", status="done", cost_usd=0.0)
    )


def test_multiple_sessions_tracked_independently(bridge_enabled):
    b = bridge_enabled
    b.on_event(LLMCallStarted(session_id="s1", model="c", prompt_tokens=0, turn=1))
    b.on_event(LLMCallStarted(session_id="s2", model="c", prompt_tokens=0, turn=1))
    assert b.open_llm_spans == 2
    b.on_event(LLMCallFinished(session_id="s1", input_tokens=0, output_tokens=0,
                                cache_read_tokens=0, duration_ms=0.0))
    assert b.open_llm_spans == 1


# ---------------------------------------------------------------------------
# Attach / detach
# ---------------------------------------------------------------------------


def test_attach_and_detach():
    bus = EventBus()
    bridge = TelemetryBridge(enabled=False)
    count_before = bus.subscriber_count()
    bridge.attach(bus)
    assert bus.subscriber_count() > count_before
    # Emitting should not raise
    bus.emit(LLMCallStarted(session_id="s1", model="c", prompt_tokens=0, turn=1))
    bridge.detach(bus)
    assert bus.subscriber_count() == count_before
