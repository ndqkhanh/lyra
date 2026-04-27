"""Contract tests for :class:`OpenTelemetryCollector` (v1.7.3).

The v1.7.2 ``OTLPExporter`` only spoke to ``InMemoryCollector``. This
pass adds a **real OTel SDK bridge** so HIR events can fan-out to
Jaeger / Honeycomb / Datadog / any OTLP-compatible backend.

Design:
- Accepts an injected ``tracer_provider`` so tests drive behaviour
  without starting a real OTLP export pipeline.
- Raises :class:`FeatureUnavailable` when called with no provider and
  the ``opentelemetry`` SDK is missing.
- Maps HIR span dicts onto OTel spans: ``kind`` → span name,
  ``attributes`` → span attributes, ``session_id`` → trace attribute.
- Satisfies the existing :class:`Collector` protocol so
  :class:`OTLPExporter` can keep using it.
"""
from __future__ import annotations

import pytest

from lyra_core.lsp_backend import FeatureUnavailable


class _FakeSpan:
    def __init__(self, name: str) -> None:
        self.name = name
        self.attrs: dict = {}
        self.ended = False

    def set_attribute(self, key: str, value) -> None:
        self.attrs[key] = value

    def set_attributes(self, attrs: dict) -> None:
        self.attrs.update(dict(attrs))

    def end(self) -> None:
        self.ended = True

    def __enter__(self) -> "_FakeSpan":
        return self

    def __exit__(self, *exc) -> None:
        self.end()


class _FakeTracer:
    def __init__(self) -> None:
        self.spans: list[_FakeSpan] = []

    def start_as_current_span(self, name: str, attributes: dict | None = None):
        s = _FakeSpan(name)
        if attributes:
            s.set_attributes(attributes)
        self.spans.append(s)
        return s


class _FakeTracerProvider:
    def __init__(self) -> None:
        self.tracer = _FakeTracer()

    def get_tracer(self, name: str, *_, **__) -> _FakeTracer:
        return self.tracer


def test_otel_collector_satisfies_collector_protocol() -> None:
    from lyra_core.observability.otel_export import Collector, OpenTelemetryCollector

    col = OpenTelemetryCollector(tracer_provider=_FakeTracerProvider())
    # Runtime duck-type check.
    assert hasattr(col, "submit")
    assert callable(col.submit)
    # Keeps the existing Protocol shape.
    assert isinstance(col, Collector)


def test_otel_collector_creates_span_per_submit() -> None:
    from lyra_core.observability.otel_export import OpenTelemetryCollector

    tp = _FakeTracerProvider()
    col = OpenTelemetryCollector(tracer_provider=tp)

    col.submit(
        {
            "session_id": "sess-A",
            "ts": "2026-04-30T00:00:00Z",
            "kind": "tool.call",
            "attributes": {"tool.name": "Read", "ok": True},
        }
    )

    assert len(tp.tracer.spans) == 1
    span = tp.tracer.spans[0]
    assert span.name == "tool.call"
    assert span.ended is True
    assert span.attrs["lyra.session_id"] == "sess-A"
    assert span.attrs["tool.name"] == "Read"
    assert span.attrs["ok"] is True


def test_otel_collector_handles_empty_attributes() -> None:
    from lyra_core.observability.otel_export import OpenTelemetryCollector

    tp = _FakeTracerProvider()
    col = OpenTelemetryCollector(tracer_provider=tp)

    col.submit(
        {
            "session_id": "sess-B",
            "ts": "2026-04-30T00:00:01Z",
            "kind": "session.start",
        }
    )

    assert len(tp.tracer.spans) == 1
    assert tp.tracer.spans[0].name == "session.start"


def test_exporter_pipes_events_into_otel_collector() -> None:
    from lyra_core.observability.hir import HirEvent
    from lyra_core.observability.otel_export import OpenTelemetryCollector, OTLPExporter

    tp = _FakeTracerProvider()
    col = OpenTelemetryCollector(tracer_provider=tp)
    exporter = OTLPExporter(collector=col)

    exporter.export(
        [
            HirEvent(
                schema_version="1",
                session_id="sess-C",
                ts="2026-04-30T00:00:02Z",
                kind="tool.result",
                payload={"ok": True, "duration_ms": 42},
            )
        ]
    )

    assert len(tp.tracer.spans) == 1
    span = tp.tracer.spans[0]
    assert span.name == "tool.result"
    assert span.attrs["lyra.session_id"] == "sess-C"
    assert span.attrs["ok"] is True
    assert span.attrs["duration_ms"] == 42


def test_default_provider_missing_raises_feature_unavailable(monkeypatch) -> None:
    import sys

    from lyra_core.observability.otel_export import OpenTelemetryCollector

    saved = sys.modules.get("opentelemetry")
    sys.modules["opentelemetry"] = None  # type: ignore[assignment]
    try:
        with pytest.raises(FeatureUnavailable):
            OpenTelemetryCollector()
    finally:
        if saved is None:
            sys.modules.pop("opentelemetry", None)
        else:
            sys.modules["opentelemetry"] = saved


def test_submit_stringifies_non_primitive_attribute_values() -> None:
    """OTel spec requires attribute values to be primitives or lists of
    primitives. Our bridge must not raise on a dict/nested value — it
    should coerce to a JSON string so the pipeline keeps flowing."""
    from lyra_core.observability.otel_export import OpenTelemetryCollector

    tp = _FakeTracerProvider()
    col = OpenTelemetryCollector(tracer_provider=tp)

    col.submit(
        {
            "session_id": "s",
            "ts": "t",
            "kind": "tool.call",
            "attributes": {"nested": {"inner": 1}, "simple": "ok"},
        }
    )

    span = tp.tracer.spans[0]
    # primitive untouched
    assert span.attrs["simple"] == "ok"
    # dict coerced (either JSON string or repr)
    assert isinstance(span.attrs["nested"], str)
    assert "inner" in span.attrs["nested"]
