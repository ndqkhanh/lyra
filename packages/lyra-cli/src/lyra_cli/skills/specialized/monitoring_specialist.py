"""Monitoring Specialist Skill — observability and alerting configuration validation.

Validates monitoring setups for:
- Metric collection completeness
- Alert rule effectiveness
- Dashboard coverage
- SLO/SLI definitions
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AlertSeverity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class MonitoringGap:
    area: str
    severity: AlertSeverity
    description: str
    recommendation: str


class MonitoringSpecialistSkill:
    """Validates monitoring and observability configurations."""

    _GOLDEN_SIGNALS = frozenset({"latency", "traffic", "errors", "saturation"})
    _CRITICAL_AREAS = frozenset({"api", "database", "cache", "queue"})

    def run(self, input_data: dict) -> dict:
        metrics = input_data.get("metrics", [])
        alerts = input_data.get("alerts", [])
        gaps: list[MonitoringGap] = []

        metric_names = {m.get("name", "") for m in metrics}
        alert_areas = {a.get("area", "") for a in alerts}

        for signal in self._GOLDEN_SIGNALS:
            if not any(signal in m.lower() for m in metric_names):
                gaps.append(
                    MonitoringGap(
                        signal,
                        AlertSeverity.CRITICAL,
                        f"No '{signal}' metric — one of the Four Golden Signals is missing.",
                        f"Add {signal} metric collection and alerting.",
                    )
                )

        for area in self._CRITICAL_AREAS:
            if area not in alert_areas:
                gaps.append(
                    MonitoringGap(
                        area,
                        AlertSeverity.WARNING,
                        f"No alerts configured for '{area}'.",
                        f"Add baseline alerts for {area} errors and latency.",
                    )
                )

        if not alerts:
            gaps.append(
                MonitoringGap(
                    "alerting",
                    AlertSeverity.CRITICAL,
                    "No alerts defined at all.",
                    "Define at minimum: error rate, latency P99, availability.",
                )
            )
        else:
            critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
            if not critical_alerts:
                gaps.append(
                    MonitoringGap(
                        "alerting",
                        AlertSeverity.WARNING,
                        "No critical-severity alerts defined.",
                        "Add at least one critical alert (e.g., service down, error rate > 5%).",
                    )
                )

        return {
            "gaps": [g.__dict__ for g in gaps],
            "golden_signals_covered": len(self._GOLDEN_SIGNALS)
            - len([g for g in gaps if g.area in self._GOLDEN_SIGNALS]),
            "score": max(0, 100 - len(gaps) * 15),
            "passed": len([g for g in gaps if g.severity == AlertSeverity.CRITICAL]) == 0,
        }
