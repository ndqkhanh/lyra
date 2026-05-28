"""Tests for infrastructure distributed tracing system."""

from __future__ import annotations

import pytest
from lyra_cli.infrastructure.tracing import (
    DistributedTracer,
    Span,
    SpanContext,
    SpanKind,
    SpanStatus,
    Trace,
    TraceExporter,
)


class TestSpanContext:
    """Tests for SpanContext."""

    def test_span_context_creation(self):
        """Test creating a span context."""
        context = SpanContext(
            trace_id="trace123",
            span_id="span456",
            parent_span_id="parent789",
        )

        assert context.trace_id == "trace123"
        assert context.span_id == "span456"
        assert context.parent_span_id == "parent789"

    def test_span_context_to_dict(self):
        """Test converting span context to dictionary."""
        context = SpanContext(
            trace_id="trace123",
            span_id="span456",
            parent_span_id="parent789",
        )

        context_dict = context.to_dict()
        assert context_dict["trace_id"] == "trace123"
        assert context_dict["span_id"] == "span456"
        assert context_dict["parent_span_id"] == "parent789"

    def test_span_context_from_dict(self):
        """Test creating span context from dictionary."""
        data = {
            "trace_id": "trace123",
            "span_id": "span456",
            "parent_span_id": "parent789",
        }

        context = SpanContext.from_dict(data)
        assert context.trace_id == "trace123"
        assert context.span_id == "span456"
        assert context.parent_span_id == "parent789"


class TestSpan:
    """Tests for Span."""

    def test_span_creation(self):
        """Test creating a span."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            name="test_operation",
            kind=SpanKind.INTERNAL,
            start_time=1000.0,
        )

        assert span.span_id == "span123"
        assert span.trace_id == "trace456"
        assert span.name == "test_operation"
        assert span.kind == SpanKind.INTERNAL
        assert span.status == SpanStatus.UNSET

    def test_span_duration(self):
        """Test calculating span duration."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            name="test_operation",
            kind=SpanKind.INTERNAL,
            start_time=1000.0,
        )

        span.end_time = 1002.5
        duration = span.duration_ms()

        assert duration == 2500.0

    def test_span_add_event(self):
        """Test adding events to span."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            name="test_operation",
            kind=SpanKind.INTERNAL,
            start_time=1000.0,
        )

        span.add_event("test_event", {"key": "value"})

        assert len(span.events) == 1
        assert span.events[0].name == "test_event"
        assert span.events[0].attributes["key"] == "value"

    def test_span_set_attribute(self):
        """Test setting span attributes."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            name="test_operation",
            kind=SpanKind.INTERNAL,
            start_time=1000.0,
        )

        span.set_attribute("http.method", "GET")
        span.set_attribute("http.status_code", 200)

        assert span.attributes["http.method"] == "GET"
        assert span.attributes["http.status_code"] == 200

    def test_span_set_status(self):
        """Test setting span status."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            name="test_operation",
            kind=SpanKind.INTERNAL,
            start_time=1000.0,
        )

        span.set_status(SpanStatus.ERROR, "Operation failed")

        assert span.status == SpanStatus.ERROR
        assert span.attributes["status.description"] == "Operation failed"

    def test_span_to_dict(self):
        """Test converting span to dictionary."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            name="test_operation",
            kind=SpanKind.INTERNAL,
            start_time=1000.0,
            end_time=1002.0,
        )

        span_dict = span.to_dict()
        assert span_dict["span_id"] == "span123"
        assert span_dict["trace_id"] == "trace456"
        assert span_dict["name"] == "test_operation"
        assert span_dict["kind"] == "internal"
        assert span_dict["duration_ms"] == 2000.0


class TestTrace:
    """Tests for Trace."""

    def test_trace_creation(self):
        """Test creating a trace."""
        trace = Trace(trace_id="trace123")

        assert trace.trace_id == "trace123"
        assert len(trace.spans) == 0

    def test_trace_add_span(self):
        """Test adding spans to trace."""
        trace = Trace(trace_id="trace123")

        span1 = Span(
            span_id="span1",
            trace_id="trace123",
            name="operation1",
            kind=SpanKind.INTERNAL,
            start_time=1000.0,
        )

        span2 = Span(
            span_id="span2",
            trace_id="trace123",
            name="operation2",
            kind=SpanKind.INTERNAL,
            start_time=1001.0,
            parent_span_id="span1",
        )

        trace.add_span(span1)
        trace.add_span(span2)

        assert len(trace.spans) == 2

    def test_trace_get_root_spans(self):
        """Test getting root spans."""
        trace = Trace(trace_id="trace123")

        root_span = Span(
            span_id="span1",
            trace_id="trace123",
            name="root",
            kind=SpanKind.INTERNAL,
            start_time=1000.0,
        )

        child_span = Span(
            span_id="span2",
            trace_id="trace123",
            name="child",
            kind=SpanKind.INTERNAL,
            start_time=1001.0,
            parent_span_id="span1",
        )

        trace.add_span(root_span)
        trace.add_span(child_span)

        root_spans = trace.get_root_spans()
        assert len(root_spans) == 1
        assert root_spans[0].span_id == "span1"

    def test_trace_get_children(self):
        """Test getting child spans."""
        trace = Trace(trace_id="trace123")

        parent_span = Span(
            span_id="parent",
            trace_id="trace123",
            name="parent",
            kind=SpanKind.INTERNAL,
            start_time=1000.0,
        )

        child1 = Span(
            span_id="child1",
            trace_id="trace123",
            name="child1",
            kind=SpanKind.INTERNAL,
            start_time=1001.0,
            parent_span_id="parent",
        )

        child2 = Span(
            span_id="child2",
            trace_id="trace123",
            name="child2",
            kind=SpanKind.INTERNAL,
            start_time=1002.0,
            parent_span_id="parent",
        )

        trace.add_span(parent_span)
        trace.add_span(child1)
        trace.add_span(child2)

        children = trace.get_children("parent")
        assert len(children) == 2


