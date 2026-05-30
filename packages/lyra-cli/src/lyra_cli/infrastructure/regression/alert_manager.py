"""Alert manager for regression detection — dispatches alerts on regressions."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum


class AlertChannel(StrEnum):
    LOG = "log"
    CONSOLE = "console"
    WEBHOOK = "webhook"
    CALLBACK = "callback"


class AlertSeverity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Alert:
    alert_id: str
    message: str
    severity: AlertSeverity
    metric_name: str
    current_value: float
    baseline_value: float
    deviation_pct: float
    timestamp: float
    acknowledged: bool = False


@dataclass
class AlertRule:
    metric_pattern: str
    threshold_pct: float
    severity: AlertSeverity
    cooldown_seconds: float = 300.0
    enabled: bool = True
    _last_fired: dict[str, float] = field(default_factory=dict)


class AlertManager:
    """Manages regression alerts with rules, deduplication, and dispatch.

    Usage::

        mgr = AlertManager()
        mgr.add_rule("latency_*", threshold_pct=10.0, severity=AlertSeverity.WARNING)
        mgr.on_callback = lambda alert: print(f"ALERT: {alert.message}")
        alerts = mgr.check_metric("latency_p95", current=450.0, baseline=200.0)
    """

    def __init__(self, dedup_window_seconds: float = 300.0) -> None:
        self._rules: list[AlertRule] = []
        self._alerts: deque[Alert] = deque(maxlen=1000)
        self._alert_counter: int = 0
        self._dedup_window = dedup_window_seconds
        self._recent_keys: dict[str, float] = {}
        self.on_callback: Callable[[Alert], None] | None = None

    @property
    def alert_count(self) -> int:
        return len(self._alerts)

    @property
    def recent_alerts(self) -> list[Alert]:
        return list(self._alerts)

    def add_rule(
        self,
        metric_pattern: str,
        threshold_pct: float,
        severity: AlertSeverity = AlertSeverity.WARNING,
        cooldown_seconds: float = 300.0,
    ) -> AlertRule:
        rule = AlertRule(
            metric_pattern=metric_pattern,
            threshold_pct=threshold_pct,
            severity=severity,
            cooldown_seconds=cooldown_seconds,
        )
        self._rules.append(rule)
        return rule

    def check_metric(
        self,
        metric_name: str,
        current_value: float,
        baseline_value: float,
    ) -> Alert | None:
        if baseline_value == 0.0:
            return None

        deviation = abs((current_value - baseline_value) / baseline_value) * 100.0

        for rule in self._rules:
            if not rule.enabled:
                continue
            if not self._match_pattern(metric_name, rule.metric_pattern):
                continue
            if deviation < rule.threshold_pct:
                continue

            dedup_key = f"{metric_name}:{rule.severity}"
            last_fired = rule._last_fired.get(dedup_key, 0.0)
            now = time.time()
            if now - last_fired < rule.cooldown_seconds:
                continue

            rule._last_fired[dedup_key] = now
            self._alert_counter += 1
            alert = Alert(
                alert_id=f"alert-{self._alert_counter:06d}",
                message=f"{rule.severity.upper()}: {metric_name} deviated {deviation:.1f}% "
                f"(current={current_value:.2f}, baseline={baseline_value:.2f})",
                severity=rule.severity,
                metric_name=metric_name,
                current_value=current_value,
                baseline_value=baseline_value,
                deviation_pct=round(deviation, 2),
                timestamp=now,
            )
            self._alerts.append(alert)
            self._dispatch(alert)
            return alert

        return None

    def acknowledge(self, alert_id: str) -> bool:
        for i, alert in enumerate(self._alerts):
            if alert.alert_id == alert_id:
                self._alerts[i] = Alert(
                    alert_id=alert.alert_id,
                    message=alert.message,
                    severity=alert.severity,
                    metric_name=alert.metric_name,
                    current_value=alert.current_value,
                    baseline_value=alert.baseline_value,
                    deviation_pct=alert.deviation_pct,
                    timestamp=alert.timestamp,
                    acknowledged=True,
                )
                return True
        return False

    def get_alerts_by_severity(self, severity: AlertSeverity) -> list[Alert]:
        return [a for a in self._alerts if a.severity == severity]

    def get_alerts_by_metric(self, metric_name: str) -> list[Alert]:
        return [a for a in self._alerts if a.metric_name == metric_name]

    def clear(self) -> None:
        self._alerts.clear()
        self._alert_counter = 0

    def _dispatch(self, alert: Alert) -> None:
        if self.on_callback:
            try:
                self.on_callback(alert)
            except Exception:
                pass

    @staticmethod
    def _match_pattern(name: str, pattern: str) -> bool:
        import fnmatch

        return fnmatch.fnmatch(name, pattern)
