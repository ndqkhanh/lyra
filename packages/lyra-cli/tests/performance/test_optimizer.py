"""Tests for the PerformanceOptimizer module."""

from __future__ import annotations

import pytest
from lyra_cli.performance.optimizer import (
    OptimizationStatus,
    OptimizationSuggestion,
    OptimizationType,
    PerformanceOptimizer,
)


def test_suggest_caching_creates_suggestion() -> None:
    """suggest_caching should create a CACHING type suggestion."""
    optimizer = PerformanceOptimizer()
    suggestion = optimizer.suggest_caching(
        "get_user_data",
        description="Cache user data lookups",
        expected_improvement_pct=50.0,
    )
    assert suggestion.optimization_type == OptimizationType.CACHING
    assert suggestion.target_function == "get_user_data"
    assert suggestion.expected_improvement_pct == 50.0
    assert "cache" in suggestion.name
    assert suggestion in optimizer.suggestions


def test_all_suggestion_types() -> None:
    """Each suggestion method should create the correct type."""
    optimizer = PerformanceOptimizer()

    caching = optimizer.suggest_caching("fn_a")
    assert caching.optimization_type == OptimizationType.CACHING

    batching = optimizer.suggest_batching("fn_b")
    assert batching.optimization_type == OptimizationType.BATCHING

    async_conv = optimizer.suggest_async_conversion("fn_c")
    assert async_conv.optimization_type == OptimizationType.ASYNC_CONVERSION

    lazy = optimizer.suggest_lazy_loading("fn_d")
    assert lazy.optimization_type == OptimizationType.LAZY_LOADING


def test_apply_optimization_measures_impact() -> None:
    """apply_optimization should record before/after measurements."""
    optimizer = PerformanceOptimizer()
    suggestion = optimizer.suggest_caching("compute")

    impact = optimizer.apply_optimization(
        suggestion,
        measure_before=lambda: 100.0,
        measure_after=lambda: 60.0,
    )
    assert impact.status == OptimizationStatus.APPLIED
    assert impact.before_value == 100.0
    assert impact.after_value == 60.0
    assert impact.improvement_pct == 40.0
    assert impact.successful
    assert impact in optimizer.impacts


def test_apply_optimization_handles_failure() -> None:
    """apply_optimization should return FAILED status when measure_after raises."""

    def failing_measure() -> float:
        raise ValueError("measurement failed")

    optimizer = PerformanceOptimizer()
    suggestion = optimizer.suggest_caching("compute")

    impact = optimizer.apply_optimization(
        suggestion,
        measure_before=lambda: 100.0,
        measure_after=failing_measure,
    )
    assert impact.status == OptimizationStatus.FAILED
    assert not impact.successful


def test_get_high_impact_filters_correctly() -> None:
    """get_high_impact should return only optimizations above threshold."""
    optimizer = PerformanceOptimizer()

    low = optimizer.suggest_caching("low_impact")
    high = optimizer.suggest_caching("high_impact")

    optimizer.apply_optimization(
        low, measure_before=lambda: 100.0, measure_after=lambda: 95.0
    )
    optimizer.apply_optimization(
        high, measure_before=lambda: 100.0, measure_after=lambda: 50.0
    )

    high_impacts = optimizer.get_high_impact(min_improvement=30.0)
    assert len(high_impacts) == 1
    assert high_impacts[0].suggestion.target_function == "high_impact"


def test_analyze_hot_paths_generates_suggestions() -> None:
    """analyze_hot_paths should create suggestions based on function times."""
    optimizer = PerformanceOptimizer()
    suggestions = optimizer.analyze_hot_paths(
        function_times={
            "frequent_func": 500.0,
            "moderate_func": 200.0,
            "slow_func": 300.0,
            "fast_func": 5.0,
        },
        call_counts={
            "frequent_func": 15,
            "moderate_func": 5,
            "slow_func": 1,
            "fast_func": 1,
        },
        threshold_ms=10.0,
    )
    assert len(suggestions) >= 1
    types = {s.optimization_type for s in suggestions}
    assert OptimizationType.CACHING in types or OptimizationType.BATCHING in types


def test_total_improvement_accumulates() -> None:
    """total_improvement should sum all applied improvement percentages."""
    optimizer = PerformanceOptimizer()

    s1 = optimizer.suggest_caching("a")
    s2 = optimizer.suggest_caching("b")

    optimizer.apply_optimization(
        s1, measure_before=lambda: 100.0, measure_after=lambda: 70.0
    )
    optimizer.apply_optimization(
        s2, measure_before=lambda: 200.0, measure_after=lambda: 100.0
    )

    assert optimizer.total_improvement() == pytest.approx(80.0)


def test_get_summary_returns_expected_keys() -> None:
    """get_summary should return comprehensive optimization statistics."""
    optimizer = PerformanceOptimizer()

    s = optimizer.suggest_caching("test")
    optimizer.apply_optimization(
        s, measure_before=lambda: 100.0, measure_after=lambda: 50.0
    )

    summary = optimizer.get_summary()
    assert summary["total_suggestions"] >= 1
    assert summary["total_applied"] >= 1
    assert summary["total_improvement_pct"] == 50.0
    assert "by_type" in summary


def test_suggestion_summary_format() -> None:
    """OptimizationSuggestion.summary should return a readable string."""
    s = OptimizationSuggestion(
        name="cache_get_data",
        optimization_type=OptimizationType.CACHING,
        target_function="get_data",
        description="Cache data lookups",
        expected_improvement_pct=30.0,
    )
    summary = s.summary
    assert "[caching]" in summary
    assert "cache_get_data" in summary
    assert "+30%" in summary or "30%" in summary
