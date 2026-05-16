"""Tests for Phase 7 & 8 Evaluation modules."""

import pytest

from lyra_cli.evaluation import (
    BenchmarkFramework,
    InnovationEngine,
)


# ============================================================================
# Benchmark Tests
# ============================================================================

@pytest.fixture
def benchmark_framework():
    """Create benchmark framework."""
    return BenchmarkFramework()


def test_benchmark_run(benchmark_framework):
    """Test running a benchmark."""
    result = benchmark_framework.run_benchmark("test_benchmark")

    assert result.benchmark_name == "test_benchmark"
    assert result.score > 0
    assert benchmark_framework.stats["total_benchmarks"] == 1


def test_benchmark_metrics(benchmark_framework):
    """Test benchmark metrics collection."""
    result = benchmark_framework.run_benchmark("test_benchmark")

    assert "accuracy" in result.metrics
    assert "latency_ms" in result.metrics
    assert "throughput" in result.metrics


def test_ablation_study(benchmark_framework):
    """Test ablation study."""
    study = benchmark_framework.run_ablation_study(
        study_name="test_study",
        baseline_config={"feature_a": True},
        variants={
            "no_feature_a": {"feature_a": False},
        }
    )

    assert study.study_name == "test_study"
    assert study.baseline_score > 0
    assert len(study.variant_scores) > 0


def test_benchmark_summary(benchmark_framework):
    """Test benchmark summary."""
    benchmark_framework.run_benchmark("test1")
    benchmark_framework.run_benchmark("test2")

    summary = benchmark_framework.get_benchmark_summary()

    assert summary["total_benchmarks"] == 2
    assert summary["avg_score"] > 0


def test_benchmark_export(benchmark_framework):
    """Test exporting benchmark results."""
    benchmark_framework.run_benchmark("test_benchmark")

    exported = benchmark_framework.export_results()

    assert "results" in exported
    assert "summary" in exported
    assert len(exported["results"]) == 1


# ============================================================================
# Innovation Tests
# ============================================================================

@pytest.fixture
def innovation_engine():
    """Create innovation engine."""
    return InnovationEngine()


def test_innovation_register(innovation_engine):
    """Test registering an innovation."""
    innov_id = innovation_engine.register_innovation(
        name="Mermaid Canvas",
        description="Visual diagram integration",
        category="visualization"
    )

    assert innov_id is not None
    assert innovation_engine.stats["total_innovations"] == 1


def test_innovation_get_all(innovation_engine):
    """Test getting all innovations."""
    innovation_engine.register_innovation(
        "Feature 1", "Description 1", "category1"
    )
    innovation_engine.register_innovation(
        "Feature 2", "Description 2", "category2"
    )

    innovations = innovation_engine.get_innovations()

    assert len(innovations) == 2


def test_innovation_export(innovation_engine):
    """Test exporting innovations."""
    innovation_engine.register_innovation(
        "Test Innovation", "Test Description", "test"
    )

    exported = innovation_engine.export_innovations()

    assert "innovations" in exported
    assert "stats" in exported
    assert len(exported["innovations"]) == 1
