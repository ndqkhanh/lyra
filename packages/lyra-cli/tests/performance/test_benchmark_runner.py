"""Tests for the BenchmarkRunner module."""

from __future__ import annotations

import time
from typing import Any

import pytest

from lyra_cli.performance.benchmark_runner import (
    BaselineComparison,
    BenchmarkCategory,
    BenchmarkConfig,
    BenchmarkRunner,
    BenchmarkStatus,
    _percentile,
)


def test_default_configs_created() -> None:
    """Runner should initialize with 8 default configs across 4 categories."""
    runner = BenchmarkRunner()
    assert len(runner.configs) == 8
    cats = {c.category for c in runner.configs}
    assert cats == {
        BenchmarkCategory.LATENCY,
        BenchmarkCategory.THROUGHPUT,
        BenchmarkCategory.MEMORY,
        BenchmarkCategory.TOKEN_EFFICIENCY,
    }


def test_run_all_executes_all_enabled() -> None:
    """run_all should return results for all configs without a benchmark_fn."""
    runner = BenchmarkRunner()
    results = runner.run_all()
    assert len(results) == 8
    for r in results:
        assert r.status == BenchmarkStatus.COMPLETE


def test_run_category_filters_correctly() -> None:
    """run_category should only run benchmarks of the given category."""
    runner = BenchmarkRunner()
    results = runner.run_category(BenchmarkCategory.LATENCY)
    assert len(results) == 2
    for r in results:
        assert r.config.category == BenchmarkCategory.LATENCY


def test_run_single_with_custom_fn() -> None:
    """run_single should execute a custom benchmark function and record metrics."""
    calls: list[float] = []

    def slow_fn() -> dict[str, Any]:
        time.sleep(0.005)
        calls.append(1)
        return {"result": "ok"}

    config = BenchmarkConfig(
        name="custom_test",
        category=BenchmarkCategory.LATENCY,
        benchmark_fn=slow_fn,
        iterations=3,
        warmup_iterations=1,
    )
    runner = BenchmarkRunner(configs=[config])
    result = runner.run_single(config)
    assert result.status == BenchmarkStatus.COMPLETE
    assert result.duration_seconds > 0
    assert f"custom_test_p50_ms" in result.metrics
    assert result.metrics[f"custom_test_p50_ms"] > 0


def test_run_single_handles_exception() -> None:
    """run_single should return FAILED status when benchmark_fn raises."""

    def broken_fn() -> dict[str, Any]:
        raise RuntimeError("benchmark crashed")

    config = BenchmarkConfig(
        name="broken",
        category=BenchmarkCategory.LATENCY,
        benchmark_fn=broken_fn,
        iterations=1,
        warmup_iterations=0,
    )
    runner = BenchmarkRunner(configs=[config])
    result = runner.run_single(config)
    assert result.status == BenchmarkStatus.FAILED
    assert "benchmark crashed" in (result.error_message or "")


def test_baseline_comparison_regression_detection() -> None:
    """BaselineComparison should correctly flag regressions over tolerance."""
    comparison = BaselineComparison(
        baseline_value=100.0,
        current_value=120.0,
        change_pct=20.0,
        regressed=True,
    )
    assert comparison.regressed
    assert comparison.change_pct == 20.0
    assert "regressed" in comparison.summary

    comparison_ok = BaselineComparison(
        baseline_value=100.0,
        current_value=95.0,
        change_pct=-5.0,
        regressed=False,
    )
    assert not comparison_ok.regressed
    assert "improved" in comparison_ok.summary


def test_detect_regressions_finds_regressed() -> None:
    """detect_regressions should return only results exceeding tolerance."""

    def fast_fn() -> dict[str, Any]:
        return {"ok": True}

    low_baseline = BenchmarkConfig(
        name="fast_bench",
        category=BenchmarkCategory.LATENCY,
        benchmark_fn=fast_fn,
        iterations=1,
        warmup_iterations=0,
        baseline_value=10.0,
        tolerance_pct=5.0,
    )
    runner = BenchmarkRunner(configs=[low_baseline])
    runner.run_all()
    regressed = runner.detect_regressions()
    assert isinstance(regressed, list)


def test_get_summary_structure() -> None:
    """get_summary should return expected keys."""
    runner = BenchmarkRunner()
    runner.run_all()
    summary = runner.get_summary()
    assert "total" in summary
    assert "completed" in summary
    assert "failed" in summary
    assert "regressed" in summary
    assert "by_category" in summary
    assert summary["total"] == 8
    assert summary["completed"] == 8


def test_export_results(tmp_path: Any) -> None:
    """export_results should write a valid JSON file."""
    import json

    runner = BenchmarkRunner()
    runner.run_all()
    out = tmp_path / "benchmarks.json"
    runner.export_results(str(out))
    assert out.exists()
    data = json.loads(out.read_text())
    assert "summary" in data
    assert "results" in data
    assert len(data["results"]) == 8


def test_percentile_edge_cases() -> None:
    """_percentile should handle edge cases correctly."""
    assert _percentile([], 50) == 0.0
    assert _percentile([5.0], 50) == 5.0
    assert _percentile([1.0, 2.0, 3.0], 50) == 2.0
    assert _percentile([1.0, 2.0, 3.0, 4.0], 50) == pytest.approx(2.5)
    assert _percentile([1.0, 2.0, 3.0, 4.0, 5.0], 95) == pytest.approx(4.8)
