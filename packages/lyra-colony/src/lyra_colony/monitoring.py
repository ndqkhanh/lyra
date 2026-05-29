"""Colony observability: monitoring, metrics, alerting, and audit logs."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class MonitoringError(Exception):
    """Base exception for monitoring errors."""


class AlertThresholdExceededError(MonitoringError):
    """Raised when a monitored metric exceeds an alert threshold."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AgentStatus(Enum):
    """Current operational status of a colony agent."""

    INITIALIZING = auto()
    READY = auto()
    BUSY = auto()
    IDLE = auto()
    DEGRADED = auto()
    UNRESPONSIVE = auto()
    TERMINATED = auto()


class AlertSeverity(Enum):
    """Severity level for monitoring alerts."""

    INFO = auto()
    WARNING = auto()
    CRITICAL = auto()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return uuid4().hex[:12]


def _now() -> float:
    return time.monotonic()


# ---------------------------------------------------------------------------
# Dataclass models
# ---------------------------------------------------------------------------


@dataclass
class MetricsSnapshot:
    """A point-in-time snapshot of colony metrics.

    Attributes:
        timestamp: When the snapshot was taken.
        total_agents: Number of registered agents.
        active_agents: Agents currently executing tasks.
        idle_agents: Agents waiting for tasks.
        degraded_agents: Agents in degraded state.
        throughput_1m: Tasks completed in the last minute.
        avg_latency_ms: Average task latency in milliseconds.
        error_rate: Fraction of tasks that resulted in error.
        cpu_utilization: Estimated CPU utilization (0.0-1.0).
        memory_utilization: Estimated memory utilization (0.0-1.0).
        queue_depth: Current scheduler queue depth.
        messages_per_second: Inter-agent message rate.
    """

    timestamp: float = field(default_factory=_now)
    total_agents: int = 0
    active_agents: int = 0
    idle_agents: int = 0
    degraded_agents: int = 0
    throughput_1m: float = 0.0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    queue_depth: int = 0
    messages_per_second: float = 0.0

    @property
    def health_score(self) -> float:
        """Composite health score: 1.0 = fully healthy, 0.0 = dead."""
        if self.total_agents == 0:
            return 0.0
        factors = [
            1.0 - (self.degraded_agents / self.total_agents),
            1.0 - self.error_rate,
            1.0 - self.cpu_utilization * 0.5,
            1.0 - self.memory_utilization * 0.5,
        ]
        return max(0.0, min(1.0, sum(factors) / len(factors)))


@dataclass
class Alert:
    """An alert triggered by a monitored condition.

    Attributes:
        alert_id: Unique alert identifier.
        rule_name: Name of the alert rule.
        severity: Severity level.
        message: Human-readable description.
        metric_name: Which metric triggered the alert.
        metric_value: The value that crossed the threshold.
        threshold: The threshold that was crossed.
        fired_at: When the alert was triggered.
        acknowledged: Whether the alert has been acknowledged.
        resolved_at: When the condition was resolved, if applicable.
    """

    alert_id: str = field(default_factory=_new_id)
    rule_name: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    message: str = ""
    metric_name: str = ""
    metric_value: float = 0.0
    threshold: float = 0.0
    fired_at: float = field(default_factory=_now)
    acknowledged: bool = False
    resolved_at: float | None = None

    def resolve(self) -> None:
        self.resolved_at = _now()

    def acknowledge(self) -> None:
        self.acknowledged = True

    @property
    def is_active(self) -> bool:
        return self.resolved_at is None


@dataclass(frozen=True)
class AuditEntry:
    """An immutable audit log entry.

    Attributes:
        entry_id: Unique entry identifier.
        agent_id: Which agent performed the action.
        action: Description of the action.
        details: Additional context.
        timestamp: When the action occurred.
    """

    entry_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    action: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_now)


# ---------------------------------------------------------------------------
# Alert rule
# ---------------------------------------------------------------------------


@dataclass
class AlertRule:
    """Defines a condition that triggers an alert.

    Attributes:
        name: Unique rule name.
        metric: Which metric to monitor.
        threshold: The value that triggers the alert.
        comparator: 'gt' (greater than) or 'lt' (less than).
        severity: Severity of the resulting alert.
        cooldown_seconds: Minimum time between successive firings.
        message_template: Template for the alert message.
    """

    name: str
    metric: str
    threshold: float
    comparator: str = "gt"
    severity: AlertSeverity = AlertSeverity.WARNING
    cooldown_seconds: float = 60.0
    message_template: str = "{metric} is {value} (threshold: {threshold})"

    def __post_init__(self) -> None:
        if self.comparator not in ("gt", "lt"):
            raise MonitoringError("comparator must be 'gt' or 'lt'")


# ---------------------------------------------------------------------------
# Colony Monitor
# ---------------------------------------------------------------------------


