"""Regression detection package — comparator, history store, and alert manager."""

from __future__ import annotations

from .alert_manager import Alert, AlertChannel, AlertManager, AlertRule, AlertSeverity
from .comparator import BenchmarkComparator, BenchmarkComparisonResult, ComparisonVerdict, MetricComparison
from .history_store import BenchmarkRun, HistoryQuery, HistoryStore

__all__ = [
    # Comparator
    "BenchmarkComparator",
    "BenchmarkComparisonResult",
    "ComparisonVerdict",
    "MetricComparison",
    # History Store
    "BenchmarkRun",
    "HistoryQuery",
    "HistoryStore",
    # Alert Manager
    "Alert",
    "AlertChannel",
    "AlertManager",
    "AlertRule",
    "AlertSeverity",
]
