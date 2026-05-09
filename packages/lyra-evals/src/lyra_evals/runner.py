"""Eval runner: executes a policy over a corpus; reports drift."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .corpora import Task


@dataclass
class TaskResult:
    task_id: str
    passed: bool
    reason: str = ""


@dataclass
class Report:
    total: int
    passed: int
    failed: int
    success_rate: float
    drift_gate_tripped: bool
    details: list[TaskResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "success_rate": self.success_rate,
            "drift_gate_tripped": self.drift_gate_tripped,
            "details": [r.__dict__ for r in self.details],
        }


Policy = Callable[[Task], TaskResult]


@dataclass
class EvalRunner:
    policy: Policy
    drift_gate: float | None = 0.85  # success-rate floor

    def run(self, tasks: list[Task]) -> Report:
        results = [self.policy(t) for t in tasks]
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        rate = (passed / total) if total else 0.0
        tripped = bool(self.drift_gate is not None and rate < self.drift_gate)
        return Report(
            total=total,
            passed=passed,
            failed=total - passed,
            success_rate=rate,
            drift_gate_tripped=tripped,
            details=results,
        )
