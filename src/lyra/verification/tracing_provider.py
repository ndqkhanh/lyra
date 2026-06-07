"""
TracingProvider — Unified OpenTelemetry tracing interface.

Backend-swappable between Langfuse, Phoenix, and raw OpenTelemetry.
Auto-instrumentation for tools, agents, router, memory, hooks.
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Iterator, Literal


class SpanStatus(Enum):
    """Span status codes."""

    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


@dataclass
class SpanEvent:
    """Event within a span."""

    name: str
    timestamp: datetime
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceSpan:
    """A tracing span."""

    span_id: str
    trace_id: str
    parent_id: str | None
    name: str
    span_type: str  # "tool", "agent", "router", "memory", "hook"
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)
    status: SpanStatus = SpanStatus.UNSET


class TracingBackend:
    """Base class for tracing backends."""

    def start_span(
        self,
        name: str,
        span_type: str,
        trace_id: str | None = None,
        parent_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TraceSpan:
        """Start a new span."""
        raise NotImplementedError

    def end_span(self, span: TraceSpan, status: SpanStatus = SpanStatus.OK):
        """End a span."""
        raise NotImplementedError

    def add_event(self, span: TraceSpan, name: str, attributes: dict[str, Any] | None = None):
        """Add an event to a span."""
        raise NotImplementedError


class LangfuseBackend(TracingBackend):
    """Langfuse tracing backend."""

    def __init__(self, **config):
        """
        Initialize Langfuse backend.

        Args:
            config: Langfuse configuration (api_key, host, etc.)
        """
        self.config = config
        self._client = None
        self._traces: dict[str, TraceSpan] = {}

    def _get_client(self):
        """Lazy-load Langfuse client."""
        if self._client is None:
            try:
                from langfuse import Langfuse

                self._client = Langfuse(**self.config)
            except ImportError:
                raise ImportError(
                    "Langfuse not installed. Install with: pip install langfuse"
                )
        return self._client

    def start_span(
        self,
        name: str,
        span_type: str,
        trace_id: str | None = None,
        parent_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TraceSpan:
        """Start a span."""
        import uuid

        span_id = str(uuid.uuid4())
        trace_id = trace_id or span_id

        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_id=parent_id,
            name=name,
            span_type=span_type,
            start_time=datetime.now(),
            attributes=attributes or {},
        )

        self._traces[span_id] = span
        return span

    def end_span(self, span: TraceSpan, status: SpanStatus = SpanStatus.OK):
        """End a span."""
        span.end_time = datetime.now()
        span.duration_ms = (
            (span.end_time - span.start_time).total_seconds() * 1000
        )
        span.status = status

        # Send to Langfuse
        try:
            client = self._get_client()
            client.span(
                id=span.span_id,
                trace_id=span.trace_id,
                parent_observation_id=span.parent_id,
                name=span.name,
                start_time=span.start_time,
                end_time=span.end_time,
                metadata=span.attributes,
                level=status.value,
            )
        except Exception:
            # Don't fail the operation if tracing fails
            pass

    def add_event(
        self, span: TraceSpan, name: str, attributes: dict[str, Any] | None = None
    ):
        """Add an event to a span."""
        event = SpanEvent(
            name=name, timestamp=datetime.now(), attributes=attributes or {}
        )
        span.events.append(event)


class PhoenixBackend(TracingBackend):
    """Phoenix (Arize AI) tracing backend."""

    def __init__(self, **config):
        """
        Initialize Phoenix backend.

        Args:
            config: Phoenix configuration
        """
        self.config = config
        self._traces: dict[str, TraceSpan] = {}

    def start_span(
        self,
        name: str,
        span_type: str,
        trace_id: str | None = None,
        parent_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TraceSpan:
        """Start a span."""
        import uuid

        span_id = str(uuid.uuid4())
        trace_id = trace_id or span_id

        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_id=parent_id,
            name=name,
            span_type=span_type,
            start_time=datetime.now(),
            attributes=attributes or {},
        )

        self._traces[span_id] = span
        return span

    def end_span(self, span: TraceSpan, status: SpanStatus = SpanStatus.OK):
        """End a span."""
        span.end_time = datetime.now()
        span.duration_ms = (
            (span.end_time - span.start_time).total_seconds() * 1000
        )
        span.status = status

        # In real implementation: send to Phoenix
        # For now: store locally
        pass

    def add_event(
        self, span: TraceSpan, name: str, attributes: dict[str, Any] | None = None
    ):
        """Add an event."""
        event = SpanEvent(
            name=name, timestamp=datetime.now(), attributes=attributes or {}
        )
        span.events.append(event)


class OTelBackend(TracingBackend):
    """Raw OpenTelemetry backend."""

    def __init__(self, **config):
        """
        Initialize OpenTelemetry backend.

        Args:
            config: OTel configuration (endpoint, headers, etc.)
        """
        self.config = config
        self._tracer = None
        self._traces: dict[str, TraceSpan] = {}

    def _get_tracer(self):
        """Lazy-load OTel tracer."""
        if self._tracer is None:
            try:
                from opentelemetry import trace

                self._tracer = trace.get_tracer("lyra")
            except ImportError:
                raise ImportError(
                    "OpenTelemetry not installed. Install with: pip install opentelemetry-api"
                )
        return self._tracer

    def start_span(
        self,
        name: str,
        span_type: str,
        trace_id: str | None = None,
        parent_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TraceSpan:
        """Start a span."""
        import uuid

        span_id = str(uuid.uuid4())
        trace_id = trace_id or span_id

        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_id=parent_id,
            name=name,
            span_type=span_type,
            start_time=datetime.now(),
            attributes=attributes or {},
        )

        self._traces[span_id] = span
        return span

    def end_span(self, span: TraceSpan, status: SpanStatus = SpanStatus.OK):
        """End a span."""
        span.end_time = datetime.now()
        span.duration_ms = (
            (span.end_time - span.start_time).total_seconds() * 1000
        )
        span.status = status

    def add_event(
        self, span: TraceSpan, name: str, attributes: dict[str, Any] | None = None
    ):
        """Add an event."""
        event = SpanEvent(
            name=name, timestamp=datetime.now(), attributes=attributes or {}
        )
        span.events.append(event)


class TracingProvider:
    """
    Unified tracing interface with backend-swappable support.

    Spans are emitted for:
    - Agent invocation (entire session or subagent run)
    - Tool call (each Bash/Read/Write/etc.)
    - Router decision (model selected, cost estimate)
    - Memory operation (retrieval, storage)
    - Hook execution (each hook triggered)
    """

    def __init__(
        self, backend: Literal["langfuse", "phoenix", "otel"] = "otel", **config
    ):
        """
        Initialize tracing provider.

        Args:
            backend: Tracing backend to use
            config: Backend-specific configuration
        """
        self.backend_name = backend
        self.backend = self._init_backend(backend, config)
        self._current_span: TraceSpan | None = None

    def _init_backend(
        self, backend: str, config: dict[str, Any]
    ) -> TracingBackend:
        """Initialize tracing backend."""
        if backend == "langfuse":
            return LangfuseBackend(**config)
        elif backend == "phoenix":
            return PhoenixBackend(**config)
        elif backend == "otel":
            return OTelBackend(**config)
        else:
            raise ValueError(f"Unknown backend: {backend}")

    @contextmanager
    def span(
        self,
        name: str,
        span_type: str = "agent",
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[TraceSpan]:
        """
        Context manager for tracing spans.

        Args:
            name: Span name
            span_type: Type of span (tool, agent, router, memory, hook)
            attributes: Span attributes

        Yields:
            Active span
        """
        # Determine parent
        parent_id = self._current_span.span_id if self._current_span else None
        trace_id = (
            self._current_span.trace_id if self._current_span else None
        )

        # Start span
        span = self.backend.start_span(
            name=name,
            span_type=span_type,
            trace_id=trace_id,
            parent_id=parent_id,
            attributes=attributes or {},
        )

        # Set attributes
        span.attributes["lyra.type"] = span_type
        for k, v in (attributes or {}).items():
            span.attributes[f"lyra.{k}"] = v

        # Set as current
        previous_span = self._current_span
        self._current_span = span

        try:
            yield span
            # Success
            self.backend.end_span(span, SpanStatus.OK)
        except Exception as e:
            # Error
            self.backend.add_event(
                span, "exception", {"exception": str(e), "type": type(e).__name__}
            )
            self.backend.end_span(span, SpanStatus.ERROR)
            raise
        finally:
            # Restore previous span
            self._current_span = previous_span

    @asynccontextmanager
    async def async_span(
        self,
        name: str,
        span_type: str = "agent",
        attributes: dict[str, Any] | None = None,
    ) -> AsyncIterator[TraceSpan]:
        """
        Async context manager for tracing spans.

        Args:
            name: Span name
            span_type: Type of span
            attributes: Span attributes

        Yields:
            Active span
        """
        parent_id = self._current_span.span_id if self._current_span else None
        trace_id = self._current_span.trace_id if self._current_span else None

        span = self.backend.start_span(
            name=name,
            span_type=span_type,
            trace_id=trace_id,
            parent_id=parent_id,
            attributes=attributes or {},
        )

        span.attributes["lyra.type"] = span_type
        for k, v in (attributes or {}).items():
            span.attributes[f"lyra.{k}"] = v

        previous_span = self._current_span
        self._current_span = span

        try:
            yield span
            self.backend.end_span(span, SpanStatus.OK)
        except Exception as e:
            self.backend.add_event(
                span, "exception", {"exception": str(e), "type": type(e).__name__}
            )
            self.backend.end_span(span, SpanStatus.ERROR)
            raise
        finally:
            self._current_span = previous_span


class AutoInstrumentor:
    """
    Auto-instrument Lyra's core components.

    Wraps key methods with tracing spans. No manual instrumentation required.
    """

    def __init__(self, tracer: TracingProvider):
        """
        Initialize auto-instrumentor.

        Args:
            tracer: Tracing provider
        """
        self.tracer = tracer

    def instrument_tool_registry(self, registry: Any):
        """
        Wrap tool handlers with tracing.

        Args:
            registry: Tool registry to instrument
        """
        if not hasattr(registry, "_tools"):
            return

        for name, tool in registry._tools.items():
            original = tool.handler

            async def traced_handler(*args, **kwargs):
                with self.tracer.span(
                    f"tool.{name}",
                    "tool",
                    {"tool.name": name, "tool.category": getattr(tool, "category", "unknown")},
                ):
                    return await original(*args, **kwargs)

            tool.handler = traced_handler

    def instrument_agent_dispatcher(self, dispatcher: Any):
        """
        Wrap agent dispatch with tracing.

        Args:
            dispatcher: Agent dispatcher to instrument
        """
        if not hasattr(dispatcher, "dispatch"):
            return

        original_dispatch = dispatcher.dispatch

        async def traced_dispatch(*args, **kwargs):
            agent_name = kwargs.get("agent_name", "primary")
            with self.tracer.span(
                f"agent.{agent_name}",
                "agent",
                {"agent.name": agent_name},
            ):
                return await original_dispatch(*args, **kwargs)

        dispatcher.dispatch = traced_dispatch

    def instrument_router(self, router: Any):
        """
        Wrap router decisions with tracing.

        Args:
            router: Model router to instrument
        """
        if not hasattr(router, "route"):
            return

        original_route = router.route

        def traced_route(*args, **kwargs):
            with self.tracer.span("router.decision", "router"):
                result = original_route(*args, **kwargs)
                # Add routing info to span
                if self.tracer._current_span and isinstance(result, dict):
                    self.tracer._current_span.attributes.update({
                        "lyra.model": result.get("model", "unknown"),
                        "lyra.provider": result.get("provider", "unknown"),
                    })
                return result

        router.route = traced_route

    def instrument_memory_store(self, store: Any):
        """
        Wrap memory operations with tracing.

        Args:
            store: Memory store to instrument
        """
        if hasattr(store, "get"):
            original_get = store.get

            async def traced_get(*args, **kwargs):
                with self.tracer.span("memory.get", "memory"):
                    return await original_get(*args, **kwargs)

            store.get = traced_get

        if hasattr(store, "set"):
            original_set = store.set

            async def traced_set(*args, **kwargs):
                with self.tracer.span("memory.set", "memory"):
                    return await original_set(*args, **kwargs)

            store.set = traced_set

    def instrument_hook_engine(self, engine: Any):
        """
        Wrap hook execution with tracing.

        Args:
            engine: Hook engine to instrument
        """
        if not hasattr(engine, "fire"):
            return

        original_fire = engine.fire

        async def traced_fire(hook_name: str, *args, **kwargs):
            with self.tracer.span(
                f"hook.{hook_name}",
                "hook",
                {"hook.name": hook_name},
            ):
                return await original_fire(hook_name, *args, **kwargs)

        engine.fire = traced_fire
