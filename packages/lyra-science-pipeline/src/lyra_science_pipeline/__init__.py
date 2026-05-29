"""Science Pipeline — Hypothesis→Experiment→Analyze→Learn discovery cycle."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "Hypothesis",
    "ExperimentResult",
    "TrialHarness",
    "SciencePipeline",
]


@dataclass
class Hypothesis:
    id: str
    statement: str
    independent_var: str
    dependent_var: str
    expected_effect: str
    confidence: float = 0.5
    status: str = "proposed"  # proposed, testing, confirmed, refuted


@dataclass
class ExperimentResult:
    hypothesis_id: str
    outcome: str
    effect_size: float
    significance: float
    supports_hypothesis: bool
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrialHarness:
    id: str
    sandbox_type: str
    max_steps: int = 10
    variables: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)


class SciencePipeline:
    """Scientific discovery pipeline implementing the full cycle."""

    def __init__(self):
        self.hypotheses: list[Hypothesis] = []
        self.results: list[ExperimentResult] = []
        self.trial_harnesses: list[TrialHarness] = []

    def propose_hypothesis(self, statement: str, iv: str, dv: str, effect: str) -> Hypothesis:
        h = Hypothesis(
            id=f"H{len(self.hypotheses)+1}",
            statement=statement,
            independent_var=iv,
            dependent_var=dv,
            expected_effect=effect,
        )
        self.hypotheses.append(h)
        return h

    def create_harness(self, sandbox_type: str, variables: dict[str, Any]) -> TrialHarness:
        h = TrialHarness(
            id=f"TH{len(self.trial_harnesses)+1}",
            sandbox_type=sandbox_type,
            variables=variables,
        )
        self.trial_harnesses.append(h)
        return h

    async def run_experiment(self, hypothesis_id: str, harness_id: str) -> ExperimentResult:
        hypothesis = next((h for h in self.hypotheses if h.id == hypothesis_id), None)
        if not hypothesis:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")

        hypothesis.status = "testing"
        effect_size = 0.7  # simulated
        significance = 0.95  # simulated
        supports = effect_size > 0.3 and significance > 0.8

        result = ExperimentResult(
            hypothesis_id=hypothesis_id,
            outcome=f"Experiment completed: {hypothesis.statement}",
            effect_size=effect_size,
            significance=significance,
            supports_hypothesis=supports,
        )
        self.results.append(result)
        hypothesis.status = "confirmed" if supports else "refuted"
        hypothesis.confidence = significance if supports else 1 - significance
        return result

    def analyze_results(self) -> list[dict[str, Any]]:
        analysis = []
        for h in self.hypotheses:
            related = [r for r in self.results if r.hypothesis_id == h.id]
            analysis.append(
                {
                    "hypothesis": h.statement,
                    "status": h.status,
                    "confidence": h.confidence,
                    "experiments": len(related),
                    "conclusion": (
                        "Supported"
                        if any(r.supports_hypothesis for r in related)
                        else "Not supported"
                    ),
                }
            )
        return analysis
