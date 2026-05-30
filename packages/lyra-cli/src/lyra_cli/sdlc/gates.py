"""Quality gates for automated code review and merge approval."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GateStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    PENDING = "pending"
    SKIPPED = "skipped"


class GateSeverity(StrEnum):
    BLOCKER = "blocker"
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


@dataclass(frozen=True)
class GateCheck:
    check_id: str
    name: str
    status: GateStatus
    severity: GateSeverity = GateSeverity.MAJOR
    message: str = ""
    score: float = 0.0


@dataclass(frozen=True)
class GateResult:
    gate_name: str
    checks: tuple[GateCheck, ...]
    overall: GateStatus
    score: float
    summary: str = ""


class QualityGate:
    """Configurable quality gate with weighted checks.

    Usage::

        gate = QualityGate("pre-merge", min_score=0.8)
        gate.add_check("test_coverage", weight=0.3, threshold=0.8)
        gate.add_check("lint_errors", weight=0.2, threshold=0.0, higher_is_better=False)
        result = gate.evaluate({"test_coverage": 0.85, "lint_errors": 0})
    """

    def __init__(self, name: str, min_score: float = 0.8) -> None:
        self.name = name
        self.min_score = min_score
        self._checks: dict[str, _GateDefinition] = {}

    def add_check(
        self,
        name: str,
        weight: float = 1.0,
        threshold: float = 0.8,
        higher_is_better: bool = True,
        severity: GateSeverity = GateSeverity.MAJOR,
    ) -> None:
        self._checks[name] = _GateDefinition(
            name=name, weight=weight, threshold=threshold,
            higher_is_better=higher_is_better, severity=severity,
        )

    def remove_check(self, name: str) -> None:
        self._checks.pop(name, None)

    def evaluate(self, metrics: dict[str, float]) -> GateResult:
        checks: list[GateCheck] = []
        total_weight = 0.0
        weighted_score = 0.0

        for name, gate_def in self._checks.items():
            value = metrics.get(name)
            if value is None:
                checks.append(
                    GateCheck(
                        check_id=name, name=name, status=GateStatus.SKIPPED,
                        message=f"Metric '{name}' not provided",
                    )
                )
                continue

            if gate_def.higher_is_better:
                passed = value >= gate_def.threshold
            else:
                passed = value <= gate_def.threshold

            norm_score = min(value / gate_def.threshold, 1.0) if gate_def.threshold > 0 else 1.0
            if not gate_def.higher_is_better:
                norm_score = 1.0 - min(value / (gate_def.threshold * 2), 1.0)

            status = GateStatus.PASSED if passed else GateStatus.FAILED
            checks.append(
                GateCheck(
                    check_id=name, name=name, status=status,
                    severity=gate_def.severity,
                    message=f"Value {value:.2f} vs threshold {gate_def.threshold:.2f}",
                    score=round(norm_score, 2),
                )
            )
            total_weight += gate_def.weight
            weighted_score += gate_def.weight * norm_score

        final_score = weighted_score / total_weight if total_weight > 0 else 0.0
        has_blocker = any(
            c.severity == GateSeverity.BLOCKER and c.status == GateStatus.FAILED
            for c in checks
        )
        overall = GateStatus.PASSED if final_score >= self.min_score and not has_blocker else GateStatus.FAILED

        return GateResult(
            gate_name=self.name,
            checks=tuple(checks),
            overall=overall,
            score=round(final_score, 2),
            summary=self._build_summary(checks, overall, final_score),
        )

    @staticmethod
    def _build_summary(checks: list[GateCheck], overall: GateStatus, score: float) -> str:
        passed = sum(1 for c in checks if c.status == GateStatus.PASSED)
        failed = sum(1 for c in checks if c.status == GateStatus.FAILED)
        return f"{overall.upper()} (score={score:.0%}, {passed}/{len(checks)} checks passed, {failed} failed)"


@dataclass
class _GateDefinition:
    name: str
    weight: float
    threshold: float
    higher_is_better: bool
    severity: GateSeverity
