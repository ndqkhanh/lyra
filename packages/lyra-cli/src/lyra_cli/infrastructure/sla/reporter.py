"""SLA Reporter — compliance report generation for SLA tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SLAReportEntry:
    sla_name: str
    target: float
    current_value: float
    is_compliant: bool
    margin: float  # positive = above target, negative = below


@dataclass(frozen=True)
class SLAReport:
    entries: tuple[SLAReportEntry, ...]
    overall_compliance_pct: float
    total_slas: int
    compliant_count: int
    violation_count: int
    generated_at: float

    @property
    def is_fully_compliant(self) -> bool:
        return self.violation_count == 0

    @property
    def compliance_ratio(self) -> float:
        return self.compliant_count / max(self.total_slas, 1)


class SLAReporter:
    """Generates SLA compliance reports from measurement data.

    Computes per-SLA compliance status, overall compliance percentage,
    and structured report entries suitable for human or machine consumption.
    """

    def __init__(self) -> None:
        self._report_history: list[SLAReport] = []

    def generate_report(
        self,
        sla_definitions: dict[str, Any],
        measurements: dict[str, float],
        timestamp: float,
    ) -> SLAReport:
        entries: list[SLAReportEntry] = []
        compliant = 0
        violations = 0

        for name, sla_def in sla_definitions.items():
            current = measurements.get(name, 0.0)
            target = sla_def.get("target", 0.0)
            is_compliant = current >= target
            margin = current - target

            entries.append(SLAReportEntry(
                sla_name=name,
                target=target,
                current_value=current,
                is_compliant=is_compliant,
                margin=margin,
            ))

            if is_compliant:
                compliant += 1
            else:
                violations += 1

        total = len(entries)
        overall = (compliant / max(total, 1)) * 100.0

        report = SLAReport(
            entries=tuple(entries),
            overall_compliance_pct=overall,
            total_slas=total,
            compliant_count=compliant,
            violation_count=violations,
            generated_at=timestamp,
        )
        self._report_history.append(report)
        return report

    def get_report_history(self) -> list[SLAReport]:
        return list(self._report_history)

    def get_trend(self) -> str:
        if len(self._report_history) < 2:
            return "stable"
        prev = self._report_history[-2].overall_compliance_pct
        curr = self._report_history[-1].overall_compliance_pct
        if curr > prev + 0.5:
            return "improving"
        if curr < prev - 0.5:
            return "degrading"
        return "stable"

    def reset(self) -> None:
        self._report_history.clear()
