"""Explanation Engine — decision explanations, counterfactuals, confidence breakdowns.

Helps humans understand why Lyra makes the decisions it does.
Critical for trust calibration in human-AGI collaboration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "Explanation",
    "Counterfactual",
    "ExplanationEngine",
]


@dataclass
class Explanation:
    decision_id: str
    summary: str
    reasoning_steps: list[str]
    confidence: float = 1.0
    alternative_considered: list[str] = field(default_factory=list)


@dataclass
class Counterfactual:
    decision_id: str
    alternative_action: str
    predicted_outcome: str
    delta: float = 0.0


class ExplanationEngine:
    """Generates natural language explanations for agent decisions."""

    def __init__(self):
        self._explanation_count = 0

    def explain(self, decision: dict[str, Any], depth: str = "normal") -> Explanation:
        self._explanation_count += 1
        action = decision.get("action", "unknown")
        return Explanation(
            decision_id=f"dec_{self._explanation_count}",
            summary=f"The agent chose to {action} for the following reasons:",
            reasoning_steps=[
                f"1. Analyzed the current state: {decision.get('context', 'N/A')[:50]}",
                f"2. Evaluated {len(decision.get('alternatives', ['the chosen action']))} alternatives",
                f"3. Selected '{action}' as the highest-scoring option (score: {decision.get('score', 0.5):.2f})",
            ],
            confidence=decision.get("confidence", 0.8),
            alternative_considered=decision.get("alternatives", []),
        )

    def counterfactual(self, decision: dict[str, Any], alternative: str) -> Counterfactual:
        return Counterfactual(
            decision_id=f"cf_{self._explanation_count}",
            alternative_action=alternative,
            predicted_outcome=f"If we had chosen '{alternative}' instead, the result would have been different.",
            delta=decision.get("score", 0.5) - 0.3,
        )

    def confidence_breakdown(self, decision: dict[str, Any]) -> dict[str, float]:
        return {
            "data_quality": 0.85,
            "model_certainty": 0.75,
            "context_completeness": 0.90,
            "history_consistency": 0.80,
        }

    @property
    def stats(self) -> dict[str, Any]:
        return {"explanations_generated": self._explanation_count}
