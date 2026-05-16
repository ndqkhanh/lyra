"""
Observability module for Lyra - Production Quality & Observability.

Implements:
- OpenTelemetry integration for distributed tracing
- Agent Execution Record (AER) for transparency
- Split-view monitoring dashboard
"""

from lyra_cli.observability.tracing import (
    SpanKind,
    SpanAttribute,
    SpanEvent,
    Span,
    Trace,
    TracingProvider,
    MetricsProvider,
)

from lyra_cli.observability.aer import (
    ActionType,
    AgentAction,
    AgentDecision,
    AgentExecutionRecord,
    AERSystem,
)

from lyra_cli.observability.monitoring import (
    MetricPoint,
    TimeSeriesMetric,
    AgentStatus,
    SystemHealth,
    MonitoringDashboard,
)

__all__ = [
    # Tracing
    "SpanKind",
    "SpanAttribute",
    "SpanEvent",
    "Span",
    "Trace",
    "TracingProvider",
    "MetricsProvider",
    # AER
    "ActionType",
    "AgentAction",
    "AgentDecision",
    "AgentExecutionRecord",
    "AERSystem",
    # Monitoring
    "MetricPoint",
    "TimeSeriesMetric",
    "AgentStatus",
    "SystemHealth",
    "MonitoringDashboard",
]
