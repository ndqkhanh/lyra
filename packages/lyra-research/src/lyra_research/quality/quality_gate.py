"""Base quality gate for role transitions."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List

from lyra_research.quality.quality_criterion import CriterionResult, QualityCriterion


@dataclass
class GateResult:
    """Result from quality gate check."""

    gate_name: str
    passed: bool
    criteria_results: List[CriterionResult]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0

    def has_critical_failures(self) -> bool:
        """Check if any critical criteria failed."""
        return any(
            not r.passed and r.severity == "critical" for r in self.criteria_results
        )

    def has_high_failures(self) -> bool:
        """Check if any high severity criteria failed."""
        return any(
            not r.passed and r.severity == "high" for r in self.criteria_results
        )

    def get_failed_criteria(self) -> List[CriterionResult]:
        """Get list of failed criteria."""
        return [r for r in self.criteria_results if not r.passed]

    def get_pass_rate(self) -> float:
        """Calculate pass rate (0.0 to 1.0)."""
        if not self.criteria_results:
            return 0.0
        passed = sum(1 for r in self.criteria_results if r.passed)
        return passed / len(self.criteria_results)


class QualityGate(ABC):
    """
    Base quality gate for role transitions.

    Each gate:
    - Has multiple quality criteria
    - Evaluates data against criteria
    - Returns pass/fail result
    - Tracks historical pass rates
    """

    def __init__(self, name: str, criteria: List[QualityCriterion]) -> None:
        """
        Initialize quality gate.

        Args:
            name: Gate name (e.g., "DiscoveryGate")
            criteria: List of quality criteria
        """
        self.name = name
        self.criteria = criteria
        self.history: List[GateResult] = []

    def check(self, data: Any, retry_count: int = 0) -> GateResult:
        """
        Check if data passes quality gate.

        Args:
            data: Data to evaluate
            retry_count: Number of retries so far

        Returns:
            GateResult with pass/fail status and criterion results
        """
        # Evaluate all criteria
        criteria_results = [criterion.evaluate(data) for criterion in self.criteria]

        # Gate passes if all criteria pass
        passed = all(r.passed for r in criteria_results)

        result = GateResult(
            gate_name=self.name,
            passed=passed,
            criteria_results=criteria_results,
            retry_count=retry_count,
        )

        # Store in history
        self.history.append(result)

        return result

    def get_pass_rate(self) -> float:
        """
        Get historical pass rate.

        Returns:
            Pass rate (0.0 to 1.0), or 0.0 if no history
        """
        if not self.history:
            return 0.0
        passed = sum(1 for r in self.history if r.passed)
        return passed / len(self.history)

    def get_criterion_stats(self) -> dict[str, dict[str, float]]:
        """
        Get statistics for each criterion.

        Returns:
            Dict mapping criterion name to stats (pass_rate, avg_score)
        """
        stats = {}
        for criterion in self.criteria:
            criterion_results = [
                r
                for result in self.history
                for r in result.criteria_results
                if r.name == criterion.name
            ]

            if criterion_results:
                pass_rate = sum(1 for r in criterion_results if r.passed) / len(
                    criterion_results
                )
                avg_score = sum(r.score for r in criterion_results) / len(
                    criterion_results
                )
                stats[criterion.name] = {
                    "pass_rate": pass_rate,
                    "avg_score": avg_score,
                }

        return stats