class TestDistributedTracer:
    """Tests for DistributedTracer."""

    def test_start_trace(self):
        """Test starting a trace."""
        tracer = DistributedTracer()
        trace_id = tracer.start_trace()

        assert trace_id is not None
        trace = tracer.get_trace(trace_id)
        assert trace is not None
        assert trace.trace_id == trace_id

    def test_start_span(self):
        """Test starting a span."""
        tracer = DistributedTracer()
        trace_id = tracer.start_trace()

        span = tracer.start_span(
            name="test_operation",
            kind=SpanKind.INTERNAL,
            trace_id=trace_id,
        )

        assert span.name == "test_operation"
        assert span.trace_id == trace_id
        assert span.kind == SpanKind.INTERNAL

    def test_end_span(self):
        """Test ending a span."""
        tracer = DistributedTracer()
        trace_id = tracer.start_trace()

        span = tracer.start_span(
            name="test_operation",
            trace_id=trace_id,
        )

        tracer.end_span(span, SpanStatus.OK)

        assert span.end_time is not None
        assert span.status == SpanStatus.OK

    def test_trace_span_context_manager(self):
        """Test trace_span context manager."""
        tracer = DistributedTracer()

        with tracer.trace_span("test_operation") as span:
            span.set_attribute("test", "value")

        assert span.end_time is not None
        assert span.status == SpanStatus.OK
        assert span.attributes["test"] == "value"

    def test_trace_span_error_handling(self):
        """Test trace_span error handling."""
        tracer = DistributedTracer()

        with pytest.raises(ValueError):
            with tracer.trace_span("test_operation") as span:
                raise ValueError("Test error")

        assert span.status == SpanStatus.ERROR
        assert "error.type" in span.attributes
        assert span.attributes["error.type"] == "ValueError"

    def test_nested_spans(self):
        """Test nested span creation."""
        tracer = DistributedTracer()

        with tracer.trace_span("parent") as parent_span:
            with tracer.trace_span("child") as child_span:
                assert child_span.parent_span_id == parent_span.span_id

    def test_get_current_context(self):
        """Test getting current context."""
        tracer = DistributedTracer()

        with tracer.trace_span("test_operation") as span:
            context = tracer.get_current_context()
            assert context is not None
            assert context.span_id == span.span_id
            assert context.trace_id == span.trace_id

    def test_export_trace(self):
        """Test exporting trace."""
        tracer = DistributedTracer()
        trace_id = tracer.start_trace()

        span = tracer.start_span("test_operation", trace_id=trace_id)
        tracer.end_span(span)

        exported = tracer.export_trace(trace_id)
        assert exported is not None
        assert exported["trace_id"] == trace_id
        assert len(exported["spans"]) == 1


class TestTraceExporter:
    """Tests for TraceExporter."""

    def test_export_to_json(self):
        """Test exporting trace to JSON."""
        tracer = DistributedTracer()
        exporter = TraceExporter(tracer)

        trace_id = tracer.start_trace()
        span = tracer.start_span("test_operation", trace_id=trace_id)
        tracer.end_span(span)

        json_data = exporter.export_to_json(trace_id)
        assert json_data is not None
        assert json_data["trace_id"] == trace_id

    def test_export_all_traces(self):
        """Test exporting all traces."""
        tracer = DistributedTracer()
        exporter = TraceExporter(tracer)

        # Create multiple traces
        for i in range(3):
            trace_id = tracer.start_trace()
            span = tracer.start_span(f"operation_{i}", trace_id=trace_id)
            tracer.end_span(span)

        all_traces = exporter.export_all_traces()
        assert len(all_traces) == 3

    def test_export_to_opentelemetry(self):
        """Test exporting to OpenTelemetry format."""
        tracer = DistributedTracer()
        exporter = TraceExporter(tracer)

        trace_id = tracer.start_trace()
        span = tracer.start_span("test_operation", trace_id=trace_id)
        span.set_attribute("http.method", "GET")
        tracer.end_span(span)

        otel_data = exporter.export_to_opentelemetry(trace_id)
        assert otel_data is not None
        assert "resourceSpans" in otel_data
        assert len(otel_data["resourceSpans"]) > 0
