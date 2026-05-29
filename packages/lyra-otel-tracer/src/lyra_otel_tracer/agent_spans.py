"""Hierarchical multi-agent tracing inspired by OpenTelemetry."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from lyra_otel_tracer.exceptions import SpanError


@dataclass(frozen=True)
class SpanContext:
    """Identifies a span within a trace."""

    trace_id: str
    span_id: str
    parent_span_id: str = ""


@dataclass(frozen=True)
class SpanEvent:
    """An event recorded on a span."""

    name: str
    timestamp: float
    attributes: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class AgentSpan:
    """Represents a single operation performed by an agent."""

    context: SpanContext
    agent_id: str
    operation: str
    start_time: float
    end_time: float = 0.0
    status: str = "running"
    events: tuple[SpanEvent, ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Trace:
    """A complete trace consisting of a root span and its child spans."""

    trace_id: str
    root_span: AgentSpan
    child_spans: tuple[AgentSpan, ...] = ()
    duration_ms: float = 0.0


class SpanManager:
    """Manages the lifecycle of spans and traces."""

    def __init__(self) -> None:
        self._spans: dict[str, AgentSpan] = {}
        self._traces: dict[str, list[AgentSpan]] = {}

    def _generate_id(self) -> str:
        return uuid.uuid4().hex[:16]

    async def start_span(
        self,
        agent_id: str,
        operation: str,
        parent: SpanContext | None = None,
    ) -> AgentSpan:
        """Start a new span, optionally as a child of a parent span."""
        trace_id = parent.trace_id if parent else uuid.uuid4().hex[:16]
        span_id = self._generate_id()
        parent_span_id = parent.span_id if parent else ""

        context = SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
        )

        span = AgentSpan(
            context=context,
            agent_id=agent_id,
            operation=operation,
            start_time=time.time(),
        )

        self._spans[span_id] = span
        if trace_id not in self._traces:
            self._traces[trace_id] = []
        self._traces[trace_id].append(span)

        return span

    async def end_span(
        self,
        span: AgentSpan,
        status: str = "ok",
    ) -> AgentSpan:
        """Mark a span as completed with the given status."""
        stored = self._spans.get(span.context.span_id, span)
        if stored.status != "running":
            raise SpanError(f"Span {span.context.span_id} is not running")

        ended = AgentSpan(
            context=span.context,
            agent_id=span.agent_id,
            operation=span.operation,
            start_time=span.start_time,
            end_time=time.time(),
            status=status,
            events=span.events,
            metadata=span.metadata,
        )

        self._spans[span.context.span_id] = ended

        # Update in trace list
        trace_id = span.context.trace_id
        if trace_id in self._traces:
            self._traces[trace_id] = [
                ended if s.context.span_id == span.context.span_id else s
                for s in self._traces[trace_id]
            ]

        return ended

    async def add_event(
        self,
        span: AgentSpan,
        name: str,
        attributes: dict[str, str] | None = None,
    ) -> AgentSpan:
        """Add an event to a span and return the updated span."""
        attrs: tuple[tuple[str, str], ...] = ()
        if attributes:
            attrs = tuple(sorted(attributes.items()))

        event = SpanEvent(
            name=name,
            timestamp=time.time(),
            attributes=attrs,
        )

        updated = AgentSpan(
            context=span.context,
            agent_id=span.agent_id,
            operation=span.operation,
            start_time=span.start_time,
            end_time=span.end_time,
            status=span.status,
            events=span.events + (event,),
            metadata=span.metadata,
        )

        self._spans[span.context.span_id] = updated
        trace_id = span.context.trace_id
        if trace_id in self._traces:
            self._traces[trace_id] = [
                updated if s.context.span_id == span.context.span_id else s
                for s in self._traces[trace_id]
            ]

        return updated

    async def get_trace(self, trace_id: str) -> Trace:
        """Retrieve a complete trace by trace_id."""
        if trace_id not in self._traces:
            raise SpanError(f"Trace {trace_id} not found")

        spans = self._traces[trace_id]
        if not spans:
            raise SpanError(f"Trace {trace_id} is empty")

        root = spans[0]
        children = spans[1:]

        duration_ms = 0.0
        if root.end_time > 0 and root.start_time > 0:
            duration_ms = (root.end_time - root.start_time) * 1000

        return Trace(
            trace_id=trace_id,
            root_span=root,
            child_spans=tuple(children),
            duration_ms=duration_ms,
        )

    async def get_active_spans(self) -> tuple[AgentSpan, ...]:
        """Return all spans that are still running."""
        return tuple(
            s for s in self._spans.values() if s.status == "running"
        )
