"""Lyra SLA — Service Level Agreement management for agent QoS.

Defines SLAs with SLOs/SLIs, collects real-time metrics, enforces compliance,
manages budgets (token, time, cost), auto-scales based on SLA performance,
and generates dashboards, reports, and post-mortems.
"""

from __future__ import annotations

from .sla_manager import (
    SLIMetric,
    BudgetType,
    ViolationSeverity,
    SLO,
    SLA,
    SLAViolation,
    Budget,
    SLAManager,
)

from .metrics import (
    MetricSnapshot,
    RollingStats,
    MetricsCollector,
)

from .auto_scaler import (
    ScalingDirection,
    ScalingStrategy,
    ResourceConfig,
    ScalingDecision,
    CostQualityTradeoff,
    ReactiveScaler,
    PredictiveScaler,
    AutoScaler,
)

from .reporting import (
    ReportFormat,
    ComplianceReport,
    TrendAnalysis,
    BreachPostMortem,
    DashboardGenerator,
    ComplianceReporter,
    TrendAnalyzer,
    PostMortemGenerator,
    ReportExporter,
)

from .exceptions import (
    SLAError,
    SLANotFoundError,
    SLAViolationError,
    BudgetExceededError,
    InvalidMetricError,
    AutoScalerError,
)

__all__ = [
    # SLA manager
    "SLIMetric",
    "BudgetType",
    "ViolationSeverity",
    "SLO",
    "SLA",
    "SLAViolation",
    "Budget",
    "SLAManager",
    # Metrics
    "MetricSnapshot",
    "RollingStats",
    "MetricsCollector",
    # Auto-scaler
    "ScalingDirection",
    "ScalingStrategy",
    "ResourceConfig",
    "ScalingDecision",
    "CostQualityTradeoff",
    "ReactiveScaler",
    "PredictiveScaler",
    "AutoScaler",
    # Reporting
    "ReportFormat",
    "ComplianceReport",
    "TrendAnalysis",
    "BreachPostMortem",
    "DashboardGenerator",
    "ComplianceReporter",
    "TrendAnalyzer",
    "PostMortemGenerator",
    "ReportExporter",
    # Exceptions
    "SLAError",
    "SLANotFoundError",
    "SLAViolationError",
    "BudgetExceededError",
    "InvalidMetricError",
    "AutoScalerError",
]
