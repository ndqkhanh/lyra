"""Fitness evaluator — measures strategy fitness against defined targets.

Evaluates evolution strategies against configurable fitness targets
(success rate, speed, cost, quality) and produces weighted fitness scores.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class FitnessTarget:
    name: str
    weight: float
    target_value: float
    higher_is_better: bool


@dataclass(frozen=True)
class FitnessReport:
    strategy_id: str
    scores: dict[str, float]
    weighted_score: float
    meets_all_targets: bool
    evaluated_at: float


class FitnessEvaluator:
    """Evaluates strategy fitness against configurable targets.

    Computes normalized scores for each fitness dimension and
    produces a weighted composite score. Supports both maximization
    and minimization targets.
    """

    DEFAULT_TARGETS: list[FitnessTarget] = [
        FitnessTarget(name="success_rate", weight=0.4, target_value=0.9, higher_is_better=True),
        FitnessTarget(name="speed_ms", weight=0.2, target_value=500.0, higher_is_better=False),
        FitnessTarget(name="cost_tokens", weight=0.2, target_value=1000.0, higher_is_better=False),
        FitnessTarget(name="quality_score", weight=0.2, target_value=0.85, higher_is_better=True),
    ]

    def __init__(self, targets: list[FitnessTarget] | None = None) -> None:
        self._targets = targets or self.DEFAULT_TARGETS
        self._reports: dict[str, list[FitnessReport]] = {}

    def evaluate(
        self, strategy_id: str, metrics: dict[str, float]
    ) -> FitnessReport:
        scores: dict[str, float] = {}
        weighted_total = 0.0
        total_weight = sum(t.weight for t in self._targets)
        all_met = True

        for target in self._targets:
            raw = metrics.get(target.name, 0.0)
            score = self._normalize(raw, target)
            scores[target.name] = score
            weighted_total += score * target.weight

            if target.higher_is_better:
                if raw < target.target_value:
                    all_met = False
            else:
                if raw > target.target_value:
                    all_met = False

        weighted_score = round(weighted_total / max(total_weight, 0.001), 4)

        report = FitnessReport(
            strategy_id=strategy_id,
            scores=scores,
            weighted_score=weighted_score,
            meets_all_targets=all_met,
            evaluated_at=time.time(),
        )
        self._reports.setdefault(strategy_id, []).append(report)
        return report

    def _normalize(self, value: float, target: FitnessTarget) -> float:
        if target.target_value == 0:
            return 1.0 if value >= 0 else 0.0

        if target.higher_is_better:
            return round(min(1.0, value / target.target_value), 4)
        return round(min(1.0, target.target_value / max(value, 0.001)), 4)

    def get_best(self) -> FitnessReport | None:
        best = None
        best_score = -1.0
        for reports in self._reports.values():
            for report in reports:
                if report.weighted_score > best_score:
                    best_score = report.weighted_score
                    best = report
        return best

    def get_history(self, strategy_id: str) -> list[FitnessReport]:
        return self._reports.get(strategy_id, [])

    def stats(self) -> dict:
        return {
            "strategies_evaluated": len(self._reports),
            "targets": [t.name for t in self._targets],
        }
