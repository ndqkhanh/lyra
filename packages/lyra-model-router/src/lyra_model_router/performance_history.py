"""Performance history tracking with learned success rates per category+model.

Plan 10 Layer 5: Tracks outcomes of routing decisions to build a
learned performance profile. Used by the router to prefer models
with proven success on specific task categories and complexity levels.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field

from .task_classifier import TaskCategory


@dataclass(frozen=True)
class PerformanceRecord:
    """A single performance observation.

    Attributes:
        model_id: The model that was used.
        category: Task category.
        complexity: Complexity score at time of routing (1-10).
        success: Whether the task was completed successfully.
        tokens_used: Total tokens consumed.
        latency_ms: Observed latency.
        cost_usd: Actual cost.
        timestamp: Unix timestamp of the observation.
    """

    model_id: str
    category: TaskCategory
    complexity: float
    success: bool
    tokens_used: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class ModelPerformance:
    """Aggregated performance metrics for a model+category pair.

    Attributes:
        model_id: Model identifier.
        category: Task category.
        total_attempts: Number of routing decisions.
        success_count: Number of successful outcomes.
        success_rate: Ratio of success/attempts (0.0-1.0).
        avg_latency_ms: Mean observed latency.
        avg_cost_usd: Mean observed cost.
        last_used: Timestamp of most recent use.
    """

    model_id: str
    category: TaskCategory
    total_attempts: int = 0
    success_count: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    avg_cost_usd: float = 0.0
    last_used: float = 0.0

    @property
    def is_cold(self) -> bool:
        """True if insufficient data for reliable recommendation."""
        return self.total_attempts < 5


@dataclass(frozen=True)
class Recommendation:
    """Model recommendation based on performance history.

    Attributes:
        model_id: Recommended model.
        category: Task category.
        success_rate: Historical success rate for this pair.
        confidence: Recommendation confidence (0.0-1.0).
        sample_size: Number of historical observations.
    """

    model_id: str
    category: TaskCategory
    success_rate: float
    confidence: float
    sample_size: int


class PerformanceHistory:
    """Learned performance profile for routing optimization.

    Tracks success/failure per model+category+complexity band,
    enabling the router to prefer models with proven track records.
    Includes time-decay so recent performance outweighs stale data.
    """

    def __init__(self, decay_days: float = 30.0) -> None:
        self._decay_days = decay_days
        self._records: list[PerformanceRecord] = []

    def record(self, record: PerformanceRecord) -> None:
        """Record a performance observation."""
        self._records.append(record)

    def get_model_performance(
        self, model_id: str, category: TaskCategory
    ) -> ModelPerformance:
        """Get aggregated performance for a specific model+category pair."""
        relevant = [
            r for r in self._records
            if r.model_id == model_id and r.category == category
        ]
        if not relevant:
            return ModelPerformance(model_id=model_id, category=category)

        total = len(relevant)
        success = sum(1 for r in relevant if r.success)
        latencies = [r.latency_ms for r in relevant if r.latency_ms > 0]
        costs = [r.cost_usd for r in relevant if r.cost_usd > 0]
        last = max(r.timestamp for r in relevant)

        return ModelPerformance(
            model_id=model_id,
            category=category,
            total_attempts=total,
            success_count=success,
            success_rate=round(success / total, 4),
            avg_latency_ms=round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            avg_cost_usd=round(sum(costs) / len(costs), 6) if costs else 0.0,
            last_used=last,
        )

    def recommend_model(
        self,
        category: TaskCategory,
        available_models: list[str],
        complexity: float = 5.0,
        min_attempts: int = 3,
    ) -> Recommendation | None:
        """Recommend the best model for a task category based on history.

        Filters to records within ±2.0 of the target complexity so
        recommendations are tuned to the difficulty band.

        Returns None if no model has sufficient history.
        """
        best: Recommendation | None = None

        for model_id in available_models:
            perf = self.get_model_performance(model_id, category)
            if perf.total_attempts < min_attempts:
                continue

            # Time-decayed success rate — recent success matters more
            decayed_rate = self._apply_time_decay(
                model_id, category, complexity_band=complexity
            )

            # Confidence scales with sample size and complexity match
            complexity_bonus = self._complexity_bonus(model_id, category, complexity)
            confidence = min(1.0, (perf.total_attempts / 20.0) + complexity_bonus)

            if best is None or decayed_rate > best.success_rate:
                best = Recommendation(
                    model_id=model_id,
                    category=category,
                    success_rate=round(decayed_rate, 4),
                    confidence=round(confidence, 4),
                    sample_size=perf.total_attempts,
                )

        return best

    def _complexity_bonus(
        self, model_id: str, category: TaskCategory, complexity: float
    ) -> float:
        """Bonus confidence when history matches the target complexity."""
        relevant = [
            r for r in self._records
            if r.model_id == model_id
            and r.category == category
            and abs(r.complexity - complexity) <= 2.0
        ]
        if not relevant:
            return 0.0
        success = sum(1 for r in relevant if r.success)
        return min(0.3, (success / len(relevant)) * 0.3)

    def get_category_leaderboard(
        self, category: TaskCategory, top_n: int = 5
    ) -> list[ModelPerformance]:
        """Return models ranked by success rate for a category."""
        models: dict[str, list[PerformanceRecord]] = defaultdict(list)
        for r in self._records:
            if r.category == category:
                models[r.model_id].append(r)

        performances: list[ModelPerformance] = []
        for model_id, recs in models.items():
            total = len(recs)
            success = sum(1 for r in recs if r.success)
            performances.append(ModelPerformance(
                model_id=model_id,
                category=category,
                total_attempts=total,
                success_count=success,
                success_rate=round(success / total, 4),
            ))

        performances.sort(key=lambda p: p.success_rate, reverse=True)
        return performances[:top_n]

    def get_global_stats(self) -> dict[str, float]:
        """Return global statistics across all records."""
        if not self._records:
            return {"total_decisions": 0, "global_success_rate": 0.0}

        total = len(self._records)
        success = sum(1 for r in self._records if r.success)
        return {
            "total_decisions": total,
            "global_success_rate": round(success / total, 4),
            "avg_complexity": round(
                sum(r.complexity for r in self._records) / total, 1
            ),
            "unique_models": len({r.model_id for r in self._records}),
            "unique_categories": len({r.category for r in self._records}),
        }

    def _apply_time_decay(
        self,
        model_id: str,
        category: TaskCategory,
        complexity_band: float | None = None,
    ) -> float:
        """Compute time-decayed success rate — recent outcomes weigh more.

        When complexity_band is provided, filters to records within ±2.0
        of the target complexity for more relevant scoring.
        """
        now = time.time()
        decay_seconds = self._decay_days * 86400
        relevant = [
            r for r in self._records
            if r.model_id == model_id and r.category == category
        ]
        if complexity_band is not None:
            relevant = [
                r for r in relevant
                if abs(r.complexity - complexity_band) <= 2.0
            ]
        if not relevant:
            return 0.0

        weighted_success = 0.0
        total_weight = 0.0
        for r in relevant:
            age = now - r.timestamp
            weight = max(0.1, 1.0 - (age / decay_seconds))
            weighted_success += weight * (1.0 if r.success else 0.0)
            total_weight += weight

        return weighted_success / total_weight if total_weight > 0 else 0.0

    def prune_old_records(self, max_age_days: float = 90.0) -> int:
        """Remove records older than max_age_days. Returns count removed."""
        cutoff = time.time() - (max_age_days * 86400)
        before = len(self._records)
        self._records = [r for r in self._records if r.timestamp >= cutoff]
        return before - len(self._records)

    @property
    def record_count(self) -> int:
        return len(self._records)
