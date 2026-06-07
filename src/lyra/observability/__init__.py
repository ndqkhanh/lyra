"""
Observability — metrics dashboard for tokens, cost, latency, tool calls, and errors.
"""

from lyra.observability.dashboard import (
    MetricsDashboard,
    SessionMetrics,
    MetricSnapshot,
)

__version__ = "0.1.0"

__all__ = [
    "MetricsDashboard",
    "SessionMetrics",
    "MetricSnapshot",
]
