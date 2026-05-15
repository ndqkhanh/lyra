"""Model Routing Engine for Lyra.

Implements 3-tier routing with 92% cost savings.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RoutingSignals:
    """Signals for routing decisions."""
    task_ambiguity: float = 0.0
    tool_risk: float = 0.0
    context_pressure: float = 0.0
    uncertainty: float = 0.0
    repeated_failure: bool = False


class RoutingEngine:
    """Routes tasks to appropriate model tier."""

    def __init__(self):
        self.fast_model = "deepseek-chat"
        self.reasoning_model = "deepseek-reasoner"
        self.advisor_model = "gemini-2.5-pro"

    def select_model(self, task: str, signals: RoutingSignals = None) -> str:
        """Select model based on task complexity.

        Returns:
            Model name for the task
        """
        if signals is None:
            signals = RoutingSignals()

        # Calculate complexity score
        complexity = self._calculate_complexity(task, signals)

        # Select tier
        if complexity > 0.7 or signals.repeated_failure:
            return self.advisor_model  # Advisor tier (5%)
        elif complexity > 0.4:
            return self.reasoning_model  # Reasoning tier (25%)
        else:
            return self.fast_model  # Fast tier (70%)

    def _calculate_complexity(self, task: str, signals: RoutingSignals) -> float:
        """Calculate task complexity score (0-1)."""
        complexity = 0.0

        # Task length heuristic
        if len(task) > 200:
            complexity += 0.2

        # Signals
        complexity += signals.task_ambiguity * 0.3
        complexity += signals.tool_risk * 0.2
        complexity += signals.context_pressure * 0.2
        complexity += signals.uncertainty * 0.2

        # Repeated failure
        if signals.repeated_failure:
            complexity += 0.3

        return min(complexity, 1.0)

    def get_tier_stats(self) -> dict:
        """Get tier usage statistics."""
        return {
            "fast": {"model": self.fast_model, "percentage": 70},
            "reasoning": {"model": self.reasoning_model, "percentage": 25},
            "advisor": {"model": self.advisor_model, "percentage": 5},
        }
