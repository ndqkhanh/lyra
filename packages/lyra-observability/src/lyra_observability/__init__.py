"""Lyra Observability — Phase A3: Basic Observability Stack.

Provides tracer (span-based tracing), metrics (counters, gauges, histograms),
structured logging, and a plain-text dashboard for Lyra AGI systems.
"""

from __future__ import annotations

from lyra_observability.dashboard import Dashboard, DashboardPanel
from lyra_observability.logger import LogEntry, LogLevel, StructuredLogger
from lyra_observability.metrics import MetricType, MetricValue, MetricsCollector
from lyra_observability.tracer import Span, Tracer

__all__ = [
    "Tracer",
    "Span",
    "MetricsCollector",
    "MetricType",
    "MetricValue",
    "StructuredLogger",
    "LogLevel",
    "LogEntry",
    "Dashboard",
    "DashboardPanel",
]
