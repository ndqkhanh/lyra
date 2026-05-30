"""
Test suite for benchmark infrastructure.

Validates that all benchmark suites are properly configured and can execute.
"""

import sys
from pathlib import Path

import pytest

# Add benchmarks directory to path
sys.path.insert(0, str(Path(__file__).parent))

from benchmark_deep_research import DeepResearchBenchmark
from benchmark_auto_research import AutoResearchBenchmark
from benchmark_scientist_research import ScientistResearchBenchmark
from benchmark_ai_research import AIResearchBenchmark
from benchmark_comparison import BaselineComparisonBenchmark


def test_deep_research_benchmark_initialization(tmp_path: Path):
    """Test Deep Research benchmark can be initialized."""
    benchmark = DeepResearchBenchmark(output_dir=tmp_path)
    assert benchmark.output_dir == tmp_path
    assert benchmark.cost_tracker is not None
    assert benchmark.model_router is not None


def test_auto_research_benchmark_initialization(tmp_path: Path):
    """Test Auto Research benchmark can be initialized."""
    benchmark = AutoResearchBenchmark(output_dir=tmp_path)
    assert benchmark.output_dir == tmp_path
    assert benchmark.cost_tracker is not None


def test_scientist_research_benchmark_initialization(tmp_path: Path):
    """Test Scientist Research benchmark can be initialized."""
    benchmark = ScientistResearchBenchmark(output_dir=tmp_path)
    assert benchmark.output_dir == tmp_path
    assert benchmark.cost_tracker is not None


def test_ai_research_benchmark_initialization(tmp_path: Path):
    """Test AI Research benchmark can be initialized."""
    benchmark = AIResearchBenchmark(output_dir=tmp_path)
    assert benchmark.output_dir == tmp_path
    assert benchmark.cost_tracker is not None


def test_baseline_comparison_benchmark_initialization(tmp_path: Path):
    """Test Baseline Comparison benchmark can be initialized."""
    benchmark = BaselineComparisonBenchmark(output_dir=tmp_path)
    assert benchmark.output_dir == tmp_path
    assert benchmark.cost_tracker is not None


def test_benchmark_metrics_structure():
    """Test benchmark metrics have correct structure."""
    from benchmark_deep_research import BenchmarkMetrics, BenchmarkResult

    # Test BenchmarkMetrics
    metrics = BenchmarkMetrics(
        workflow_name="test",
        latency_seconds=1.0,
        token_usage={"input": 100, "output": 50},
        cost_usd=0.01,
        success=True,
        sources_processed=5,
        quality_score=0.85,
        error_count=0,
    )
    assert metrics.workflow_name == "test"
    assert metrics.latency_seconds == 1.0
    assert metrics.success is True

    # Test BenchmarkResult
    result = BenchmarkResult(
        workflow_name="test",
        runs=10,
        avg_latency=1.5,
        p50_latency=1.4,
        p95_latency=2.0,
        p99_latency=2.2,
        avg_cost=0.015,
        success_rate=0.95,
        avg_quality=0.88,
        total_errors=1,
    )
    assert result.runs == 10
    assert result.success_rate == 0.95


def test_cost_tracker_functionality():
    """Test cost tracker calculates costs correctly."""
    from lyra_research.deepseek_router import CostTracker

    tracker = CostTracker()

    # Track a request
    cost = tracker.track_request(
        model="deepseek-chat",
        input_tokens=1000,
        output_tokens=500,
    )

    assert cost > 0
    assert tracker.total_cost == cost
    assert tracker.total_requests == 1
    assert "deepseek-chat" in tracker.costs_by_model


def test_model_router_functionality():
    """Test model router routes tasks correctly."""
    from lyra_research.deepseek_router import ModelRouter

    router = ModelRouter()

    # Test simple task routing
    decision = router.route_task("What is the status?")
    assert decision.selected_model == "deepseek-chat"
    assert decision.cost_tier == "low"

    # Test complex task routing
    decision = router.route_task("Analyze and synthesize comprehensive research on multi-agent systems")
    assert decision.selected_model == "deepseek-v4-pro"
    assert decision.cost_tier == "high"


@pytest.mark.benchmark
def test_quick_benchmark_execution(tmp_path: Path):
    """Test that benchmarks can execute quickly (smoke test)."""
    benchmark = DeepResearchBenchmark(output_dir=tmp_path)

    # Run with just 1 iteration for smoke test
    result = benchmark.benchmark_simple_query(iterations=1)

    assert result.runs == 1
    assert result.avg_latency >= 0
    assert result.success_rate >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
