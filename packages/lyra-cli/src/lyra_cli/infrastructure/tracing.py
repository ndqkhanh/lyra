"""Distributed tracing system for tracking requests across agents and tools.

Provides OpenTelemetry-compatible distributed tracing:
- Span-based tracing with parent-child relationships
- Context propagation across async boundaries
- Integration with existing tracing infrastructure
- Export to multiple backends
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lyra_cli.logging_config import get_logger

logger = get_logger(__name__)


class SpanKind(Enum):
    """Type of span operation."""

    INTERNAL = "internal"
    CLIENT = "client"
    SERVER = "server"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(Enum):
    """Span completion status."""

    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanContext:
    """Context for distributed tracing.

    Contains trace and span IDs for propagation across service boundaries.
    """

    trace_id: str
    span_id: str
    parent_span_id: str | None = None

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for serialization."""
        result = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
        }
        if self.parent_span_id:
            result["parent_span_id"] = self.parent_span_id
        return result

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> SpanContext:
        """Create from dictionary."""
        return cls(
            trace_id=data["trace_id"],
            span_id=data["span_id"],
            parent_span_id=data.get("parent_span_id"),
        )


@dataclass
class SpanEvent:
    """An event that occurred during a span."""

    name: str
    timestamp: float
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """A distributed tracing span.

    Represents a single operation in a distributed trace.
    """

    span_id: str
    trace_id: str
    name: str
    kind: SpanKind
    start_time: float
    parent_span_id: str | None = None
    end_time: float | None = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)

    def duration_ms(self) -> float | None:
        """Calculate span duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add an event to the span."""
        event = SpanEvent(
            name=name,
            timestamp=time.time(),
            attributes=attributes or {},
        )
        self.events.append(event)

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value

    def set_status(self, status: SpanStatus, description: str | None = None) -> None:
        """Set span status."""
        self.status = status
        if description:
            self.attributes["status.description"] = description

    def end(self, status: SpanStatus | None = None) -> None:
        """End the span."""
        self.end_time = time.time()
        if status:
            self.status = status

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms(),
            "status": self.status.value,
            "attributes": self.attributes,
            "events": [
                {
                    "name": event.name,
                    "timestamp": event.timestamp,
                    "attributes": event.attributes,
                }
                for event in self.events
            ],
        }


@dataclass
class Trace:
    """A complete distributed trace."""

    trace_id: str
    spans: list[Span] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def add_span(self, span: Span) -> None:
        """Add a span to the trace."""
        self.spans.append(span)

    def get_root_spans(self) -> list[Span]:
        """Get root spans (spans with no parent)."""
        return [s for s in self.spans if s.parent_span_id is None]

    def get_children(self, span_id: str) -> list[Span]:
        """Get child spans of a given span."""
        return [s for s in self.spans if s.parent_span_id == span_id]

    def total_duration_ms(self) -> float | None:
        """Calculate total trace duration from root spans."""
        root_spans = self.get_root_spans()
        if not root_spans:
            return None

        durations = [s.duration_ms() for s in root_spans if s.duration_ms() is not None]
        return max(durations) if durations else None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "trace_id": self.trace_id,
            "created_at": self.created_at,
            "total_duration_ms": self.total_duration_ms(),
            "span_count": len(self.spans),
            "spans": [span.to_dict() for span in self.spans],
        }


