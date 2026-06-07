"""Alert management for drift detection.

Provides severity levels, deduplication, throttling, escalation policies,
and alert history/analytics.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Protocol

from .drift_detector import DriftSeverity, DriftSignal, DriftType

logger = logging.getLogger(__name__)


# ── Enums and data classes ──────────────────────────────────────────────


class AlertSeverity(Enum):
    """Alert severity levels with numeric priority (lower = more urgent)."""

    INFO = 30
    WARN = 20
    CRITICAL = 10


class AlertState(Enum):
    """Lifecycle state of an alert."""

    FIRED = auto()
    ACKNOWLEDGED = auto()
    RESOLVED = auto()
    ESCALATED = auto()
    SUPPRESSED = auto()


class EscalationLevel(Enum):
    """Escalation tiers for alerts."""

    NONE = auto()
    TEAM_LEAD = auto()
    ONCALL = auto()
    INCIDENT = auto()


@dataclass
class AlertRule:
    """Defines when and how an alert should be generated.

    Attributes:
        rule_id: Unique rule identifier.
        name: Human-readable rule name.
        drift_type: Which drift type triggers this rule.
        min_severity: Minimum drift severity to trigger.
        cooldown_seconds: Minimum time between repeated alerts.
        max_alerts_per_hour: Throttle limit.
        escalation: Escalation level.
        notification_channels: Where to send alerts.
        enabled: Whether this rule is active.
    """

    rule_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    drift_type: DriftType | None = None
    min_severity: DriftSeverity = DriftSeverity.LOW
    cooldown_seconds: float = 300.0  # 5 minutes
    max_alerts_per_hour: int = 12
    escalation: EscalationLevel = EscalationLevel.NONE
    notification_channels: list[str] = field(default_factory=lambda: ["log"])
    enabled: bool = True


@dataclass
class Alert:
    """A triggered alert.

    Attributes:
        alert_id: Unique alert identifier.
        rule_id: The rule that triggered this alert.
        signal: The drift signal that caused the alert.
        severity: Alert severity level.
        state: Current alert state.
        created_at: When the alert was created.
        acknowledged_at: When acknowledged (if ever).
        resolved_at: When resolved (if ever).
        message: Human-readable alert message.
        metadata: Additional context.
    """

    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    rule_id: str = ""
    signal: DriftSignal | None = None
    severity: AlertSeverity = AlertSeverity.INFO
    state: AlertState = AlertState.FIRED
    created_at: float = field(default_factory=time.time)
    acknowledged_at: float | None = None
    resolved_at: float | None = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertThrottleState:
    """Tracks throttling state for a rule."""

    last_fired: float = 0.0
    fire_count: int = 0
    window_start: float = field(default_factory=time.time)


# ── Notification handler protocol ──────────────────────────────────────


class NotificationHandler(Protocol):
    """Protocol for alert notification handlers."""

    async def send(self, alert: Alert) -> bool: ...


# ── Alert Manager ──────────────────────────────────────────────────────


class AlertManager:
    """Manages alert lifecycle: generation, deduplication, throttling, escalation.

    Coordinates with drift signals to produce actionable alerts with appropriate
    severity levels and notification routing.
    """

    def __init__(
        self,
        max_history: int = 10000,
        default_cooldown: float = 300.0,
    ) -> None:
        self.max_history = max_history
        self.default_cooldown = default_cooldown

        self._rules: dict[str, AlertRule] = {}
        self._alerts: deque[Alert] = deque(maxlen=max_history)
        self._throttle_states: dict[str, AlertThrottleState] = defaultdict(AlertThrottleState)
        self._handlers: dict[str, NotificationHandler] = {}
        self._signal_signatures: deque[str] = deque(maxlen=1000)  # For dedup

    # ── Rule management ────────────────────────────────────────────────

    def add_rule(self, rule: AlertRule) -> None:
        """Register an alert rule."""
        self._rules[rule.rule_id] = rule
        logger.info("Alert rule '%s' (%s) registered", rule.name, rule.rule_id)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule by ID."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> AlertRule | None:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def list_rules(self, enabled_only: bool = True) -> list[AlertRule]:
        """List all rules, optionally filtered to enabled ones."""
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules

    # ── Notification handlers ──────────────────────────────────────────

    def register_handler(self, channel: str, handler: NotificationHandler) -> None:
        """Register a notification handler for a channel name."""
        self._handlers[channel] = handler

    def unregister_handler(self, channel: str) -> None:
        """Remove a notification handler."""
        self._handlers.pop(channel, None)

    # ── Signal processing ──────────────────────────────────────────────

    def _compute_signal_signature(self, signal: DriftSignal) -> str:
        """Compute a deduplication signature for a drift signal.

        Two signals with the same type, metric, and similar score (rounded)
        within a short window are considered duplicates.
        """
        key = f"{signal.drift_type.name}:{signal.metric}:{signal.score:.3f}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def _should_throttle(self, rule: AlertRule) -> bool:
        """Check if an alert should be throttled for a given rule."""
        state = self._throttle_states[rule.rule_id]
        now = time.time()

        # Reset hourly counter if window has passed
        if now - state.window_start > 3600.0:
            state.window_start = now
            state.fire_count = 0

        # Check cooldown
        if now - state.last_fired < rule.cooldown_seconds:
            return True

        # Check rate limit
        if state.fire_count >= rule.max_alerts_per_hour:
            return True

        return False

    def _record_fire(self, rule: AlertRule) -> None:
        """Record that an alert was fired for throttling tracking."""
        state = self._throttle_states[rule.rule_id]
        state.last_fired = time.time()
        state.fire_count += 1

    def _map_severity(self, drift_severity: DriftSeverity) -> AlertSeverity:
        """Map drift severity to alert severity."""
        mapping = {
            DriftSeverity.NONE: AlertSeverity.INFO,
            DriftSeverity.LOW: AlertSeverity.INFO,
            DriftSeverity.MEDIUM: AlertSeverity.WARN,
            DriftSeverity.HIGH: AlertSeverity.WARN,
            DriftSeverity.CRITICAL: AlertSeverity.CRITICAL,
        }
        return mapping.get(drift_severity, AlertSeverity.INFO)

    async def process_signal(self, signal: DriftSignal) -> Alert | None:
        """Process a drift signal and potentially create an alert.

        Handles deduplication, throttling, and routing to appropriate rules.

        Args:
            signal: The drift signal to process.

        Returns:
            An Alert if one was created, None if suppressed or no matching rule.
        """
        if not signal.is_drift:
            return None

        # Deduplication
        sig = self._compute_signal_signature(signal)
        if sig in self._signal_signatures:
            logger.debug("Duplicate signal suppressed: %s", sig)
            return None
        self._signal_signatures.append(sig)

        # Find matching rules
        matching_rules = [
            r for r in self._rules.values()
            if r.enabled
            and (r.drift_type is None or r.drift_type == signal.drift_type)
            and signal.severity.value >= r.min_severity.value
        ]

        if not matching_rules:
            logger.debug("No matching rules for signal: type=%s metric=%s",
                        signal.drift_type.name, signal.metric)
            return None

        # Use the most specific (matched drift_type) rule, or first
        specific_rules = [r for r in matching_rules if r.drift_type == signal.drift_type]
        rule = specific_rules[0] if specific_rules else matching_rules[0]

        # Throttle check
        if self._should_throttle(rule):
            logger.debug("Alert throttled for rule '%s'", rule.name)
            return None

        # Create alert
        self._record_fire(rule)
        alert = Alert(
            rule_id=rule.rule_id,
            signal=signal,
            severity=self._map_severity(signal.severity),
            message=self._format_message(rule, signal),
            metadata={
                "drift_type": signal.drift_type.name,
                "metric": signal.metric,
                "score": signal.score,
                "threshold": signal.threshold,
                "drift_severity": signal.severity.name,
            },
        )
        self._alerts.append(alert)

        # Send notifications
        await self._notify(alert, rule.notification_channels)

        logger.info(
            "Alert fired: %s [%s] rule=%s metric=%s score=%.3f",
            alert.alert_id[:8], alert.severity.name,
            rule.name, signal.metric, signal.score,
        )

        return alert

    async def process_signals(self, signals: list[DriftSignal]) -> list[Alert]:
        """Process multiple drift signals concurrently.

        Args:
            signals: List of drift signals to process.

        Returns:
            List of created alerts (excluding suppressed/throttled).
        """
        tasks = [self.process_signal(s) for s in signals]
        results = await asyncio.gather(*tasks)
        return [a for a in results if a is not None]

    def _format_message(self, rule: AlertRule, signal: DriftSignal) -> str:
        """Format a human-readable alert message."""
        return (
            f"[{rule.name}] {signal.drift_type.name} drift detected on "
            f"'{signal.metric}': score={signal.score:.4f} (threshold={signal.threshold}) "
            f"severity={signal.severity.name}"
        )

    async def _notify(self, alert: Alert, channels: list[str]) -> None:
        """Send alert to all configured notification channels."""
        for channel in channels:
            handler = self._handlers.get(channel)
            if handler:
                try:
                    success = await handler.send(alert)
                    if not success:
                        logger.warning("Notification to '%s' failed for alert %s",
                                     channel, alert.alert_id[:8])
                except Exception as exc:
                    logger.error("Notification handler '%s' error: %s", channel, exc)

    # ── Alert lifecycle ────────────────────────────────────────────────

    def acknowledge(self, alert_id: str) -> bool:
        """Acknowledge an alert.

        Args:
            alert_id: The alert to acknowledge.

        Returns:
            True if acknowledged, False if not found.
        """
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.state = AlertState.ACKNOWLEDGED
                alert.acknowledged_at = time.time()
                logger.info("Alert %s acknowledged", alert_id[:8])
                return True
        return False

    def resolve(self, alert_id: str) -> bool:
        """Resolve an alert.

        Args:
            alert_id: The alert to resolve.

        Returns:
            True if resolved, False if not found.
        """
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.state = AlertState.RESOLVED
                alert.resolved_at = time.time()
                logger.info("Alert %s resolved", alert_id[:8])
                return True
        return False

    def escalate(self, alert_id: str) -> bool:
        """Escalate an alert.

        Args:
            alert_id: The alert to escalate.

        Returns:
            True if escalated, False if not found.
        """
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.state = AlertState.ESCALATED
                logger.info("Alert %s escalated", alert_id[:8])
                return True
        return False

    # ── Querying ───────────────────────────────────────────────────────

    def get_active_alerts(self) -> list[Alert]:
        """Get all alerts that are not resolved."""
        return [a for a in self._alerts if a.state != AlertState.RESOLVED]

    def get_alerts_by_severity(self, severity: AlertSeverity) -> list[Alert]:
        """Get all alerts of a specific severity."""
        return [a for a in self._alerts if a.severity == severity]

    def get_alerts_by_type(self, drift_type: DriftType) -> list[Alert]:
        """Get all alerts for a specific drift type."""
        return [
            a for a in self._alerts
            if a.signal and a.signal.drift_type == drift_type
        ]

    def get_alerts_since(self, timestamp: float) -> list[Alert]:
        """Get all alerts created after a given timestamp."""
        return [a for a in self._alerts if a.created_at > timestamp]

    def get_alert_count(self, state: AlertState | None = None) -> int:
        """Get count of alerts, optionally filtered by state."""
        if state is None:
            return len(self._alerts)
        return sum(1 for a in self._alerts if a.state == state)

    # ── Analytics ──────────────────────────────────────────────────────

    @property
    def alert_stats(self) -> dict[str, Any]:
        """Get alert statistics for analytics."""
        now = time.time()
        last_hour = now - 3600
        last_day = now - 86400

        all_alerts = list(self._alerts)
        recent_hour = [a for a in all_alerts if a.created_at > last_hour]
        recent_day = [a for a in all_alerts if a.created_at > last_day]

        # Per-type breakdown
        by_type: dict[str, int] = {}
        for a in all_alerts:
            if a.signal:
                dt = a.signal.drift_type.name
                by_type[dt] = by_type.get(dt, 0) + 1

        # Per-severity breakdown
        by_severity: dict[str, int] = {}
        for a in all_alerts:
            sev = a.severity.name
            by_severity[sev] = by_severity.get(sev, 0) + 1

        # Resolution time stats (for resolved alerts)
        resolved = [a for a in all_alerts if a.resolved_at is not None]
        resolution_times = [
            (a.resolved_at - a.created_at) for a in resolved  # type: ignore[operator]
        ]

        return {
            "total_alerts": len(all_alerts),
            "last_hour": len(recent_hour),
            "last_day": len(recent_day),
            "by_type": by_type,
            "by_severity": by_severity,
            "active_count": self.get_alert_count(None) - len(resolved),
            "resolved_count": len(resolved),
            "avg_resolution_time_seconds": (
                sum(resolution_times) / len(resolution_times) if resolution_times else 0.0
            ),
            "rules_count": len(self._rules),
        }

    @property
    def escalatable_alerts(self) -> list[Alert]:
        """Get alerts that should be considered for escalation.

        Criteria: CRITICAL severity, FIRED state, older than 5 minutes.
        """
        now = time.time()
        return [
            a for a in self._alerts
            if a.severity == AlertSeverity.CRITICAL
            and a.state == AlertState.FIRED
            and (now - a.created_at) > 300.0
        ]

    # ── Cleanup ────────────────────────────────────────────────────────

    def prune_old_alerts(self, max_age_seconds: float = 86400 * 7) -> int:
        """Remove alerts older than the specified age.

        Args:
            max_age_seconds: Maximum age in seconds (default: 7 days).

        Returns:
            Number of alerts pruned.
        """
        cutoff = time.time() - max_age_seconds
        before_count = len(self._alerts)
        # Filter resolved alerts only for pruning
        kept = deque(
            [a for a in self._alerts if a.created_at > cutoff or a.state != AlertState.RESOLVED],
            maxlen=self.max_history,
        )
        self._alerts = kept
        pruned = before_count - len(self._alerts)
        if pruned > 0:
            logger.info("Pruned %d old alerts", pruned)
        return pruned


# ── Built-in notification handlers ─────────────────────────────────────


class LogNotificationHandler:
    """Simple notification handler that logs alerts."""

    async def send(self, alert: Alert) -> bool:
        logger.warning(
            "ALERT [%s] %s: %s",
            alert.severity.name,
            alert.alert_id[:8],
            alert.message,
        )
        return True


class CallbackNotificationHandler:
    """Notification handler that invokes a user-provided callback."""

    def __init__(self, callback: Callable[[Alert], Any]) -> None:
        self.callback = callback

    async def send(self, alert: Alert) -> bool:
        try:
            result = self.callback(alert)
            if asyncio.iscoroutine(result):
                await result
            return True
        except Exception as exc:
            logger.error("Callback notification failed: %s", exc)
            return False


# ── Escalation policy ──────────────────────────────────────────────────


class EscalationPolicy:
    """Manages escalation rules for alerts.

    Defines when alerts should be escalated and to whom, with support for
    time-based and severity-based automation.
    """

    def __init__(self, alert_manager: AlertManager) -> None:
        self._manager = alert_manager
        self._escalation_delays: dict[AlertSeverity, float] = {
            AlertSeverity.CRITICAL: 300.0,   # 5 minutes
            AlertSeverity.WARN: 1800.0,       # 30 minutes
            AlertSeverity.INFO: 3600.0,       # 1 hour
        }
        self._escalation_chains: dict[EscalationLevel, list[str]] = {
            EscalationLevel.TEAM_LEAD: ["slack", "email"],
            EscalationLevel.ONCALL: ["pagerduty", "slack"],
            EscalationLevel.INCIDENT: ["pagerduty", "email", "slack"],
        }

    def set_delay(self, severity: AlertSeverity, delay_seconds: float) -> None:
        """Set the escalation delay for a severity level."""
        self._escalation_delays[severity] = delay_seconds

    def set_channels(self, level: EscalationLevel, channels: list[str]) -> None:
        """Set the notification channels for an escalation level."""
        self._escalation_chains[level] = channels

    async def check_and_escalate(self) -> list[Alert]:
        """Check for alerts that need escalation and escalate them.

        Returns:
            List of alerts that were escalated.
        """
        now = time.time()
        escalated: list[Alert] = []

        for alert in self._manager.get_active_alerts():
            if alert.state == AlertState.ESCALATED:
                continue

            delay = self._escalation_delays.get(alert.severity, 3600.0)
            if (now - alert.created_at) >= delay:
                self._manager.escalate(alert.alert_id)
                escalated.append(alert)

        return escalated
