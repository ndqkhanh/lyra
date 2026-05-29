"""Lyra SLA — Service Level Agreement management for agent QoS.

Defines SLAs with SLOs/SLIs, collects real-time metrics, enforces compliance,
manages budgets (token, time, cost), auto-scales based on SLA performance,
and generates dashboards, reports, and post-mortems.
"""

from __future__ import annotations

from .auto_scaler import (
    AutoScaler,
    CostQualityTradeoff,
    PredictiveScaler,
    ReactiveScaler,
    ResourceConfig,
    ScalingDecision,
    ScalingDirection,
    ScalingStrategy,
)
from .exceptions import (
    AutoScalerError,
    BudgetExceededError,
    InvalidMetricError,
    SLAError,
    SLANotFoundError,
    SLAViolationError,
)
from .metrics import (
    MetricsCollector,
    MetricSnapshot,
    RollingStats,
)
from .reporting import (
    BreachPostMortem,
    ComplianceReport,
    ComplianceReporter,
    DashboardGenerator,
    PostMortemGenerator,
    ReportExporter,
    ReportFormat,
    TrendAnalysis,
    TrendAnalyzer,
)
from .sla_manager import (
    SLA,
    SLO,
    Budget,
    BudgetType,
    SLAManager,
    SLAViolation,
    SLIMetric,
    ViolationSeverity,
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
