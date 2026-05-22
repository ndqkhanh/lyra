"""Alignment Engine — value learning, constraint satisfaction, inverse reinforcement learning, trust calibration.

Ensures Lyra's actions align with human values. Learns preferences from
feedback, satisfies constraints, and calibrates trust appropriately.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "Constraint",
    "ValuePreference",
    "AlignmentEngine",
]


@dataclass
class Constraint:
    name: str
    check: str
    is_hard: bool = True


@dataclass
class ValuePreference:
    dimension: str
    direction: str  # "maximize" | "minimize" | "satisfice"
    threshold: float = 0.5


class AlignmentEngine:
    """Learns human values, satisfies constraints, and calibrates trust."""

    def __init__(self):
        self.constraints: list[Constraint] = []
        self.preferences: list[ValuePreference] = []
        self._feedback: list[dict[str, Any]] = []
        self.trust_score: float = 0.5

    def add_constraint(self, constraint: Constraint) -> None:
        self.constraints.append(constraint)

    def add_preference(self, preference: ValuePreference) -> None:
        self.preferences.append(preference)

    def check_constraints(self, action: dict[str, Any]) -> list[str]:
        violations = []
        for constraint in self.constraints:
            if not self._evaluate(constraint.check, action):
                violations.append(constraint.name)
        return violations

    def _evaluate(self, check: str, action: dict[str, Any]) -> bool:
        action_str = str(action).lower()
        if "not" in check.lower():
            negated_term = check.lower().replace("not ", "").replace("not_", "")
            return negated_term not in action_str
        return check.lower() in action_str

    def learn_from_feedback(self, action: dict[str, Any], human_rating: float) -> None:
        self._feedback.append({"action": action, "rating": human_rating})
        avg_rating = sum(f["rating"] for f in self._feedback) / len(self._feedback)
        self.trust_score = 0.3 + 0.7 * avg_rating

    def should_ask_human(self, action: dict[str, Any], confidence: float) -> bool:
        violations = self.check_constraints(action)
        if violations:
            return True
        if confidence < self.trust_score:
            return True
        return False

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "constraints": len(self.constraints),
            "preferences": len(self.preferences),
            "feedback_samples": len(self._feedback),
            "trust_score": self.trust_score,
        }
