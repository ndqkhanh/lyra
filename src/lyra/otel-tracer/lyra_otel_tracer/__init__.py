"""Lyra OTEL Tracer — OpenTelemetry-inspired tracing, token tracking, latency monitoring, cost
attribution, hallucination detection, drift monitoring, and Prometheus export for Lyra multi-agent
systems."""

from __future__ import annotations

from lyra.otel_tracer.agent_spans import (
    AgentSpan,
    SpanContext,
    SpanEvent,
    SpanManager,
    Trace,
)
from lyra.otel_tracer.cost_attributor import (
    CostAttributor,
    CostBreakdown,
    CostConfig,
    CostEntry,
)
from lyra.otel_tracer.drift_integrator import (
    DriftConfig,
    DriftIntegrator,
    DriftMeasurement,
    DriftReport,
)
from lyra.otel_tracer.exceptions import (
    CostAttributionError,
    DriftIntegrationError,
    ExportError,
    HallucinationDetectionError,
    LatencyMonitorError,
    OtelTracerError,
    SpanError,
    TokenTrackerError,
)
from lyra.otel_tracer.hallucination_detector import (
    DetectorConfig,
    HallucinationDetector,
    HallucinationReport,
    HallucinationSignal,
)
from lyra.otel_tracer.latency_monitor import (
    LatencyAlert,
    LatencyMonitor,
    LatencySample,
    LatencyStats,
)
from lyra.otel_tracer.prometheus_export import (
    ExportConfig,
    GrafanaDashboard,
    PrometheusExporter,
    PromMetric,
)
from lyra.otel_tracer.token_tracker import (
    TokenAlert,
    TokenSummary,
    TokenTracker,
    TokenUsage,
)

__all__ = [
    # exceptions
    "OtelTracerError",
    "SpanError",
    "TokenTrackerError",
    "HallucinationDetectionError",
    "CostAttributionError",
    "LatencyMonitorError",
    "DriftIntegrationError",
    "ExportError",
    # agent_spans
    "SpanContext",
    "SpanEvent",
    "AgentSpan",
    "Trace",
    "SpanManager",
    # token_tracker
    "TokenUsage",
    "TokenSummary",
    "TokenAlert",
    "TokenTracker",
    # hallucination_detector
    "DetectorConfig",
    "HallucinationSignal",
    "HallucinationReport",
    "HallucinationDetector",
    # cost_attributor
    "CostEntry",
    "CostBreakdown",
    "CostConfig",
    "CostAttributor",
    # latency_monitor
    "LatencySample",
    "LatencyStats",
    "LatencyAlert",
    "LatencyMonitor",
    # drift_integrator
    "DriftConfig",
    "DriftMeasurement",
    "DriftReport",
    "DriftIntegrator",
    # prometheus_export
    "PromMetric",
    "ExportConfig",
    "GrafanaDashboard",
    "PrometheusExporter",
]
