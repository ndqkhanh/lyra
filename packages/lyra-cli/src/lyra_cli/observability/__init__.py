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

from lyra_cli.observability.dashboard_command import (
    DashboardCommand,
    DashboardConfig,
    DashboardPanel,
    PanelType,
)
from lyra_cli.observability.health_command import (
    ComponentHealth,
    DependencyStatus,
    HealthCommand,
    HealthScore,
)
from lyra_cli.observability.metrics_command import (
    MetricsCommand,
    MetricsFilter,
    MetricsFormat,
    MetricsQuery,
    MetricType,
)
from lyra_cli.observability.trace_command import (
    SpanDetail,
    TraceCommand,
    TraceFilter,
    TraceTimeline,
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
    # Commands (9.3)
    "MetricsCommand",
    "MetricsQuery",
    "MetricsFilter",
    "MetricsFormat",
    "MetricType",
    "HealthCommand",
    "ComponentHealth",
    "DependencyStatus",
    "HealthScore",
    "TraceCommand",
    "SpanDetail",
    "TraceFilter",
    "TraceTimeline",
    "DashboardCommand",
    "DashboardConfig",
    "DashboardPanel",
    "PanelType",
]
