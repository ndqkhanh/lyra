"""Task Complexity Estimator — predict difficulty for compute allocation."""
from __future__ import annotations; import logging, math; from dataclasses import dataclass, field; from typing import Any
logger = logging.getLogger(__name__); __all__ = ["ComplexityScore", "ComplexityEstimator"]

@dataclass
class ComplexityScore: step_count: float = 0.0; ambiguity: float = 0.0; knowledge_depth: float = 0.0; overall: float = 0.0

class ComplexityEstimator:
    def __init__(self): self._estimations = 0
    def estimate(self, task: str) -> ComplexityScore:
        self._estimations += 1; t = task.lower()
        steps = min(1.0, len(t.split('.')) * 0.1 + len([w for w in ["then","first","after","finally","next"] if w in t]) * 0.15)
        ambig = 0.1 if any(w in t for w in ["maybe","perhaps","could","might","possibly"]) else 0.05
        depth = 0.1 * min(5, len([w for w in ["analyze","research","implement","design","architect","optimize"] if w in t]))
        return ComplexityScore(step_count=steps, ambiguity=ambig, knowledge_depth=depth, overall=min(1.0, steps+ambig+depth))
    @property
    def stats(self) -> dict: return {"estimations": self._estimations}
