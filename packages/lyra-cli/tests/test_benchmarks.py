"""Tests for Lyra Ultra Benchmarking System."""

import json
import os
import tempfile

from lyra_cli.benchmarks import (
    BenchmarkConfig,
    BenchmarkReport,
    BenchmarkResult,
    BenchmarkRunner,
    BenchmarkStatus,
    BenchmarkType,
)

# ============================================================================
# Configuration Tests
# ============================================================================

def test_benchmark_config_creation():
    """Test creating a benchmark configuration."""
    config = BenchmarkConfig(
        name="test_benchmark",
        benchmark_type=BenchmarkType.MEMORY,
        baseline_score=0.85,
        target_score=0.90,
    )

    assert config.name == "test_benchmark"
    assert config.benchmark_type == BenchmarkType.MEMORY
    assert config.enabled is True
    assert config.baseline_score == 0.85
    assert config.target_score == 0.90


# ============================================================================
# Result Tests
# ============================================================================

def test_benchmark_result_passed():
    """Test benchmark result pass detection."""
    config = BenchmarkConfig(
        name="test",
        benchmark_type=BenchmarkType.MEMORY,
        target_score=0.90,
    )

    result = BenchmarkResult(
        config=config,
        status=BenchmarkStatus.COMPLETE,
        score=0.95,
    )

    assert result.passed is True


def test_benchmark_result_failed():
    """Test benchmark result fail detection."""
    config = BenchmarkConfig(
        name="test",
        benchmark_type=BenchmarkType.MEMORY,
        target_score=0.90,
    )

    result = BenchmarkResult(
        config=config,
        status=BenchmarkStatus.COMPLETE,
        score=0.85,
    )

    assert result.passed is False


def test_benchmark_result_improvement_pct():
    """Test improvement percentage calculation."""
    config = BenchmarkConfig(
        name="test",
        benchmark_type=BenchmarkType.MEMORY,
    )

    result = BenchmarkResult(
        config=config,
        status=BenchmarkStatus.COMPLETE,
        score=0.95,
        baseline_score=0.85,
    )

    # (0.95 - 0.85) / 0.85 * 100 = 11.76%
    assert result.improvement_pct is not None
    assert abs(result.improvement_pct - 11.76) < 0.01


# ============================================================================
# Report Tests
# ============================================================================

def test_benchmark_report_summary():
    """Test benchmark report summary statistics."""
    config1 = BenchmarkConfig(
        name="test1",
        benchmark_type=BenchmarkType.MEMORY,
        target_score=0.90,
    )

    config2 = BenchmarkConfig(
        name="test2",
        benchmark_type=BenchmarkType.TASK,
        target_score=0.80,
    )

    results = [
        BenchmarkResult(
            config=config1,
            status=BenchmarkStatus.COMPLETE,
            score=0.95,
        ),
        BenchmarkResult(
            config=config2,
            status=BenchmarkStatus.COMPLETE,
            score=0.75,
        ),
    ]

    report = BenchmarkReport(
        results=results,
        total_duration_seconds=120.5,
    )

    assert report.total == 2
    assert report.passed == 1
    assert report.failed == 0
    assert report.pass_rate == 0.5


def test_benchmark_report_by_type():
    """Test grouping results by type."""
    config1 = BenchmarkConfig(
        name="memory1",
        benchmark_type=BenchmarkType.MEMORY,
    )

    config2 = BenchmarkConfig(
        name="memory2",
        benchmark_type=BenchmarkType.MEMORY,
    )

    config3 = BenchmarkConfig(
        name="task1",
        benchmark_type=BenchmarkType.TASK,
    )

    results = [
        BenchmarkResult(config=config1, status=BenchmarkStatus.COMPLETE),
        BenchmarkResult(config=config2, status=BenchmarkStatus.COMPLETE),
        BenchmarkResult(config=config3, status=BenchmarkStatus.COMPLETE),
    ]

    report = BenchmarkReport(results=results, total_duration_seconds=100)

    by_type = report.by_type()

    assert len(by_type[BenchmarkType.MEMORY]) == 2
    assert len(by_type[BenchmarkType.TASK]) == 1


def test_benchmark_report_to_dict():
    """Test exporting report to dictionary."""
    config = BenchmarkConfig(
        name="test",
        benchmark_type=BenchmarkType.MEMORY,
        target_score=0.90,
    )

    result = BenchmarkResult(
        config=config,
        status=BenchmarkStatus.COMPLETE,
        score=0.95,
    )

    report = BenchmarkReport(
        results=[result],
        total_duration_seconds=60.0,
    )

    data = report.to_dict()

    assert "summary" in data
    assert "by_type" in data
    assert "results" in data
    assert data["summary"]["total"] == 1
    assert data["summary"]["passed"] == 1


# ============================================================================
# Runner Tests
# ============================================================================

def test_benchmark_runner_initialization():
    """Test benchmark runner initialization."""
    runner = BenchmarkRunner()

    assert len(runner.configs) > 0
    assert len(runner.results) == 0


def test_benchmark_runner_has_all_benchmarks():
    """Test that runner has all required benchmarks."""
    runner = BenchmarkRunner()

    names = [c.name for c in runner.configs]

    # Memory benchmarks
    assert "memory_agent_bench_retrieval" in names
    assert "memory_agent_bench_learning" in names
    assert "memory_agent_bench_long_range" in names
    assert "memory_agent_bench_forgetting" in names
    assert "long_mem_eval" in names
    assert "locomo" in names

    # Task benchmarks
    assert "gaia" in names
    assert "swe_bench" in names
    assert "web_arena" in names
    assert "os_world" in names

    # Ablation studies
    assert "ablation_no_graph_memory" in names
    assert "ablation_no_verifier_gates" in names
    assert "ablation_no_experience_memory" in names
    assert "ablation_no_context_compression" in names
    assert "ablation_no_model_routing" in names
    assert "ablation_no_multi_agent" in names
    assert "ablation_no_multimodal" in names


