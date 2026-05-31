"""Tests for lyra_otel_tracer.exceptions."""

from __future__ import annotations

from lyra_otel_tracer.exceptions import (
    CostAttributionError,
    DriftIntegrationError,
    ExportError,
    HallucinationDetectionError,
    LatencyMonitorError,
    OtelTracerError,
    SpanError,
    TokenTrackerError,
)


class TestExceptions:
    def test_otel_tracer_error_base(self) -> None:
        assert issubclass(SpanError, OtelTracerError)
        assert issubclass(TokenTrackerError, OtelTracerError)
        assert issubclass(HallucinationDetectionError, OtelTracerError)
        assert issubclass(CostAttributionError, OtelTracerError)
        assert issubclass(LatencyMonitorError, OtelTracerError)
        assert issubclass(DriftIntegrationError, OtelTracerError)
        assert issubclass(ExportError, OtelTracerError)

    def test_otel_tracer_error_message(self) -> None:
        err = OtelTracerError("test message")
        assert str(err) == "test message"

    def test_span_error_message(self) -> None:
        err = SpanError("span not found")
        assert str(err) == "span not found"

    def test_token_tracker_error_message(self) -> None:
        err = TokenTrackerError("invalid token count")
        assert str(err) == "invalid token count"

    def test_hallucination_detection_error_message(self) -> None:
        err = HallucinationDetectionError("invalid pattern")
        assert str(err) == "invalid pattern"

    def test_cost_attribution_error_message(self) -> None:
        err = CostAttributionError("invalid cost config")
        assert str(err) == "invalid cost config"

    def test_latency_monitor_error_message(self) -> None:
        err = LatencyMonitorError("invalid stat name")
        assert str(err) == "invalid stat name"

    def test_drift_integration_error_message(self) -> None:
        err = DriftIntegrationError("unknown metric")
        assert str(err) == "unknown metric"

    def test_export_error_message(self) -> None:
        err = ExportError("export failed")
        assert str(err) == "export failed"

    def test_span_error_is_otel_tracer_error(self) -> None:
        assert isinstance(SpanError("test"), OtelTracerError)

    def test_token_tracker_error_is_otel_tracer_error(self) -> None:
        assert isinstance(TokenTrackerError("test"), OtelTracerError)

    def test_hallucination_detection_error_is_otel_tracer_error(self) -> None:
        assert isinstance(HallucinationDetectionError("test"), OtelTracerError)

    def test_cost_attribution_error_is_otel_tracer_error(self) -> None:
        assert isinstance(CostAttributionError("test"), OtelTracerError)

    def test_latency_monitor_error_is_otel_tracer_error(self) -> None:
        assert isinstance(LatencyMonitorError("test"), OtelTracerError)

    def test_drift_integration_error_is_otel_tracer_error(self) -> None:
        assert isinstance(DriftIntegrationError("test"), OtelTracerError)

    def test_export_error_is_otel_tracer_error(self) -> None:
        assert isinstance(ExportError("test"), OtelTracerError)

    def test_exception_with_none_message(self) -> None:
        err = SpanError()
        assert str(err) == ""

    def test_exception_with_empty_message(self) -> None:
        err = TokenTrackerError("")
        assert str(err) == ""

    def test_nested_exception_catch_base(self) -> None:
        try:
            raise SpanError("nested")
        except OtelTracerError as e:
            assert str(e) == "nested"

    def test_exception_catch_all_base(self) -> None:
        errors = [
            SpanError("a"),
            TokenTrackerError("b"),
            HallucinationDetectionError("c"),
            CostAttributionError("d"),
            LatencyMonitorError("e"),
            DriftIntegrationError("f"),
            ExportError("g"),
        ]
        for err in errors:
            assert isinstance(err, Exception)
            assert isinstance(err, OtelTracerError)
