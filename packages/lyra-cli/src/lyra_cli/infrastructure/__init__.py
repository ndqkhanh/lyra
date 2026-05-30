"""Infrastructure module for monitoring, tracing, and reliability.

This module provides production-grade infrastructure components:
- Monitoring: Metrics collection, dashboards, alerts
- Tracing: Distributed tracing across agents and tools
- Reliability: Circuit breakers, retries, fallbacks
- Health: Health checks and diagnostics
- Profiling: Performance profiling and optimization
"""

from __future__ import annotations

from lyra_cli.infrastructure.health import (
    HealthCheck,
    HealthCheckRegistry,
    HealthStatus,
)
from lyra_cli.infrastructure.monitoring import (
    Alert,
    AlertSeverity,
    MetricsCollector,
    MetricType,
    MonitoringService,
)
from lyra_cli.infrastructure.profiler import (
    PerformanceProfiler,
    ProfileReport,
)
from lyra_cli.infrastructure.sla_tracker import (
    SLAComplianceReport,
    SLADefinition,
    SLAMeasurement,
    SLATracker,
    SLAViolation,
    Severity,
)
from lyra_cli.infrastructure.reliability import (
    CircuitBreaker,
    CircuitState,
    Fallback,
    ReliabilityManager,
    RetryPolicy,
)
from lyra_cli.infrastructure.tracing import (
    DistributedTracer,
    Span,
    SpanContext,
    TraceExporter,
)

__all__ = [
    # Monitoring
    "MetricsCollector",
    "MetricType",
    "Alert",
    "AlertSeverity",
    "MonitoringService",
    # Tracing
    "DistributedTracer",
    "Span",
    "SpanContext",
    "TraceExporter",
    # Reliability
    "CircuitBreaker",
    "CircuitState",
    "RetryPolicy",
    "Fallback",
    "ReliabilityManager",
    # Health
    "HealthCheck",
    "HealthStatus",
    "HealthCheckRegistry",
    # Profiling
    "PerformanceProfiler",
    "ProfileReport",
    # SLA (9.4)
    "SLADefinition",
    "SLAMeasurement",
    "SLAViolation",
    "SLAComplianceReport",
    "SLATracker",
    "Severity",
]
