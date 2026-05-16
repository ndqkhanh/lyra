"""
OpenTelemetry Integration for Distributed Tracing.

Provides observability into agent operations with spans, metrics, and traces.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import time


class SpanKind(Enum):
    """Type of span."""

    INTERNAL = "internal"
    CLIENT = "client"
    SERVER = "server"
    PRODUCER = "producer"
    CONSUMER = "consumer"


@dataclass
class SpanAttribute:
    """A span attribute (key-value pair)."""

    key: str
    value: Any


@dataclass
class SpanEvent:
    """An event within a span."""

    name: str
    timestamp: str
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """A distributed tracing span."""

    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    kind: SpanKind
    start_time: float
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    status: str = "unset"  # unset, ok, error

    def duration_ms(self) -> Optional[float]:
        """Calculate span duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000


@dataclass
class Trace:
    """A complete trace with multiple spans."""

    trace_id: str
    spans: List[Span] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class TracingProvider:
    """
    OpenTelemetry-style tracing provider.

    Features:
    - Distributed tracing with spans
    - Parent-child span relationships
    - Span attributes and events
    - Trace collection and export
    """

    def __init__(self):
        self.traces: Dict[str, Trace] = {}
        self.active_spans: Dict[str, Span] = {}

        # Statistics
        self.stats = {
            "total_traces": 0,
            "total_spans": 0,
            "active_spans": 0,
            "completed_spans": 0,
        }

    def start_trace(self, trace_id: str) -> str:
        """
        Start a new trace.

        Args:
            trace_id: Unique trace identifier

        Returns:
            Trace ID
        """
        trace = Trace(trace_id=trace_id)
        self.traces[trace_id] = trace
        self.stats["total_traces"] += 1

        return trace_id

    def start_span(
        self,
        trace_id: str,
        span_id: str,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """
        Start a new span.

        Args:
            trace_id: Trace this span belongs to
            span_id: Unique span identifier
            name: Span name
            kind: Span kind
            parent_span_id: Parent span ID (for nested spans)
            attributes: Initial attributes

        Returns:
            Span object
        """
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            start_time=time.time(),
            attributes=attributes or {},
        )

        # Add to trace
        if trace_id in self.traces:
            self.traces[trace_id].spans.append(span)

        # Track active span
        self.active_spans[span_id] = span

        # Update statistics
        self.stats["total_spans"] += 1
        self.stats["active_spans"] += 1

        return span

    def end_span(
        self,
        span_id: str,
        status: str = "ok",
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        End a span.

        Args:
            span_id: Span to end
            status: Final status (ok, error)
            attributes: Final attributes to add
        """
        if span_id not in self.active_spans:
            return

        span = self.active_spans[span_id]
        span.end_time = time.time()
        span.status = status

        if attributes:
            span.attributes.update(attributes)

        # Remove from active spans
        del self.active_spans[span_id]

        # Update statistics
        self.stats["active_spans"] -= 1
        self.stats["completed_spans"] += 1

    def add_span_event(
        self,
        span_id: str,
        event_name: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Add an event to a span.

        Args:
            span_id: Span to add event to
            event_name: Event name
            attributes: Event attributes
        """
        if span_id not in self.active_spans:
            return

        span = self.active_spans[span_id]
        event = SpanEvent(
            name=event_name,
            timestamp=datetime.now().isoformat(),
            attributes=attributes or {},
        )
        span.events.append(event)

    def set_span_attribute(self, span_id: str, key: str, value: Any):
        """
        Set a span attribute.

        Args:
            span_id: Span to set attribute on
            key: Attribute key
            value: Attribute value
        """
        if span_id not in self.active_spans:
            return

        span = self.active_spans[span_id]
        span.attributes[key] = value

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a trace by ID."""
        return self.traces.get(trace_id)

    def get_span(self, span_id: str) -> Optional[Span]:
        """Get an active span by ID."""
        return self.active_spans.get(span_id)

    def export_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Export a trace in OpenTelemetry format.

        Args:
            trace_id: Trace to export

        Returns:
            Trace data in dict format
        """
        trace = self.get_trace(trace_id)
        if not trace:
            return None

        return {
            "trace_id": trace.trace_id,
            "created_at": trace.created_at,
            "spans": [
                {
                    "span_id": span.span_id,
                    "trace_id": span.trace_id,
                    "parent_span_id": span.parent_span_id,
                    "name": span.name,
                    "kind": span.kind.value,
                    "start_time": span.start_time,
                    "end_time": span.end_time,
                    "duration_ms": span.duration_ms(),
                    "attributes": span.attributes,
                    "events": [
                        {
                            "name": event.name,
                            "timestamp": event.timestamp,
                            "attributes": event.attributes,
                        }
                        for event in span.events
                    ],
                    "status": span.status,
                }
                for span in trace.spans
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get tracing statistics."""
        return {
            **self.stats,
            "num_traces": len(self.traces),
        }


class MetricsProvider:
    """
    OpenTelemetry-style metrics provider.

    Features:
    - Counter metrics
    - Gauge metrics
    - Histogram metrics
    """

    def __init__(self):
        self.counters: Dict[str, float] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = {}

    def increment_counter(self, name: str, value: float = 1.0):
        """Increment a counter metric."""
        self.counters[name] = self.counters.get(name, 0.0) + value

    def set_gauge(self, name: str, value: float):
        """Set a gauge metric."""
        self.gauges[name] = value

    def record_histogram(self, name: str, value: float):
        """Record a histogram value."""
        if name not in self.histograms:
            self.histograms[name] = []
        self.histograms[name].append(value)

    def get_counter(self, name: str) -> float:
        """Get counter value."""
        return self.counters.get(name, 0.0)

    def get_gauge(self, name: str) -> Optional[float]:
        """Get gauge value."""
        return self.gauges.get(name)

    def get_histogram_stats(self, name: str) -> Optional[Dict[str, float]]:
        """Get histogram statistics."""
        if name not in self.histograms or not self.histograms[name]:
            return None

        values = self.histograms[name]
        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
        }

    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics."""
        return {
            "counters": self.counters.copy(),
            "gauges": self.gauges.copy(),
            "histograms": {
                name: self.get_histogram_stats(name)
                for name in self.histograms
            },
        }
