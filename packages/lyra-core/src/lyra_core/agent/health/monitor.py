"""Agent health monitor — sliding-window signal collection and trend detection."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from lyra_core.agent.health.signals import HealthSignal, SignalSeverity, SignalSource


class HealthTrend(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


@dataclass(frozen=True)
class MonitorConfig:
    window_seconds: float = 300.0
    max_signals_per_source: int = 1000
    degrade_threshold: float = 0.3
    critical_threshold: float = 0.6
    trend_window_count: int = 3
    min_signals_for_trend: int = 5


@dataclass(frozen=True)
class HealthStatus:
    overall: str
    per_source: tuple[tuple[str, str, float, HealthTrend], ...]
    anomaly_count: int
    active_playbook: str
    last_updated: float = field(default_factory=time.time)


class AgentHealthMonitor:
    """Collects health signals over sliding windows and detects trends.

    Usage::

        monitor = AgentHealthMonitor()
        monitor.ingest(HealthSignal(
            source=SignalSource.ERROR_RATE,
            severity=SignalSeverity.WARN,
            value=0.25,
        ))
        status = monitor.snapshot()
    """

    def __init__(self, config: MonitorConfig | None = None) -> None:
        self.config = config or MonitorConfig()
        self._signals: dict[str, list[HealthSignal]] = {}
        self._anomalies: list[object] = []
        self._active_playbook: str = ""
        self._last_updated: float = 0.0

    def ingest(self, signal: HealthSignal) -> None:
        key = signal.source.value
        self._signals.setdefault(key, []).append(signal)
        self._last_updated = signal.timestamp
        self._prune(key)

    def _prune(self, source_key: str) -> None:
        signals = self._signals.get(source_key)
        if signals is None:
            return
        cutoff = time.time() - self.config.window_seconds
        self._signals[source_key] = [s for s in signals if s.timestamp >= cutoff]
        if len(self._signals[source_key]) > self.config.max_signals_per_source:
            self._signals[source_key] = self._signals[source_key][
                -self.config.max_signals_per_source :
            ]

    def get_signals(
        self,
        source: SignalSource | None = None,
    ) -> list[HealthSignal]:
        if source is not None:
            return list(self._signals.get(source.value, []))
        all_signals: list[HealthSignal] = []
        for sigs in self._signals.values():
            all_signals.extend(sigs)
        return sorted(all_signals, key=lambda s: s.timestamp)

    def get_source_summary(
        self,
        source: SignalSource,
    ) -> dict[str, object]:
        signals = self._signals.get(source.value, [])
        if not signals:
            return {"source": source.value, "count": 0, "latest_value": 0.0, "mean_value": 0.0, "trend": HealthTrend.STABLE.value}
        values = [s.value for s in signals]
        severities = [s.severity for s in signals]
        latest_sev = severities[-1] if severities else SignalSeverity.OK
        return {
            "source": source.value,
            "count": len(signals),
            "latest_value": values[-1],
            "mean_value": sum(values) / len(values),
            "trend": self._compute_trend(values).value,
            "latest_severity": latest_sev.value,
        }

    def snapshot(self) -> HealthStatus:
        per_source: list[tuple[str, str, float, HealthTrend]] = []
        worst_severity = SignalSeverity.OK

        for src in SignalSource:
            sigs = self._signals.get(src.value, [])
            if not sigs:
                continue
            values = [s.value for s in sigs]
            avg = sum(values) / len(values)
            trend = self._compute_trend(values)
            latest_sev = sigs[-1].severity if sigs else SignalSeverity.OK

            per_source.append((src.value, latest_sev.value, round(avg, 4), trend))

            if self._severity_rank(latest_sev) > self._severity_rank(worst_severity):
                worst_severity = latest_sev

        return HealthStatus(
            overall=worst_severity.value,
            per_source=tuple(per_source),
            anomaly_count=len(self._anomalies),
            active_playbook=self._active_playbook,
            last_updated=self._last_updated,
        )

    def _compute_trend(self, values: list[float]) -> HealthTrend:
        if len(values) < self.config.min_signals_for_trend:
            return HealthTrend.STABLE
        n = self.config.trend_window_count
        if len(values) < n * 2:
            return HealthTrend.STABLE
        recent = values[-n:]
        prior = values[-(n * 2) : -n]
        if not prior:
            return HealthTrend.STABLE
        recent_avg = sum(recent) / len(recent)
        prior_avg = sum(prior) / len(prior)
        if prior_avg == 0:
            return HealthTrend.STABLE
        change = (recent_avg - prior_avg) / prior_avg
        if change > self.config.degrade_threshold:
            return HealthTrend.DECLINING
        if change < -self.config.degrade_threshold:
            return HealthTrend.IMPROVING
        return HealthTrend.STABLE

    def _compute_overall(self, worst: SignalSeverity) -> str:
        degrade = self.config.degrade_threshold
        critical = self.config.critical_threshold
        for src in SignalSource:
            sigs = self._signals.get(src.value, [])
            if not sigs:
                continue
            recent = sigs[-self.config.trend_window_count :]
            warn_count = sum(1 for s in recent if s.severity in (SignalSeverity.WARN, SignalSeverity.DEGRADED, SignalSeverity.CRITICAL))
            ratio = warn_count / len(recent) if recent else 0
            if ratio >= critical:
                return "critical"
            if ratio >= degrade:
                return "degraded"
        return worst.value

    def register_anomaly(self, anomaly: object) -> None:
        self._anomalies.append(anomaly)

    def set_active_playbook(self, playbook_id: str) -> None:
        self._active_playbook = playbook_id

    @staticmethod
    def _severity_rank(sev: SignalSeverity) -> int:
        return {SignalSeverity.OK: 0, SignalSeverity.WARN: 1, SignalSeverity.DEGRADED: 2, SignalSeverity.CRITICAL: 3}[sev]

    @property
    def signal_count(self) -> int:
        return sum(len(v) for v in self._signals.values())

    @property
    def active_playbook(self) -> str:
        return self._active_playbook

    def clear(self) -> None:
        self._signals.clear()
        self._anomalies.clear()
        self._active_playbook = ""
        self._last_updated = 0.0
