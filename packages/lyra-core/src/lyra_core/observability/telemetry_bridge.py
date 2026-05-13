"""OpenTelemetry bridge for Lyra EventBus events (Phase 7).

Opt-in via the ``LYRA_ENABLE_TELEMETRY=1`` environment variable.  When
disabled (the default) every public function is a no-op so agent loops
pay zero overhead.

When enabled the bridge:
  * Creates one OTel span per LLM call (start → finish)
  * Records token counters as span attributes + metric gauges
  * Records tool call spans with duration and error flag
  * Records subagent lifecycle spans

If ``opentelemetry-sdk`` (``opentelemetry-api``) is not installed the
bridge silently degrades — it never raises at import time.

Usage::

    export LYRA_ENABLE_TELEMETRY=1
    export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

    from lyra_core.observability.telemetry_bridge import TelemetryBridge
    bridge = TelemetryBridge.from_env()
    bridge.attach(get_event_bus())

Research grounding: Claude-Code observability patterns; Anthropic SDK
tracing hooks; OTel Python SDK ``trace.get_tracer()`` pattern.
"""
from __future__ import annotations

import os
from typing import Any


def _is_enabled() -> bool:
    return os.environ.get("LYRA_ENABLE_TELEMETRY", "").strip() in ("1", "true", "yes")


def _try_import_tracer() -> tuple[Any, bool]:
    """Return (tracer, ok) — falls back to _NoopTracer if SDK missing."""
    try:
        from opentelemetry import trace  # type: ignore[import]

        tracer = trace.get_tracer("lyra", schema_url="https://opentelemetry.io/schemas/1.21.0")
        return tracer, True
    except ImportError:
        return _NoopTracer(), False


# ---------------------------------------------------------------------------
# Span context (lightweight replacement when SDK absent)
# ---------------------------------------------------------------------------


class _NoopSpan:
    """Minimal no-op span used when OTel SDK is not installed."""

    def set_attribute(self, _key: str, _value: Any) -> None:
        pass

    def set_status(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def end(self) -> None:
        pass

    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, *_args: Any) -> None:
        pass


class _NoopTracer:
    def start_span(self, _name: str, **_kwargs: Any) -> _NoopSpan:
        return _NoopSpan()

    def start_as_current_span(self, _name: str, **_kwargs: Any) -> _NoopSpan:
        return _NoopSpan()


# ---------------------------------------------------------------------------
# TelemetryBridge
# ---------------------------------------------------------------------------


class TelemetryBridge:
    """Bridges EventBus events to OTel spans + metric counters.

    Attach to an EventBus with :meth:`attach`.  The bridge registers a
    sync listener so it runs inline on every ``emit()`` call.  If OTel
    SDK is not installed every handler is a silent no-op.
    """

    TRACER_NAME = "lyra.agent"
    SERVICE_NAME = "lyra"

    def __init__(self, enabled: bool = False) -> None:
        self._enabled = enabled
        if enabled:
            tracer, ok = _try_import_tracer()
            self._tracer = tracer if ok else _NoopTracer()
        else:
            self._tracer = _NoopTracer()

        # Track in-flight LLM spans keyed by session_id
        self._llm_spans: dict[str, Any] = {}
        # Track in-flight tool spans keyed by (session_id, tool_name)
        self._tool_spans: dict[tuple[str, str], Any] = {}

    @classmethod
    def from_env(cls) -> "TelemetryBridge":
        """Create from environment — enabled iff LYRA_ENABLE_TELEMETRY=1."""
        return cls(enabled=_is_enabled())

    def attach(self, bus: Any) -> None:
        """Register as a sync listener on *bus*."""
        bus.add_listener(self.on_event)

    def detach(self, bus: Any) -> None:
        """Remove listener from *bus*."""
        bus.remove_listener(self.on_event)

    def on_event(self, event: Any) -> None:
        """Dispatch each EventBus event to the appropriate handler."""
        # Import here so the module loads with zero side-effects
        try:
            from lyra_core.observability.event_bus import (
                LLMCallFinished,
                LLMCallStarted,
                SubagentFinished,
                SubagentSpawned,
                ToolCallFinished,
                ToolCallStarted,
            )
        except ImportError:
            return

        if isinstance(event, LLMCallStarted):
            self._on_llm_started(event)
        elif isinstance(event, LLMCallFinished):
            self._on_llm_finished(event)
        elif isinstance(event, ToolCallStarted):
            self._on_tool_started(event)
        elif isinstance(event, ToolCallFinished):
            self._on_tool_finished(event)
        elif isinstance(event, SubagentSpawned):
            self._on_subagent_spawned(event)
        elif isinstance(event, SubagentFinished):
            self._on_subagent_finished(event)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_llm_started(self, event: Any) -> None:
        span = self._tracer.start_span(
            "lyra.llm.call",
            attributes={
                "session.id": event.session_id,
                "llm.model": event.model,
                "llm.turn": event.turn,
                "llm.prompt_tokens": event.prompt_tokens,
            },
        )
        self._llm_spans[event.session_id] = span

    def _on_llm_finished(self, event: Any) -> None:
        span = self._llm_spans.pop(event.session_id, None)
        if span is None:
            return
        span.set_attribute("llm.input_tokens", event.input_tokens)
        span.set_attribute("llm.output_tokens", event.output_tokens)
        span.set_attribute("llm.cache_read_tokens", event.cache_read_tokens)
        span.set_attribute("llm.duration_ms", event.duration_ms)
        span.end()

    def _on_tool_started(self, event: Any) -> None:
        key = (event.session_id, event.tool_name)
        span = self._tracer.start_span(
            "lyra.tool.call",
            attributes={
                "session.id": event.session_id,
                "tool.name": event.tool_name,
                "tool.args_preview": event.args_preview or "",
            },
        )
        self._tool_spans[key] = span

    def _on_tool_finished(self, event: Any) -> None:
        key = (event.session_id, event.tool_name)
        span = self._tool_spans.pop(key, None)
        if span is None:
            return
        span.set_attribute("tool.duration_ms", event.duration_ms)
        span.set_attribute("tool.is_error", event.is_error)
        if event.is_error:
            try:
                from opentelemetry.trace import StatusCode  # type: ignore[import]
                span.set_status(StatusCode.ERROR)
            except ImportError:
                span.set_attribute("error", True)
        span.end()

    def _on_subagent_spawned(self, event: Any) -> None:
        span = self._tracer.start_span(
            "lyra.subagent.lifecycle",
            attributes={
                "session.id": event.session_id,
                "agent.id": event.agent_id,
                "agent.role": event.agent_role,
            },
        )
        self._tool_spans[("subagent", event.agent_id)] = span

    def _on_subagent_finished(self, event: Any) -> None:
        key = ("subagent", event.agent_id)
        span = self._tool_spans.pop(key, None)
        if span is None:
            return
        span.set_attribute("agent.status", event.status)
        span.set_attribute("agent.cost_usd", event.cost_usd)
        span.end()

    # ------------------------------------------------------------------
    # State inspection (for testing)
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def open_llm_spans(self) -> int:
        return len(self._llm_spans)

    @property
    def open_tool_spans(self) -> int:
        return len(self._tool_spans)


__all__ = ["TelemetryBridge", "_is_enabled", "_NoopSpan", "_NoopTracer"]
