"""
L6: Failure Memory Layer - Lessons learned from errors with trigger conditions.

This layer stores failure patterns to prevent repeated mistakes.
Each failure includes trigger conditions to detect similar situations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import json


@dataclass
class FailureRecord:
    """A learned lesson from a failure."""

    failure_id: str
    error_pattern: str  # Description of what went wrong
    trigger_conditions: Dict[str, Any]  # Conditions that led to failure
    lesson: str  # What was learned
    avoid_pattern: str  # How to avoid this failure
    severity: str  # "low", "medium", "high", "critical"
    occurred_at: str
    last_triggered: Optional[str] = None
    trigger_count: int = 0
    prevented_count: int = 0  # Times we successfully avoided this
    evidence: List[str] = field(default_factory=list)  # Trajectory IDs
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "failure_id": self.failure_id,
            "error_pattern": self.error_pattern,
            "trigger_conditions": self.trigger_conditions,
            "lesson": self.lesson,
            "avoid_pattern": self.avoid_pattern,
            "severity": self.severity,
            "occurred_at": self.occurred_at,
            "last_triggered": self.last_triggered,
            "trigger_count": self.trigger_count,
            "prevented_count": self.prevented_count,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FailureRecord":
        """Create from dictionary."""
        return cls(**data)


class FailureMemoryStore:
    """Storage for failure records."""

    def __init__(self, data_dir: str = "./data/l6_failure"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.failures_file = self.data_dir / "failures.json"
        self._load_failures()

    def _load_failures(self):
        """Load failures from disk."""
        if self.failures_file.exists():
            with open(self.failures_file, "r") as f:
                data = json.load(f)
                self.failures = {
                    fail_id: FailureRecord.from_dict(fail_data)
                    for fail_id, fail_data in data.items()
                }
        else:
            self.failures = {}

    def _save_failures(self):
        """Save failures to disk."""
        data = {
            fail_id: fail.to_dict()
            for fail_id, fail in self.failures.items()
        }
        with open(self.failures_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_failure(self, failure: FailureRecord) -> str:
        """Add a new failure record."""
        self.failures[failure.failure_id] = failure
        self._save_failures()
        return failure.failure_id

    def get_failure(self, failure_id: str) -> Optional[FailureRecord]:
        """Get a failure by ID."""
        return self.failures.get(failure_id)

    def check_triggers(
        self,
        current_context: Dict[str, Any],
        min_severity: str = "low"
    ) -> List[FailureRecord]:
        """
        Check if current context matches any failure trigger conditions.

        Returns list of failures that could be triggered.
        """
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_severity_level = severity_order.get(min_severity, 0)

        triggered = []

        for failure in self.failures.values():
            # Check severity
            failure_severity = severity_order.get(failure.severity, 0)
            if failure_severity < min_severity_level:
                continue

            # Check if trigger conditions match
            if self._matches_conditions(
                current_context,
                failure.trigger_conditions
            ):
                triggered.append(failure)

        # Sort by severity and trigger count
        triggered.sort(
            key=lambda f: (
                severity_order.get(f.severity, 0),
                f.trigger_count
            ),
            reverse=True
        )

        return triggered

    def _matches_conditions(
        self,
        context: Dict[str, Any],
        conditions: Dict[str, Any],
        threshold: float = 0.8
    ) -> bool:
        """
        Check if context matches trigger conditions.

        Returns True if enough conditions match.
        """
        if not conditions:
            return False

        matching = 0
        total = len(conditions)

        for key, expected_value in conditions.items():
            if key in context:
                actual_value = context[key]

                # Exact match for strings/numbers
                if isinstance(expected_value, (str, int, float, bool)):
                    if actual_value == expected_value:
                        matching += 1
                # Substring match for strings
                elif isinstance(expected_value, str) and isinstance(actual_value, str):
                    if expected_value.lower() in actual_value.lower():
                        matching += 1
                # Range match for numbers
                elif isinstance(expected_value, dict) and "min" in expected_value:
                    if expected_value["min"] <= actual_value <= expected_value.get("max", float("inf")):
                        matching += 1

        return (matching / total) >= threshold if total > 0 else False

    def record_trigger(self, failure_id: str):
        """Record that a failure was triggered."""
        if failure_id not in self.failures:
            return

        failure = self.failures[failure_id]
        failure.trigger_count += 1
        failure.last_triggered = datetime.now().isoformat()
        self._save_failures()

    def record_prevention(self, failure_id: str):
        """Record that we successfully avoided this failure."""
        if failure_id not in self.failures:
            return

        failure = self.failures[failure_id]
        failure.prevented_count += 1
        self._save_failures()

    def get_critical_failures(self) -> List[FailureRecord]:
        """Get all critical failures."""
        return [
            f for f in self.failures.values()
            if f.severity == "critical"
        ]

    def get_frequent_failures(self, limit: int = 10) -> List[FailureRecord]:
        """Get most frequently triggered failures."""
        failures = list(self.failures.values())
        failures.sort(key=lambda f: f.trigger_count, reverse=True)
        return failures[:limit]

    def get_prevention_rate(self) -> float:
        """Calculate overall prevention rate."""
        total_triggers = sum(f.trigger_count for f in self.failures.values())
        total_prevented = sum(f.prevented_count for f in self.failures.values())

        if total_triggers + total_prevented == 0:
            return 0.0

        return total_prevented / (total_triggers + total_prevented)