class DistributedTracer:
    """Distributed tracing system.

    Features:
    - Automatic span lifecycle management
    - Context propagation
    - Parent-child span relationships
    - Integration with existing tracing callbacks
    """

    def __init__(self):
        """Initialize distributed tracer."""
        self._traces: dict[str, Trace] = {}
        self._active_spans: dict[str, Span] = {}
        self._current_context: SpanContext | None = None

    def start_trace(self, trace_id: str | None = None) -> str:
        """Start a new trace.

        Args:
            trace_id: Optional trace ID (generated if not provided)

        Returns:
            Trace ID
        """
        if trace_id is None:
            trace_id = uuid.uuid4().hex

        trace = Trace(trace_id=trace_id)
        self._traces[trace_id] = trace

        logger.debug(f"Started trace: {trace_id}")
        return trace_id

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """Start a new span.

        Args:
            name: Span name
            kind: Span kind
            trace_id: Trace ID (uses current context if not provided)
            parent_span_id: Parent span ID (uses current context if not provided)
            attributes: Initial attributes

        Returns:
            Started span
        """
        # Use current context if available
        if trace_id is None and self._current_context:
            trace_id = self._current_context.trace_id
        if parent_span_id is None and self._current_context:
            parent_span_id = self._current_context.span_id

        # Create new trace if needed
        if trace_id is None:
            trace_id = self.start_trace()

        span_id = uuid.uuid4().hex
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            name=name,
            kind=kind,
            start_time=time.time(),
            parent_span_id=parent_span_id,
            attributes=attributes or {},
        )

        # Add to trace
        if trace_id in self._traces:
            self._traces[trace_id].add_span(span)

        # Track active span
        self._active_spans[span_id] = span

        logger.debug(f"Started span: {name} ({span_id}) in trace {trace_id}")
        return span

    def end_span(
        self,
        span: Span,
        status: SpanStatus = SpanStatus.OK,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """End a span.

        Args:
            span: Span to end
            status: Final status
            attributes: Final attributes to add
        """
        span.end(status)

        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        # Remove from active spans
        if span.span_id in self._active_spans:
            del self._active_spans[span.span_id]

        logger.debug(
            f"Ended span: {span.name} ({span.span_id})",
            extra={"duration_ms": span.duration_ms()},
        )

    @contextmanager
    def trace_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[Span]:
        """Context manager for automatic span lifecycle.

        Args:
            name: Span name
            kind: Span kind
            attributes: Initial attributes

        Yields:
            Active span
        """
        span = self.start_span(name, kind, attributes=attributes)

        # Set as current context
        previous_context = self._current_context
        self._current_context = SpanContext(
            trace_id=span.trace_id,
            span_id=span.span_id,
            parent_span_id=span.parent_span_id,
        )

        try:
            yield span
            self.end_span(span, SpanStatus.OK)
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            self.end_span(span, SpanStatus.ERROR)
            raise
        finally:
            # Restore previous context
            self._current_context = previous_context

    def get_trace(self, trace_id: str) -> Trace | None:
        """Get a trace by ID."""
        return self._traces.get(trace_id)

    def get_span(self, span_id: str) -> Span | None:
        """Get an active span by ID."""
        return self._active_spans.get(span_id)

    def get_current_context(self) -> SpanContext | None:
        """Get current span context."""
        return self._current_context

    def set_current_context(self, context: SpanContext | None) -> None:
        """Set current span context for propagation."""
        self._current_context = context

    def get_all_traces(self) -> list[Trace]:
        """Get all traces."""
        return list(self._traces.values())

    def export_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Export a trace in standard format.

        Args:
            trace_id: Trace to export

        Returns:
            Trace data or None if not found
        """
        trace = self.get_trace(trace_id)
        if not trace:
            return None

        return trace.to_dict()


class TraceExporter:
    """Export traces to various backends.

    Supports multiple export formats and destinations.
    """

    def __init__(self, tracer: DistributedTracer):
        """Initialize trace exporter.

        Args:
            tracer: Distributed tracer to export from
        """
        self._tracer = tracer

    def export_to_json(self, trace_id: str) -> dict[str, Any] | None:
        """Export trace to JSON format.

        Args:
            trace_id: Trace to export

        Returns:
            JSON-serializable dictionary
        """
        return self._tracer.export_trace(trace_id)

    def export_all_traces(self) -> list[dict[str, Any]]:
        """Export all traces to JSON format.

        Returns:
            List of trace dictionaries
        """
        return [
            trace.to_dict()
            for trace in self._tracer.get_all_traces()
        ]

    def export_to_opentelemetry(self, trace_id: str) -> dict[str, Any] | None:
        """Export trace in OpenTelemetry format.

        Args:
            trace_id: Trace to export

        Returns:
            OpenTelemetry-compatible dictionary
        """
        trace_data = self._tracer.export_trace(trace_id)
        if not trace_data:
            return None

        # Convert to OpenTelemetry format
        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "lyra"}},
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "lyra.infrastructure.tracing"},
                            "spans": [
                                {
                                    "traceId": span["trace_id"],
                                    "spanId": span["span_id"],
                                    "parentSpanId": span.get("parent_span_id"),
                                    "name": span["name"],
                                    "kind": span["kind"].upper(),
                                    "startTimeUnixNano": int(span["start_time"] * 1e9),
                                    "endTimeUnixNano": int(span["end_time"] * 1e9) if span["end_time"] else None,
                                    "attributes": [
                                        {"key": k, "value": {"stringValue": str(v)}}
                                        for k, v in span["attributes"].items()
                                    ],
                                    "events": [
                                        {
                                            "name": event["name"],
                                            "timeUnixNano": int(event["timestamp"] * 1e9),
                                            "attributes": [
                                                {"key": k, "value": {"stringValue": str(v)}}
                                                for k, v in event["attributes"].items()
                                            ],
                                        }
                                        for event in span["events"]
                                    ],
                                    "status": {"code": span["status"].upper()},
                                }
                                for span in trace_data["spans"]
                            ],
                        }
                    ],
                }
            ]
        }


__all__ = [
    "SpanKind",
    "SpanStatus",
    "SpanContext",
    "SpanEvent",
    "Span",
    "Trace",
    "DistributedTracer",
    "TraceExporter",
]
