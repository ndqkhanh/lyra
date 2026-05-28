"""
Observability module for Lyra - Production Quality & Observability.

Implements:
- OpenTelemetry integration for distributed tracing
- Agent Execution Record (AER) for transparency
- Split-view monitoring dashboard
"""

from lyra_cli.observability.aer import (
    ActionType,
    AERSystem,
    AgentAction,
    AgentDecision,
    AgentExecutionRecord,
)
from lyra_cli.observability.monitoring import (
    AgentStatus,
    MetricPoint,
    MonitoringDashboard,
    SystemHealth,
    TimeSeriesMetric,
)
from lyra_cli.observability.tracing import (
    MetricsProvider,
    Span,
    SpanAttribute,
    SpanEvent,
    SpanKind,
    Trace,
    TracingProvider,
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