class ColonyMonitor:
    """Observability layer for an agent colony.

    Tracks agent status, collects performance metrics, provides
    a resource utilization dashboard, fires alerts on anomalies,
    and maintains an immutable audit log.
    """

    def __init__(
        self,
        *,
        history_window: int = 3600,
        max_alerts: int = 1000,
        max_audit_entries: int = 10_000,
    ) -> None:
        self._history_window = history_window
        self._max_alerts = max_alerts
        self._max_audit_entries = max_audit_entries

        # Agent status tracking
        self._agent_status: dict[str, AgentStatus] = {}
        self._agent_last_heartbeat: dict[str, float] = {}
        self._agent_uptime: dict[str, float] = {}

        # Performance tracking
        self._latency_samples: list[float] = []
        self._throughput_samples: list[tuple[float, int]] = []  # (timestamp, count)
        self._error_counts: dict[str, int] = defaultdict(int)
        self._task_start_times: dict[str, float] = {}

        # Resource tracking
        self._cpu_samples: list[float] = []
        self._mem_samples: list[float] = []

        # Alerts
        self._alert_rules: dict[str, AlertRule] = {}
        self._alerts: list[Alert] = []
        self._last_fired: dict[str, float] = {}

        # Audit log
        self._audit_log: list[AuditEntry] = []

        # Message tracking
        self._message_times: list[float] = []

        # Background collection
        self._running = False
        self._collect_task: asyncio.Task[Any] | None = None

    # ------------------------------------------------------------------
    # Agent status
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str) -> None:
        """Register an agent for monitoring."""
        self._agent_status[agent_id] = AgentStatus.INITIALIZING
        self._agent_last_heartbeat[agent_id] = _now()

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from monitoring."""
        self._agent_status.pop(agent_id, None)
        self._agent_last_heartbeat.pop(agent_id, None)
        self._agent_uptime.pop(agent_id, None)

    def update_status(self, agent_id: str, status: AgentStatus) -> None:
        """Update an agent's operational status."""
        old = self._agent_status.get(agent_id)
        self._agent_status[agent_id] = status
        if old != status:
            logger.debug("Agent %s: %s -> %s", agent_id, old, status)
            self.log_audit(
                agent_id=agent_id,
                action="status_change",
                details={"from": old.name if old else "unknown", "to": status.name},
            )

    def heartbeat(self, agent_id: str) -> None:
        """Record an agent heartbeat."""
        self._agent_last_heartbeat[agent_id] = _now()

    def get_agent_status(self, agent_id: str) -> AgentStatus | None:
        return self._agent_status.get(agent_id)

    def get_unresponsive_agents(self, timeout_seconds: float = 30.0) -> list[str]:
        """Return agents that have not sent a heartbeat recently."""
        now = _now()
        return [
            aid
            for aid, last in self._agent_last_heartbeat.items()
            if now - last > timeout_seconds
        ]

    # ------------------------------------------------------------------
    # Performance metrics
    # ------------------------------------------------------------------

    def record_latency(self, latency_s: float) -> None:
        self._latency_samples.append(latency_s)
        if len(self._latency_samples) > self._history_window * 10:
            self._latency_samples = self._latency_samples[-self._history_window * 10:]

    def record_throughput(self, count: int) -> None:
        self._throughput_samples.append((_now(), count))
        # Prune old samples
        cutoff = _now() - self._history_window
        self._throughput_samples = [
            (t, c) for t, c in self._throughput_samples if t > cutoff
        ]

    def record_error(self, task_type: str) -> None:
        self._error_counts[task_type] += 1

    def record_task_start(self, task_id: str) -> None:
        self._task_start_times[task_id] = _now()

    def record_task_end(self, task_id: str) -> None:
        start = self._task_start_times.pop(task_id, None)
        if start is not None:
            self.record_latency(_now() - start)

    def record_message(self) -> None:
        self._message_times.append(_now())
        # Prune
        cutoff = _now() - 60
        self._message_times = [t for t in self._message_times if t > cutoff]

    # ------------------------------------------------------------------
    # Resource tracking
    # ------------------------------------------------------------------

    def record_cpu(self, utilization: float) -> None:
        self._cpu_samples.append(utilization)
        if len(self._cpu_samples) > 100:
            self._cpu_samples = self._cpu_samples[-100:]

    def record_memory(self, utilization: float) -> None:
        self._mem_samples.append(utilization)
        if len(self._mem_samples) > 100:
            self._mem_samples = self._mem_samples[-100:]

    # ------------------------------------------------------------------
    # Alert rules
    # ------------------------------------------------------------------

    def add_alert_rule(self, rule: AlertRule) -> None:
        self._alert_rules[rule.name] = rule

    def remove_alert_rule(self, name: str) -> bool:
        return self._alert_rules.pop(name, None) is not None

    def evaluate_alerts(self) -> list[Alert]:
        """Evaluate all alert rules against current metrics and fire any triggered alerts."""
        snapshot = self.snapshot()
        metric_map = {
            "error_rate": snapshot.error_rate,
            "cpu_utilization": snapshot.cpu_utilization,
            "memory_utilization": snapshot.memory_utilization,
            "avg_latency_ms": snapshot.avg_latency_ms,
            "queue_depth": float(snapshot.queue_depth),
            "degraded_agents": float(snapshot.degraded_agents),
        }

        new_alerts: list[Alert] = []
        now = _now()

        for rule in self._alert_rules.values():
            value = metric_map.get(rule.metric)
            if value is None:
                continue

            triggered = False
            if rule.comparator == "gt":
                triggered = value > rule.threshold
            elif rule.comparator == "lt":
                triggered = value < rule.threshold

            if not triggered:
                continue

            # Check cooldown
            last = self._last_fired.get(rule.name, 0.0)
            if now - last < rule.cooldown_seconds:
                continue

            self._last_fired[rule.name] = now
            alert = Alert(
                rule_name=rule.name,
                severity=rule.severity,
                message=rule.message_template.format(metric=rule.metric, value=value, threshold=rule.threshold),
                metric_name=rule.metric,
                metric_value=value,
                threshold=rule.threshold,
            )
            self._alerts.append(alert)
            new_alerts.append(alert)

            if rule.severity == AlertSeverity.CRITICAL:
                logger.error("CRITICAL alert: %s", alert.message)
            else:
                logger.warning("Alert: %s", alert.message)

        # Prune old alerts
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts:]

        return new_alerts

    def get_active_alerts(self) -> list[Alert]:
        return [a for a in self._alerts if a.is_active]

    def acknowledge_alert(self, alert_id: str) -> bool:
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledge()
                return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.resolve()
                return True
        return False

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------

    def log_audit(
        self,
        action: str,
        *,
        agent_id: str = "system",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append an entry to the immutable audit log."""
        entry = AuditEntry(
            agent_id=agent_id,
            action=action,
            details=details or {},
        )
        self._audit_log.append(entry)
        if len(self._audit_log) > self._max_audit_entries:
            self._audit_log = self._audit_log[-self._max_audit_entries:]

    def get_audit_log(
        self,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query the audit log, optionally filtered by agent."""
        entries = self._audit_log
        if agent_id is not None:
            entries = [e for e in entries if e.agent_id == agent_id]
        return entries[-limit:]

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> MetricsSnapshot:
        """Build a current MetricsSnapshot of the colony."""
        # Agent counts
        total = len(self._agent_status)
        active = sum(1 for s in self._agent_status.values() if s == AgentStatus.BUSY)
        idle = sum(1 for s in self._agent_status.values() if s == AgentStatus.IDLE)
        degraded = sum(1 for s in self._agent_status.values() if s == AgentStatus.DEGRADED)

        # Throughput (tasks in last 60 seconds)
        cutoff = _now() - 60
        recent = [c for t, c in self._throughput_samples if t > cutoff]
        throughput = sum(recent) if recent else 0.0

        # Latency
        avg_latency_ms = 0.0
        if self._latency_samples:
            avg_latency_ms = (sum(self._latency_samples) / len(self._latency_samples)) * 1000

        # Error rate
        total_completed = max(1, len(self._latency_samples))
        total_errors = sum(self._error_counts.values())
        error_rate = total_errors / total_completed if total_completed > 0 else 0.0

        # CPU / Mem
        cpu = sum(self._cpu_samples) / len(self._cpu_samples) if self._cpu_samples else 0.0
        mem = sum(self._mem_samples) / len(self._mem_samples) if self._mem_samples else 0.0

        # Messages per second
        now = _now()
        recent_msgs = sum(1 for t in self._message_times if now - t < 1.0)
        msg_rate = float(recent_msgs)

        return MetricsSnapshot(
            total_agents=total,
            active_agents=active,
            idle_agents=idle,
            degraded_agents=degraded,
            throughput_1m=throughput,
            avg_latency_ms=avg_latency_ms,
            error_rate=error_rate,
            cpu_utilization=cpu,
            memory_utilization=mem,
            messages_per_second=msg_rate,
        )

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def dashboard(self) -> dict[str, Any]:
        """Return a human-readable dashboard summary."""
        s = self.snapshot()
        return {
            "health": {
                "score": s.health_score,
                "total_agents": s.total_agents,
                "active": s.active_agents,
                "idle": s.idle_agents,
                "degraded": s.degraded_agents,
            },
            "performance": {
                "throughput_1m": s.throughput_1m,
                "avg_latency_ms": s.avg_latency_ms,
                "error_rate": s.error_rate,
                "messages_per_second": s.messages_per_second,
            },
            "resources": {
                "cpu": s.cpu_utilization,
                "memory": s.memory_utilization,
            },
            "alerts": len(self.get_active_alerts()),
            "audit_entries": len(self._audit_log),
        }

    # ------------------------------------------------------------------
    # Background collection
    # ------------------------------------------------------------------

    async def start_collection(self, interval: float = 1.0) -> None:
        """Start periodic metric collection and alert evaluation."""
        self._running = True
        self._collect_task = asyncio.create_task(self._collect_loop(interval))

    async def stop_collection(self) -> None:
        """Stop periodic collection."""
        self._running = False
        if self._collect_task:
            self._collect_task.cancel()
            try:
                await self._collect_task
            except asyncio.CancelledError:
                pass

    async def _collect_loop(self, interval: float) -> None:
        while self._running:
            try:
                self.evaluate_alerts()
                await asyncio.sleep(interval)
            except Exception:
                logger.exception("Error in monitor collection loop")
                await asyncio.sleep(interval)
