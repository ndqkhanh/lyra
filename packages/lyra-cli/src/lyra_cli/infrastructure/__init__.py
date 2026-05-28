"""Infrastructure module for monitoring, tracing, and reliability.

This module provides production-grade infrastructure components:
- Monitoring: Metrics collection, dashboards, alerts
- Tracing: Distributed tracing across agents and tools
- Reliability: Circuit breakers, retries, fallbacks
- Health: Health checks and diagnostics
- Profiling: Performance profiling and optimization
"""

from __future__ import annotations

from lyra_cli.infrastructure.monitoring import (
    MetricsCollector,
    MetricType,
    Alert,
    AlertSeverity,
    MonitoringService,
)
from lyra_cli.infrastructure.tracing import (
    DistributedTracer,
    Span,
    SpanContext,
    TraceExporter,
)
from lyra_cli.infrastructure.reliability import (
    CircuitBreaker,
    CircuitState,
    RetryPolicy,
    Fallback,
    ReliabilityManager,
)
from lyra_cli.infrastructure.health import (
    HealthCheck,
    HealthStatus,
    HealthCheckRegistry,
)
from lyra_cli.infrastructure.profiler import (
    PerformanceProfiler,
    ProfileReport,
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
]
