"""Quality criterion for evaluating data against thresholds."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class CriterionResult:
    """Result from evaluating a quality criterion."""

    name: str
    score: float
    passed: bool
    severity: str  # "critical", "high", "medium", "low"
    message: str = ""

    def __post_init__(self) -> None:
        """Validate severity."""
        valid_severities = {"critical", "high", "medium", "low"}
        if self.severity not in valid_severities:
            raise ValueError(
                f"Invalid severity: {self.severity}. Must be one of {valid_severities}"
            )


class QualityCriterion:
    """
    Quality criterion for evaluating data.

    Each criterion has:
    - Name (e.g., "min_sources")
    - Check function (evaluates data and returns score)
    - Severity (critical/high/medium/low)
    - Threshold (minimum score to pass)
    """

    def __init__(
        self,
        name: str,
        check_fn: Callable[[Any], float],
        severity: str,
        threshold: float,
    ) -> None:
        """
        Initialize quality criterion.

        Args:
            name: Criterion name
            check_fn: Function that evaluates data and returns score
            severity: Severity level ("critical", "high", "medium", "low")
            threshold: Minimum score to pass
        """
        self.name = name
        self.check_fn = check_fn
        self.severity = severity
        self.threshold = threshold

        # Validate severity
        valid_severities = {"critical", "high", "medium", "low"}
        if severity not in valid_severities:
            raise ValueError(
                f"Invalid severity: {severity}. Must be one of {valid_severities}"
            )

    def evaluate(self, data: Any) -> CriterionResult:
        """
        Evaluate criterion against data.

        Args:
            data: Data to evaluate

        Returns:
            CriterionResult with score and pass/fail status
        """
        try:
            score = self.check_fn(data)
            passed = score >= self.threshold

            message = ""
            if not passed:
                message = (
                    f"{self.name} failed: score={score:.2f}, threshold={self.threshold:.2f}"
                )

            return CriterionResult(
                name=self.name,
                score=score,
                passed=passed,
                severity=self.severity,
                message=message,
            )
        except Exception as e:
            # If check function fails, treat as critical failure
            return CriterionResult(
                name=self.name,
                score=0.0,
                passed=False,
                severity="critical",
                message=f"Evaluation error: {str(e)}",
            )
