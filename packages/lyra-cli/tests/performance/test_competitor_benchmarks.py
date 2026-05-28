"""Tests for the CompetitorBenchmark module."""

from __future__ import annotations

from lyra_cli.performance.competitor_benchmarks import (
    BenchmarkComparison,
    BenchmarkDimension,
    CompetitorBenchmark,
    CompetitorName,
    CompetitorResult,
)


def test_benchmark_task_completion() -> None:
    """benchmark_task_completion should create comparison with 3 competitors."""
    bench = CompetitorBenchmark()
    comparison = bench.benchmark_task_completion(
        "code_gen", lyra_time=10.0, claude_time=15.0, hermes_time=20.0
    )
    assert len(comparison.results) == 3
    names = {r.competitor for r in comparison.results}
    assert names == {CompetitorName.LYRA, CompetitorName.CLAUDE_CODE, CompetitorName.HERMES_AGENT}


def test_benchmark_token_efficiency() -> None:
    """benchmark_token_efficiency should use ratio values."""
    bench = CompetitorBenchmark()
    comparison = bench.benchmark_token_efficiency(
        "review", lyra_ratio=0.9, claude_ratio=0.8, hermes_ratio=0.7
    )
    lyra = [r for r in comparison.results if r.competitor == CompetitorName.LYRA][0]
    assert lyra.dimension == BenchmarkDimension.TOKEN_EFFICIENCY
    assert lyra.value == 0.9
    assert lyra.unit == "ratio"


def test_benchmark_tool_call_latency() -> None:
    """benchmark_tool_call_latency should use ms values."""
    bench = CompetitorBenchmark()
    comparison = bench.benchmark_tool_call_latency(
        "read_file", lyra_ms=45.0, claude_ms=62.0, hermes_ms=80.0
    )
    lyra = [r for r in comparison.results if r.competitor == CompetitorName.LYRA][0]
    assert lyra.value == 45.0
    assert lyra.unit == "ms"


def test_benchmark_memory_usage() -> None:
    """benchmark_memory_usage should use MB values."""
    bench = CompetitorBenchmark()
    comparison = bench.benchmark_memory_usage(
        "session", lyra_mb=128.0, claude_mb=185.0, hermes_mb=220.0
    )
    lyra = [r for r in comparison.results if r.competitor == CompetitorName.LYRA][0]
    assert lyra.value == 128.0
    assert lyra.unit == "MB"


def test_comparison_best_and_worst() -> None:
    """BenchmarkComparison should correctly identify best and worst."""
    results = [
        CompetitorResult(CompetitorName.LYRA, BenchmarkDimension.TASK_COMPLETION_TIME, 10.0),
        CompetitorResult(CompetitorName.CLAUDE_CODE, BenchmarkDimension.TASK_COMPLETION_TIME, 15.0),
        CompetitorResult(CompetitorName.HERMES_AGENT, BenchmarkDimension.TASK_COMPLETION_TIME, 20.0),
    ]
    comparison = BenchmarkComparison(
        dimension=BenchmarkDimension.TASK_COMPLETION_TIME,
        results=results,
    )
    assert comparison.best is not None
    assert comparison.best.competitor == CompetitorName.LYRA
    assert comparison.worst is not None
    assert comparison.worst.competitor == CompetitorName.HERMES_AGENT


def test_comparison_ranking() -> None:
    """ranking should sort best-to-worst (lowest first)."""
    results = [
        CompetitorResult(CompetitorName.HERMES_AGENT, BenchmarkDimension.TASK_COMPLETION_TIME, 20.0),
        CompetitorResult(CompetitorName.LYRA, BenchmarkDimension.TASK_COMPLETION_TIME, 10.0),
        CompetitorResult(CompetitorName.CLAUDE_CODE, BenchmarkDimension.TASK_COMPLETION_TIME, 15.0),
    ]
    comparison = BenchmarkComparison(
        dimension=BenchmarkDimension.TASK_COMPLETION_TIME,
        results=results,
    )
    ranking = comparison.ranking
    assert ranking[0].competitor == CompetitorName.LYRA
    assert ranking[1].competitor == CompetitorName.CLAUDE_CODE
    assert ranking[2].competitor == CompetitorName.HERMES_AGENT


def test_advantage_vs_computes_percentage() -> None:
    """advantage_vs should calculate Lyra's advantage over a competitor."""
    results = [
        CompetitorResult(CompetitorName.LYRA, BenchmarkDimension.TASK_COMPLETION_TIME, 10.0),
        CompetitorResult(CompetitorName.CLAUDE_CODE, BenchmarkDimension.TASK_COMPLETION_TIME, 20.0),
    ]
    comparison = BenchmarkComparison(
        dimension=BenchmarkDimension.TASK_COMPLETION_TIME,
        results=results,
    )
    adv = comparison.advantage_vs(CompetitorName.CLAUDE_CODE)
    assert adv["advantage_pct"] == 50.0


def test_advantage_vs_missing_lyra_returns_zero() -> None:
    """advantage_vs should return 0 when Lyra result is missing."""
    results = [
        CompetitorResult(CompetitorName.CLAUDE_CODE, BenchmarkDimension.TASK_COMPLETION_TIME, 20.0),
    ]
    comparison = BenchmarkComparison(
        dimension=BenchmarkDimension.TASK_COMPLETION_TIME,
        results=results,
    )
    adv = comparison.advantage_vs(CompetitorName.CLAUDE_CODE)
    assert adv["advantage_pct"] == 0.0


def test_run_all_default() -> None:
    """run_all should produce 4 default comparisons."""
    bench = CompetitorBenchmark()
    comparisons = bench.run_all()
    assert len(comparisons) == 4
    dims = {c.dimension for c in comparisons}
    assert dims == set(BenchmarkDimension)


def test_competitor_result_formatted() -> None:
    """CompetitorResult.formatted should produce readable output."""
    result = CompetitorResult(
        CompetitorName.LYRA, BenchmarkDimension.MEMORY_USAGE, 128.0, unit="MB"
    )
    formatted = result.formatted
    assert "Lyra" in formatted
    assert "128.00" in formatted
    assert "MB" in formatted


def test_advantage_summary_structure() -> None:
    """advantage_summary should return nested dict with expected keys."""
    bench = CompetitorBenchmark()
    bench.run_all()
    summary = bench.advantage_summary()
    for comp_name in ["Claude Code", "Hermes Agent"]:
        assert comp_name in summary
        for dim in BenchmarkDimension:
            assert dim.value in summary[comp_name]
