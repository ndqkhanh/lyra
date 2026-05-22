"""Counterfactual — 'What if' simulation engine over causal graphs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from lyra_causal_graph import CausalGraph

logger = logging.getLogger(__name__)

__all__ = [
    "Intervention",
    "SimulationResult",
    "CounterfactualEngine",
]




@dataclass
class Intervention:
    action_type: str
    source_id: str
    target_id: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationResult:
    predicted_outcome: str
    confidence: float
    causal_path: list[str]
    alternative_prob: float = 0.0


class CounterfactualEngine:
    """Rewinds causal graph, applies intervention, simulates outcome."""

    def __init__(self, causal_graph: CausalGraph):
        self.graph = causal_graph

    async def simulate(self, intervention: Intervention) -> SimulationResult:
        path = self._trace_causal_path(intervention)
        confidence = self._estimate_confidence(intervention, path)
        return SimulationResult(
            predicted_outcome=self._predict_outcome(intervention, path),
            confidence=confidence,
            causal_path=path,
        )

    def _trace_causal_path(self, intervention: Intervention) -> list[str]:
        path = []
        source_actions = self.graph.get_actions_for_entity(intervention.source_id)
        for action in source_actions:
            if action.action_type == intervention.action_type:
                path.append(f"{intervention.source_id}->{action.target_id}")
                outcome = self.graph.get_outcome_for_action(action.id)
                if outcome:
                    path.append(f"outcome:{outcome.result[:50]}")
        if not path:
            path.append(f"{intervention.source_id}->? (no prior {intervention.action_type} actions)")
        return path

    def _estimate_confidence(self, intervention: Intervention, path: list[str]) -> float:
        te = self.graph.compute_li_cte(intervention.source_id, intervention.target_id)
        base = 0.5 + (te * 0.4)
        return min(base, 0.95)

    def _predict_outcome(self, intervention: Intervention, path: list[str]) -> str:
        if "execute" in intervention.action_type or "call" in intervention.action_type:
            return f"Simulated {intervention.action_type} on {intervention.target_id}"
        return f"Would affect {intervention.target_id} via {intervention.action_type}"
