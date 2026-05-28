"""Quality gate system with tiered thresholds for SDLC pipeline enforcement."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class GateSeverity(StrEnum):
    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class GateResult:
    gate_name: str
    passed: bool
    severity: GateSeverity
    current_value: float
    threshold: float
    details: str = ""

    @property
    def is_blocker(self) -> bool:
        return not self.passed and self.severity == GateSeverity.BLOCKER


@dataclass(frozen=True)
class Gate:
    name: str
    severity: GateSeverity
    threshold: float
    comparator: str = "gte"  # "gte" = current >= threshold to pass

    def evaluate(self, current_value: float) -> GateResult:
        if self.comparator == "gte":
            passed = current_value >= self.threshold
        elif self.comparator == "lte":
            passed = current_value <= self.threshold
        elif self.comparator == "eq":
            passed = abs(current_value - self.threshold) < 0.001
        else:
            passed = True

        return GateResult(
            gate_name=self.name,
            passed=passed,
            severity=self.severity,
            current_value=current_value,
            threshold=self.threshold,
        )


@dataclass
class QualityGateRunner:
    """Runs all quality gates and determines overall pass/fail."""

    gates: list[Gate] = field(default_factory=list)
    _results: list[GateResult] = field(default_factory=list)

    def add_gate(self, gate: Gate) -> None:
        self.gates.append(gate)

    def run(self, metrics: dict[str, float]) -> list[GateResult]:
        self._results = []
        for gate in self.gates:
            value = metrics.get(gate.name, 0.0)
            result = gate.evaluate(value)
            self._results.append(result)
        return list(self._results)

    @property
    def passed(self) -> bool:
        return all(
            r.passed or r.severity != GateSeverity.BLOCKER
            for r in self._results
        )

    @property
    def blocker_count(self) -> int:
        return sum(1 for r in self._results if r.is_blocker)

    @property
    def warning_count(self) -> int:
        return sum(
            1 for r in self._results
            if not r.passed and r.severity == GateSeverity.WARNING
        )

    @staticmethod
    def default_gates() -> QualityGateRunner:
        runner = QualityGateRunner()
        runner.add_gate(Gate("coverage", GateSeverity.BLOCKER, 80.0, "gte"))
        runner.add_gate(Gate("lint_score", GateSeverity.BLOCKER, 100.0, "gte"))
        runner.add_gate(Gate("security_issues", GateSeverity.BLOCKER, 0.0, "lte"))
        runner.add_gate(Gate("performance_regression_pct", GateSeverity.BLOCKER, 10.0, "lte"))
        runner.add_gate(Gate("complexity_score", GateSeverity.WARNING, 20.0, "lte"))
        runner.add_gate(Gate("doc_coverage", GateSeverity.WARNING, 70.0, "gte"))
        return runner