def test_benchmark_runner_run_single():
    """Test running a single benchmark."""
    runner = BenchmarkRunner()

    config = runner.configs[0]
    result = runner.run_benchmark(config)

    assert result.config == config
    assert result.status in [BenchmarkStatus.COMPLETE, BenchmarkStatus.FAILED]
    assert result.duration_seconds >= 0


def test_benchmark_runner_run_all():
    """Test running all benchmarks."""
    runner = BenchmarkRunner()

    report = runner.run_all()

    assert report.total == len(runner.configs)
    assert report.total_duration_seconds >= 0
    assert len(report.results) == report.total


def test_benchmark_runner_memory_benchmark():
    """Test running memory benchmarks."""
    runner = BenchmarkRunner()

    config = BenchmarkConfig(
        name="test_memory",
        benchmark_type=BenchmarkType.MEMORY,
    )

    score, details = runner._run_memory_benchmark(config)

    assert score is not None
    assert isinstance(details, dict)


def test_benchmark_runner_task_benchmark():
    """Test running task benchmarks."""
    runner = BenchmarkRunner()

    config = BenchmarkConfig(
        name="gaia",
        benchmark_type=BenchmarkType.TASK,
    )

    score, details = runner._run_task_benchmark(config)

    assert score is not None
    assert isinstance(details, dict)


def test_benchmark_runner_ablation_study():
    """Test running ablation studies."""
    runner = BenchmarkRunner()

    config = BenchmarkConfig(
        name="ablation_no_graph_memory",
        benchmark_type=BenchmarkType.ABLATION,
        metadata={"component": "graph_memory"},
    )

    score, details = runner._run_ablation_study(config)

    assert score is not None
    assert score < 1.0  # Should show degradation
    assert "contribution_pct" in details


def test_benchmark_runner_export_report():
    """Test exporting report to file."""
    runner = BenchmarkRunner()

    config = BenchmarkConfig(
        name="test",
        benchmark_type=BenchmarkType.MEMORY,
    )

    result = BenchmarkResult(
        config=config,
        status=BenchmarkStatus.COMPLETE,
        score=0.95,
    )

    report = BenchmarkReport(
        results=[result],
        total_duration_seconds=60.0,
    )

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name

    try:
        runner.export_report(report, temp_path)

        assert os.path.exists(temp_path)

        with open(temp_path) as f:
            data = json.load(f)

        assert "summary" in data
        assert "results" in data

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_benchmark_workflow():
    """Test complete benchmark workflow."""
    runner = BenchmarkRunner()

    # Run all benchmarks
    report = runner.run_all()

    # Verify report
    assert report.total > 0
    assert report.total_duration_seconds >= 0

    # Export to file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name

    try:
        runner.export_report(report, temp_path)

        # Verify file
        with open(temp_path) as f:
            data = json.load(f)

        assert data["summary"]["total"] == report.total

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_benchmark_targets_are_achievable():
    """Test that benchmark targets are being met."""
    runner = BenchmarkRunner()
    report = runner.run_all()

    # Check that we're meeting targets
    completed = [r for r in report.results if r.status == BenchmarkStatus.COMPLETE]

    # Should have some passing benchmarks
    passed = [r for r in completed if r.passed]
    assert len(passed) > 0

    # Check specific high-priority benchmarks
    gaia = next((r for r in completed if r.config.name == "gaia"), None)
    if gaia and gaia.score:
        assert gaia.score >= 0.70  # At least baseline


def test_ablation_studies_show_contribution():
    """Test that ablation studies show component contribution."""
    runner = BenchmarkRunner()

    ablation_configs = [
        c for c in runner.configs
        if c.benchmark_type == BenchmarkType.ABLATION
    ]

    for config in ablation_configs:
        result = runner.run_benchmark(config)

        if result.status == BenchmarkStatus.COMPLETE and result.score:
            # Ablated score should be lower than baseline (1.0)
            assert result.score < 1.0

            # Should show at least 5% contribution
            degradation = 1.0 - result.score
            assert degradation >= 0.05


# ============================================================================
# Performance Tests
# ============================================================================

def test_benchmark_runner_performance():
    """Test that benchmark runner completes in reasonable time."""
    import time

    runner = BenchmarkRunner()

    start = time.time()
    report = runner.run_all()
    duration = time.time() - start

    # Should complete in under 10 seconds (placeholder benchmarks)
    assert duration < 10.0
    assert report.total_duration_seconds < 10.0


# ============================================================================
# Edge Cases
# ============================================================================

def test_benchmark_with_no_target():
    """Test benchmark without target score."""
    config = BenchmarkConfig(
        name="test",
        benchmark_type=BenchmarkType.MEMORY,
        target_score=None,
    )

    result = BenchmarkResult(
        config=config,
        status=BenchmarkStatus.COMPLETE,
        score=0.95,
    )

    # Should pass if no target
    assert result.passed is True


def test_benchmark_with_zero_baseline():
    """Test improvement calculation with zero baseline."""
    config = BenchmarkConfig(
        name="test",
        benchmark_type=BenchmarkType.MEMORY,
    )

    result = BenchmarkResult(
        config=config,
        status=BenchmarkStatus.COMPLETE,
        score=0.95,
        baseline_score=0.0,
    )

    # Should handle zero baseline gracefully
    assert result.improvement_pct is None


def test_skipped_benchmark():
    """Test skipped benchmark handling."""
    runner = BenchmarkRunner()

    # Disable a config
    runner.configs[0].enabled = False

    report = runner.run_all()

    # Should have at least one skipped
    assert report.skipped >= 1
