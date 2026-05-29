"""
Integrity Gate Implementation

Mandatory validation checkpoints that cannot be skipped.
Implements stages 2.5 (post-discovery) and 4.5 (pre-report).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class Severity(Enum):
    """Issue severity levels"""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class ValidationResult:
    """Result from a single validator"""

    passed: bool
    severity: Severity
    message: str
    validator_name: str


@dataclass
class GateResult:
    """Result from integrity gate validation"""

    passed: bool
    stage: str
    issues: list[ValidationResult]
    blocking_issues: list[ValidationResult]
    message: str = ""


class Validator(Protocol):
    """Protocol for validators"""

    def validate(self, research_state: dict) -> ValidationResult:
        """Validate research state"""
        ...


class IntegrityGate:
    """
    Cannot-skip validation checkpoint

    Implements mandatory integrity gates at stages 2.5 and 4.5.
    These gates CANNOT be skipped or bypassed.
    """

    def __init__(self, stage: str, validators: list[Validator]):
        """
        Initialize integrity gate

        Args:
            stage: Gate stage ("2.5" or "4.5")
            validators: List of validators to run
        """
        self.stage = stage
        self.validators = validators
        self.can_skip = False  # HARD-CODED: cannot be overridden

    def validate(self, research_state: dict) -> GateResult:
        """
        Run all validators, block if any CRITICAL issues found

        Args:
            research_state: Current research state

        Returns:
            GateResult with validation results
        """
        results = []

        for validator in self.validators:
            try:
                result = validator.validate(research_state)
                results.append(result)
            except Exception as e:
                # Validator failure is treated as CRITICAL
                results.append(
                    ValidationResult(
                        passed=False,
                        severity=Severity.CRITICAL,
                        message=f"Validator failed: {str(e)}",
                        validator_name=validator.__class__.__name__,
                    )
                )

        # Check for CRITICAL issues
        blocking_issues = [r for r in results if r.severity == Severity.CRITICAL and not r.passed]

        if blocking_issues:
            return GateResult(
                passed=False,
                stage=self.stage,
                issues=results,
                blocking_issues=blocking_issues,
                message=(
                    f"Stage {self.stage} BLOCKED: {len(blocking_issues)}"
                    f" CRITICAL issues detected. Cannot proceed."
                ),
            )

        return GateResult(
            passed=True,
            stage=self.stage,
            issues=results,
            blocking_issues=[],
            message=f"Stage {self.stage} passed: All validators successful",
        )
