"""SLA Tracker — service level agreement monitoring and compliance tracking.

Provides SLA definition, measurement recording, compliance checking,
violation detection, and compliance reporting for Lyra infrastructure.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class SLADefinition:
    name: str
    target: float  # target percentage (e.g., 99.9 for 99.9%)
    window_hours: float
    metric_name: str
    description: str = ""


@dataclass(frozen=True)
class SLAMeasurement:
    sla_name: str
    value: float
    target: float
    timestamp: float = field(default_factory=time.monotonic)

    @property
    def is_compliant(self) -> bool:
        return self.value >= self.target


@dataclass(frozen=True)
class SLAViolation:
    sla_name: str
    current_value: float
    target: float
    severity: Severity
    timestamp: float = field(default_factory=time.monotonic)
    message: str = ""


@dataclass(frozen=True)
class SLAComplianceReport:
    overall_compliance: float
    total_slas: int
    slas_in_violation: int
    generated_at: float = field(default_factory=time.monotonic)

    @property
    def is_overall_compliant(self) -> bool:
        return self.slas_in_violation == 0


class SLATracker:
    """Tracks SLA definitions and measurements for compliance monitoring.

    Registers SLA definitions, records periodic measurements, checks
    compliance against targets, detects violations with severity levels,
    and generates compliance reports.

    Usage::

        tracker = SLATracker()
        tracker.register_sla(SLADefinition(
            name="api-availability",
            target=99.9,
            window_hours=24.0,
            metric_name="uptime_pct",
        ))
        tracker.record_measurement("api-availability", value=99.95)
        report = tracker.check_compliance()
        if not report.is_overall_compliant:
            for v in tracker.get_active_violations():
                print(f"VIOLATION: {v.sla_name} at {v.current_value}%")
    """

    _SEVERITY_THRESHOLDS = [
        (1.0, Severity.CRITICAL),   # >1% below target
        (2.0, Severity.HIGH),       # >2% below target
        (5.0, Severity.MEDIUM),     # >5% below target
        (float("inf"), Severity.LOW),
    ]

    def __init__(self) -> None:
        self._slas: dict[str, SLADefinition] = {}
        self._measurements: dict[str, list[SLAMeasurement]] = defaultdict(list)
        self._violations: dict[str, list[SLAViolation]] = defaultdict(list)

    @property
    def sla_count(self) -> int:
        return len(self._slas)

    def register_sla(self, sla: SLADefinition) -> None:
        if sla.name in self._slas:
            raise ValueError(f"SLA '{sla.name}' already registered")
        self._slas[sla.name] = sla

    def get_sla(self, name: str) -> SLADefinition | None:
        return self._slas.get(name)

    def unregister_sla(self, name: str) -> None:
        self._slas.pop(name, None)

    def record_measurement(self, sla_name: str, value: float) -> SLAMeasurement:
        sla = self._slas.get(sla_name)
        if sla is None:
            raise ValueError(f"SLA '{sla_name}' not registered")
        m = SLAMeasurement(sla_name=sla_name, value=value, target=sla.target)
        self._measurements[sla_name].append(m)
        if not m.is_compliant:
            severity = self._calculate_severity(sla.target, value)
            self._violations[sla_name].append(SLAViolation(
                sla_name=sla_name,
                current_value=value,
                target=sla.target,
                severity=severity,
                message=f"{sla_name}: {value}% (target: {sla.target}%)",
            ))
        return m

    def get_latest_measurement(self, sla_name: str) -> SLAMeasurement | None:
        measurements = self._measurements.get(sla_name, [])
        return measurements[-1] if measurements else None

    def get_measurements(self, sla_name: str) -> list[SLAMeasurement]:
        return list(self._measurements.get(sla_name, []))

    def check_compliance(self) -> SLAComplianceReport:
        violations = 0
        for name in self._slas:
            latest = self.get_latest_measurement(name)
            if latest is not None and not latest.is_compliant:
                violations += 1
        total = len(self._slas)
        overall = ((total - violations) / max(total, 1)) * 100.0
        return SLAComplianceReport(
            overall_compliance=overall,
            total_slas=total,
            slas_in_violation=violations,
        )

    def get_active_violations(self) -> list[SLAViolation]:
        active: list[SLAViolation] = []
        for name, sla in self._slas.items():
            latest = self.get_latest_measurement(name)
            if latest is not None and not latest.is_compliant:
                severity = self._calculate_severity(sla.target, latest.value)
                active.append(SLAViolation(
                    sla_name=name,
                    current_value=latest.value,
                    target=sla.target,
                    severity=severity,
                    message=f"{name}: {latest.value}% (target: {sla.target}%)",
                ))
        return active

    def get_compliance_report(self) -> SLAComplianceReport:
        violations = len(self.get_active_violations())
        total = len(self._slas)
        overall = ((total - violations) / max(total, 1)) * 100.0
        return SLAComplianceReport(
            overall_compliance=overall,
            total_slas=total,
            slas_in_violation=violations,
        )

    def get_violation_history(self, sla_name: str) -> list[SLAViolation]:
        return list(self._violations.get(sla_name, []))

    def reset(self) -> None:
        self._slas.clear()
        self._measurements.clear()
        self._violations.clear()

    @staticmethod
    def _calculate_severity(target: float, value: float) -> Severity:
        delta = target - value
        for threshold, severity in SLATracker._SEVERITY_THRESHOLDS:
            if delta <= threshold:
                return severity
        return Severity.LOW
