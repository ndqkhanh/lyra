"""Performance optimizer for Lyra.

Provides PerformanceOptimizer which identifies optimization opportunities
(caching, batching, async conversion, lazy loading) and tracks their impact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class OptimizationType(Enum):
    """Type of optimization to apply."""

    CACHING = "caching"
    BATCHING = "batching"
    ASYNC_CONVERSION = "async_conversion"
    LAZY_LOADING = "lazy_loading"
    MEMORY_POOLING = "memory_pooling"
    QUERY_OPTIMIZATION = "query_optimization"


class OptimizationStatus(Enum):
    """Status of an optimization application."""

    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    REVERTED = "reverted"


@dataclass
class OptimizationSuggestion:
    """A suggested optimization for a performance issue."""

    name: str
    optimization_type: OptimizationType
    target_function: str
    description: str
    expected_improvement_pct: float = 0.0
    complexity: str = "medium"
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        """Human-readable summary of the suggestion."""
        return (
            f"[{self.optimization_type.value}] {self.name}: "
            f"{self.description} (expected: {self.expected_improvement_pct:+.0f}%)"
        )


@dataclass
class OptimizationImpact:
    """Measured impact of an applied optimization."""

    suggestion: OptimizationSuggestion
    status: OptimizationStatus
    before_value: float = 0.0
    after_value: float = 0.0
    improvement_pct: float = 0.0
    applied_at: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""

    @property
    def successful(self) -> bool:
        """Whether the optimization improved performance."""
        return self.improvement_pct > 0

    @property
    def detail(self) -> str:
        """Detailed description of the optimization impact."""
        if self.status != OptimizationStatus.APPLIED:
            return f"Optimization not applied ({self.status.value})"
        direction = "improved" if self.successful else "degraded"
        return (
            f"Performance {direction} by {abs(self.improvement_pct):.1f}% "
            f"({self.before_value:.3f} -> {self.after_value:.3f})"
        )


class PerformanceOptimizer:
    """Identifies and applies performance optimizations.

    Analyzes code patterns and metrics to suggest optimizations
    like caching, batching, async conversion, and lazy loading.
    Tracks the impact of each applied optimization.
    """

    def __init__(self) -> None:
        """Initialize optimizer with empty suggestion and impact lists."""
        self.suggestions: list[OptimizationSuggestion] = []
        self.impacts: list[OptimizationImpact] = []
        self._optimizers: dict[OptimizationType, Callable[..., Any]] = {}

    def suggest_caching(
        self,
        target_function: str,
        description: str = "Cache repeated function results",
        expected_improvement_pct: float = 30.0,
    ) -> OptimizationSuggestion:
        """Suggest adding caching to a function.

        Args:
            target_function: Name of function to cache.
            description: Description of the caching strategy.
            expected_improvement_pct: Expected performance gain.

        Returns:
            An OptimizationSuggestion for caching.
        """
        suggestion = OptimizationSuggestion(
            name=f"cache_{target_function}",
            optimization_type=OptimizationType.CACHING,
            target_function=target_function,
            description=description,
            expected_improvement_pct=expected_improvement_pct,
        )
        self.suggestions.append(suggestion)
        return suggestion

    def suggest_batching(
        self,
        target_function: str,
        description: str = "Batch multiple calls into one",
        expected_improvement_pct: float = 50.0,
    ) -> OptimizationSuggestion:
        """Suggest batching calls to a function.

        Args:
            target_function: Name of function to batch.
            description: Description of the batching strategy.
            expected_improvement_pct: Expected performance gain.

        Returns:
            An OptimizationSuggestion for batching.
        """
        suggestion = OptimizationSuggestion(
            name=f"batch_{target_function}",
            optimization_type=OptimizationType.BATCHING,
            target_function=target_function,
            description=description,
            expected_improvement_pct=expected_improvement_pct,
        )
        self.suggestions.append(suggestion)
        return suggestion

    def suggest_async_conversion(
        self,
        target_function: str,
        description: str = "Convert synchronous call to async",
        expected_improvement_pct: float = 40.0,
    ) -> OptimizationSuggestion:
        """Suggest converting a function to async.

        Args:
            target_function: Name of function to convert.
            description: Description of the async strategy.
            expected_improvement_pct: Expected performance gain.

        Returns:
            An OptimizationSuggestion for async conversion.
        """
        suggestion = OptimizationSuggestion(
            name=f"async_{target_function}",
            optimization_type=OptimizationType.ASYNC_CONVERSION,
            target_function=target_function,
            description=description,
            expected_improvement_pct=expected_improvement_pct,
        )
        self.suggestions.append(suggestion)
        return suggestion

    def suggest_lazy_loading(
        self,
        target_function: str,
        description: str = "Defer loading until first use",
        expected_improvement_pct: float = 20.0,
    ) -> OptimizationSuggestion:
        """Suggest lazy loading for a function or module.

        Args:
            target_function: Name of function to lazy-load.
            description: Description of the lazy loading strategy.
            expected_improvement_pct: Expected performance gain.

        Returns:
            An OptimizationSuggestion for lazy loading.
        """
        suggestion = OptimizationSuggestion(
            name=f"lazy_{target_function}",
            optimization_type=OptimizationType.LAZY_LOADING,
            target_function=target_function,
            description=description,
            expected_improvement_pct=expected_improvement_pct,
        )
        self.suggestions.append(suggestion)
        return suggestion

    def apply_optimization(
        self,
        suggestion: OptimizationSuggestion,
        measure_before: Callable[[], float],
        measure_after: Callable[[], float],
    ) -> OptimizationImpact:
        """Apply an optimization and measure its impact.

        Args:
            suggestion: The optimization to apply.
            measure_before: Callable returning before-value metric.
            measure_after: Callable returning after-value metric.

        Returns:
            OptimizationImpact with before/after measurements.
        """
        before_value = measure_before()

        try:
            optimizer = self._optimizers.get(suggestion.optimization_type)
            if optimizer:
                optimizer(suggestion)

            after_value = measure_after()
            improvement = ((before_value - after_value) / before_value * 100
                           if before_value != 0 else 0.0)

            impact = OptimizationImpact(
                suggestion=suggestion,
                status=OptimizationStatus.APPLIED,
                before_value=before_value,
                after_value=after_value,
                improvement_pct=improvement,
            )
        except Exception as e:
            impact = OptimizationImpact(
                suggestion=suggestion,
                status=OptimizationStatus.FAILED,
                before_value=before_value,
                after_value=0.0,
                notes=str(e),
            )

        self.impacts.append(impact)
        return impact

    def register_optimizer(
        self,
        opt_type: OptimizationType,
        optimizer_fn: Callable[[OptimizationSuggestion], Any],
    ) -> None:
        """Register a custom optimizer function for an optimization type.

        Args:
            opt_type: The optimization type to handle.
            optimizer_fn: Function that applies the optimization.
        """
        self._optimizers[opt_type] = optimizer_fn

    def get_high_impact(self, min_improvement: float = 20.0) -> list[OptimizationImpact]:
        """Get optimizations with at least the specified improvement.

        Args:
            min_improvement: Minimum improvement percentage to filter by.

        Returns:
            List of impacts meeting the improvement threshold.
        """
        return [
            i for i in self.impacts
            if i.status == OptimizationStatus.APPLIED
            and i.improvement_pct >= min_improvement
        ]

    def analyze_hot_paths(
        self, function_times: dict[str, float],
        call_counts: dict[str, int], threshold_ms: float = 100.0,
    ) -> list[OptimizationSuggestion]:
        """Analyze hot paths and recommend optimizations."""
        suggestions: list[OptimizationSuggestion] = []
        for func_name, total_time in function_times.items():
            if total_time < threshold_ms:
                continue
            count = call_counts.get(func_name, 1)
            if count >= 10:
                suggestions.append(self.suggest_caching(func_name, description=(
                    f"Caching recommended: {func_name} called {count}x ({total_time:.0f}ms)")))
            elif count >= 3:
                suggestions.append(self.suggest_batching(func_name, description=(
                    f"Batching recommended: {func_name} called {count}x ({total_time:.0f}ms)")))
            else:
                suggestions.append(self.suggest_async_conversion(func_name, description=(
                    f"Async recommended: {func_name} taking {total_time:.0f}ms")))
        return suggestions

    def total_improvement(self) -> float:
        """Calculate total improvement across all applied optimizations.

        Returns:
            Sum of all improvement percentages.
        """
        return sum(
            i.improvement_pct
            for i in self.impacts
            if i.status == OptimizationStatus.APPLIED
        )

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all optimization activities.

        Returns:
            Dictionary with optimization statistics.
        """
        applied = [i for i in self.impacts if i.status == OptimizationStatus.APPLIED]
        failed = [i for i in self.impacts if i.status == OptimizationStatus.FAILED]

        by_type: dict[str, list[OptimizationImpact]] = {}
        for impact in self.impacts:
            t = impact.suggestion.optimization_type.value
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(impact)

        return {
            "total_suggestions": len(self.suggestions),
            "total_applied": len(applied),
            "total_failed": len(failed),
            "total_improvement_pct": self.total_improvement(),
            "by_type": {
                opt_type: {
                    "count": len(impacts),
                    "avg_improvement": (
                        sum(i.improvement_pct for i in impacts) / len(impacts)
                        if impacts else 0.0
                    ),
                }
                for opt_type, impacts in by_type.items()
            },
        }
