"""
Performance tracking for model execution metrics.

Tracks latency, quality, and cost metrics across different models
to enable data-driven model selection.
"""

import statistics
from dataclasses import dataclass, field


@dataclass
class ModelStats:
    """Statistics for a model's performance."""

    model: str
    role: str
    execution_count: int = 0
    avg_latency_ms: float = 0.0
    avg_quality_score: float = 0.0
    avg_cost: float = 0.0
    total_cost: float = 0.0
    latencies: list[float] = field(default_factory=list)
    quality_scores: list[float] = field(default_factory=list)
    costs: list[float] = field(default_factory=list)


class ModelPerformanceTracker:
    """Track performance metrics for different models."""

    def __init__(self):
        """Initialize performance tracker."""
        # Key: (model, role) -> ModelStats
        self.stats: dict[tuple[str, str], ModelStats] = {}

    def record_execution(
        self,
        model: str,
        role: str,
        latency_ms: float,
        quality_score: float,
        cost: float
    ) -> None:
        """
        Record model execution metrics.

        Args:
            model: Model identifier
            role: Role performing the task
            latency_ms: Execution latency in milliseconds
            quality_score: Quality score (0.0-1.0)
            cost: Execution cost in USD
        """
        key = (model, role)

        if key not in self.stats:
            self.stats[key] = ModelStats(model=model, role=role)

        stats = self.stats[key]
        stats.execution_count += 1
        stats.latencies.append(latency_ms)
        stats.quality_scores.append(quality_score)
        stats.costs.append(cost)
        stats.total_cost += cost

        # Update averages
        stats.avg_latency_ms = statistics.mean(stats.latencies)
        stats.avg_quality_score = statistics.mean(stats.quality_scores)
        stats.avg_cost = statistics.mean(stats.costs)

    def get_best_model_for_role(self, role: str) -> str:
        """
        Get best performing model for a role based on history.

        Uses a composite score: quality / (latency * cost)

        Args:
            role: The role to find best model for

        Returns:
            Best model identifier

        Raises:
            ValueError: If no data exists for role
        """
        role_stats = [
            stats for (model, r), stats in self.stats.items()
            if r == role and stats.execution_count > 0
        ]

        if not role_stats:
            raise ValueError(f"No performance data for role: {role}")

        # Calculate composite score: quality / (normalized_latency * normalized_cost)
        def composite_score(stats: ModelStats) -> float:
            if stats.avg_latency_ms == 0 or stats.avg_cost == 0:
                return 0.0

            # Normalize latency (lower is better, so invert)
            norm_latency = 1000.0 / stats.avg_latency_ms

            # Normalize cost (lower is better, so invert)
            norm_cost = 0.01 / stats.avg_cost if stats.avg_cost > 0 else 0.0

            return stats.avg_quality_score * norm_latency * norm_cost

        best_stats = max(role_stats, key=composite_score)
        return best_stats.model

    def compare_models(self, role: str) -> dict[str, ModelStats]:
        """
        Compare all models for a specific role.

        Args:
            role: The role to compare models for

        Returns:
            Dictionary mapping model to stats
        """
        return {
            model: stats
            for (model, r), stats in self.stats.items()
            if r == role
        }

    def get_stats(self, model: str, role: str) -> ModelStats:
        """
        Get statistics for a specific model and role.

        Args:
            model: Model identifier
            role: Role identifier

        Returns:
            ModelStats for the model-role combination

        Raises:
            ValueError: If no data exists
        """
        key = (model, role)
        if key not in self.stats:
            raise ValueError(f"No stats for model={model}, role={role}")

        return self.stats[key]

    def get_all_stats(self) -> dict[tuple[str, str], ModelStats]:
        """
        Get all tracked statistics.

        Returns:
            Dictionary of all model-role statistics
        """
        return self.stats.copy()

    def reset_stats(self, model: str = None, role: str = None) -> None:
        """
        Reset statistics for specific model/role or all.

        Args:
            model: Optional model to reset (None = all models)
            role: Optional role to reset (None = all roles)
        """
        if model is None and role is None:
            self.stats.clear()
        else:
            keys_to_remove = [
                key for key in self.stats.keys()
                if (model is None or key[0] == model) and
                   (role is None or key[1] == role)
            ]
            for key in keys_to_remove:
                del self.stats[key]
