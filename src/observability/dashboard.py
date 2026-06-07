"""
Observability — MetricsDashboard tracking tokens, cost, latency, tool calls,
and errors per session.
"""

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class MetricSnapshot:
    """A single data point in a metrics time series."""

    timestamp: datetime
    value: float
    label: str = ""

    @classmethod
    def now(cls, value: float, label: str = "") -> "MetricSnapshot":
        """Create a snapshot with the current timestamp."""
        return cls(
            timestamp=datetime.now(timezone.utc),
            value=value,
            label=label,
        )


@dataclass
class SessionMetrics:
    """Aggregated metrics for a single session."""

    session_id: str
    total_tokens: int = 0
    total_cost: float = 0.0
    total_latency: float = 0.0
    tool_calls: int = 0
    errors: int = 0
    token_snapshots: list[MetricSnapshot] = field(default_factory=list)
    cost_snapshots: list[MetricSnapshot] = field(default_factory=list)
    latency_snapshots: list[MetricSnapshot] = field(default_factory=list)
    tool_call_snapshots: list[MetricSnapshot] = field(default_factory=list)
    error_snapshots: list[MetricSnapshot] = field(default_factory=list)

    def record_tokens(self, count: int, label: str = "") -> None:
        """Record a token usage data point."""
        self.total_tokens += count
        self.token_snapshots.append(MetricSnapshot.now(float(count), label))

    def record_cost(self, amount: float, label: str = "") -> None:
        """Record a cost data point."""
        self.total_cost += amount
        self.cost_snapshots.append(MetricSnapshot.now(amount, label))

    def record_latency(self, seconds: float, label: str = "") -> None:
        """Record a latency data point."""
        self.total_latency += seconds
        self.latency_snapshots.append(MetricSnapshot.now(seconds, label))

    def record_tool_call(self, tool_name: str = "") -> None:
        """Record a tool call event."""
        self.tool_calls += 1
        self.tool_call_snapshots.append(MetricSnapshot.now(1.0, tool_name))

    def record_error(self, error_type: str = "") -> None:
        """Record an error event."""
        self.errors += 1
        self.error_snapshots.append(MetricSnapshot.now(1.0, error_type))

    @property
    def average_latency(self) -> float:
        """Average latency across all recorded snapshots."""
        if not self.latency_snapshots:
            return 0.0
        return statistics.mean(s.value for s in self.latency_snapshots)

    @property
    def average_cost_per_token(self) -> float:
        """Average cost per token."""
        if self.total_tokens == 0:
            return 0.0
        return self.total_cost / self.total_tokens

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "session_id": self.session_id,
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 6),
            "total_latency": round(self.total_latency, 4),
            "tool_calls": self.tool_calls,
            "errors": self.errors,
            "average_latency": round(self.average_latency, 4),
            "average_cost_per_token": round(self.average_cost_per_token, 8),
            "snapshot_count": len(self.token_snapshots),
        }


class MetricsDashboard:
    """
    Tracks and reports per-session metrics including tokens, cost, latency,
    tool calls, and errors.

    Designed for real-time observability of the agent system.
    """

    def __init__(self) -> None:
        """Initialize the dashboard."""
        self._sessions: dict[str, SessionMetrics] = {}
        self._global_start: datetime = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def get_or_create_session(self, session_id: str) -> SessionMetrics:
        """
        Get existing session metrics or create a new one.

        Args:
            session_id: The session identifier.

        Returns:
            The SessionMetrics object.
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionMetrics(session_id=session_id)
        return self._sessions[session_id]

    def get_session(self, session_id: str) -> SessionMetrics | None:
        """
        Get existing session metrics.

        Args:
            session_id: The session identifier.

        Returns:
            SessionMetrics or None.
        """
        return self._sessions.get(session_id)

    def remove_session(self, session_id: str) -> bool:
        """
        Remove a session from tracking.

        Args:
            session_id: The session identifier.

        Returns:
            True if removed.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_tokens(
        self, session_id: str, count: int, label: str = ""
    ) -> SessionMetrics:
        """Record token usage for a session."""
        metrics = self.get_or_create_session(session_id)
        metrics.record_tokens(count, label)
        return metrics

    def record_cost(
        self, session_id: str, amount: float, label: str = ""
    ) -> SessionMetrics:
        """Record cost for a session."""
        metrics = self.get_or_create_session(session_id)
        metrics.record_cost(amount, label)
        return metrics

    def record_latency(
        self, session_id: str, seconds: float, label: str = ""
    ) -> SessionMetrics:
        """Record latency for a session."""
        metrics = self.get_or_create_session(session_id)
        metrics.record_latency(seconds, label)
        return metrics

    def record_tool_call(
        self, session_id: str, tool_name: str = ""
    ) -> SessionMetrics:
        """Record a tool call for a session."""
        metrics = self.get_or_create_session(session_id)
        metrics.record_tool_call(tool_name)
        return metrics

    def record_error(
        self, session_id: str, error_type: str = ""
    ) -> SessionMetrics:
        """Record an error for a session."""
        metrics = self.get_or_create_session(session_id)
        metrics.record_error(error_type)
        return metrics

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def summary(self, session_id: str | None = None) -> dict[str, Any]:
        """
        Get a summary of metrics.

        Args:
            session_id: Optional session filter.

        Returns:
            Summary dict.
        """
        if session_id is not None:
            metrics = self.get_session(session_id)
            if metrics is None:
                return {"error": "Session not found"}
            return metrics.to_dict()

        return {
            "total_sessions": len(self._sessions),
            "tracking_since": self._global_start.isoformat(),
            "global_total_tokens": sum(
                m.total_tokens for m in self._sessions.values()
            ),
            "global_total_cost": round(
                sum(m.total_cost for m in self._sessions.values()), 6
            ),
            "global_tool_calls": sum(
                m.tool_calls for m in self._sessions.values()
            ),
            "global_errors": sum(m.errors for m in self._sessions.values()),
            "sessions": [
                m.to_dict() for m in sorted(
                    self._sessions.values(),
                    key=lambda x: x.total_tokens,
                    reverse=True,
                )
            ],
        }

    def top_by_tokens(self, n: int = 5) -> list[SessionMetrics]:
        """
        Get the top N sessions by token usage.

        Args:
            n: Number of sessions to return.

        Returns:
            List of SessionMetrics sorted by total tokens descending.
        """
        return sorted(
            self._sessions.values(),
            key=lambda m: m.total_tokens,
            reverse=True,
        )[:n]

    def top_by_cost(self, n: int = 5) -> list[SessionMetrics]:
        """
        Get the top N sessions by cost.

        Args:
            n: Number of sessions to return.

        Returns:
            List of SessionMetrics sorted by total cost descending.
        """
        return sorted(
            self._sessions.values(),
            key=lambda m: m.total_cost,
            reverse=True,
        )[:n]

    def top_by_errors(self, n: int = 5) -> list[SessionMetrics]:
        """
        Get the top N sessions by error count.

        Args:
            n: Number of sessions to return.

        Returns:
            List of SessionMetrics sorted by errors descending.
        """
        return sorted(
            self._sessions.values(),
            key=lambda m: m.errors,
            reverse=True,
        )[:n]

    @property
    def session_count(self) -> int:
        """Number of tracked sessions."""
        return len(self._sessions)
