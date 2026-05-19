"""
Tests for heterogeneous model collaboration components.

Tests model routing, cross-model verification, prompt optimization,
cost optimization, and performance tracking.
"""

import pytest
from lyra_research.models import (
    ModelRouter,
    CrossModelVerifier,
    PromptOptimizer,
    CostOptimizer,
    ModelPerformanceTracker,
    ModelStats,
    VerificationResult,
)


# Model Router Tests
class TestModelRouter:
    """Tests for ModelRouter."""

    def test_route_discovery_role(self):
        """Test routing for discovery role."""
        router = ModelRouter()
        model = router.route("discovery", "medium")
        assert model == "claude-haiku-4-5"

    def test_route_analysis_role(self):
        """Test routing for analysis role."""
        router = ModelRouter()
        model = router.route("analysis", "medium")
        assert model == "claude-sonnet-4-6"

    def test_route_synthesis_role(self):
        """Test routing for synthesis role."""
        router = ModelRouter()
        model = router.route("synthesis", "medium")
        assert model == "claude-opus-4-7"

    def test_route_review_role(self):
        """Test routing for review role."""
        router = ModelRouter()
        model = router.route("review", "medium")
        assert model == "gpt-4o-mini"

    def test_route_curator_role(self):
        """Test routing for curator role."""
        router = ModelRouter()
        model = router.route("curator", "medium")
        assert model == "claude-opus-4-7"

    def test_route_with_low_complexity(self):
        """Test routing with low complexity override."""
        router = ModelRouter()
        model = router.route("analysis", "low")
        assert model == "claude-haiku-4-5"

    def test_route_with_high_complexity(self):
        """Test routing with high complexity override."""
        router = ModelRouter()
        model = router.route("discovery", "high")
        assert model == "claude-sonnet-4-6"

    def test_route_unknown_role_raises_error(self):
        """Test that unknown role raises ValueError."""
        router = ModelRouter()
        with pytest.raises(ValueError, match="Unknown role"):
            router.route("unknown_role")

    def test_get_fallback(self):
        """Test getting fallback model."""
        router = ModelRouter()
        fallback = router.get_fallback("discovery")
        assert fallback == "gpt-4o-mini"

    def test_get_fallback_unknown_role_raises_error(self):
        """Test that unknown role raises ValueError for fallback."""
        router = ModelRouter()
        with pytest.raises(ValueError, match="Unknown role"):
            router.get_fallback("unknown_role")

    def test_get_model_family_claude(self):
        """Test getting model family for Claude models."""
        router = ModelRouter()
        family = router.get_model_family("claude-sonnet-4-6")
        assert family == "claude"

    def test_get_model_family_gpt(self):
        """Test getting model family for GPT models."""
        router = ModelRouter()
        family = router.get_model_family("gpt-4o")
        assert family == "gpt"

    def test_get_model_family_unknown(self):
        """Test getting model family for unknown models."""
        router = ModelRouter()
        family = router.get_model_family("unknown-model")
        assert family == "unknown"

    def test_update_config(self):
        """Test updating model configuration."""
        router = ModelRouter()
        router.update_config("discovery", "gpt-4o", "claude-haiku-4-5")
        assert router.route("discovery") == "gpt-4o"
        assert router.get_fallback("discovery") == "claude-haiku-4-5"


# Cross-Model Verifier Tests
class TestCrossModelVerifier:
    """Tests for CrossModelVerifier."""

    def test_get_verification_model_for_claude(self):
        """Test getting verification model for Claude primary."""
        router = ModelRouter()
        verifier = CrossModelVerifier(router)
        verification_model = verifier.get_verification_model("claude-sonnet-4-6")
        assert verification_model == "gpt-4o"

    def test_get_verification_model_for_gpt(self):
        """Test getting verification model for GPT primary."""
        router = ModelRouter()
        verifier = CrossModelVerifier(router)
        verification_model = verifier.get_verification_model("gpt-4o")
        assert verification_model == "claude-sonnet-4-6"

    def test_get_verification_model_for_unknown(self):
        """Test getting verification model for unknown primary."""
        router = ModelRouter()
        verifier = CrossModelVerifier(router)
        verification_model = verifier.get_verification_model("unknown-model")
        assert verification_model == "claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_verify_with_different_model(self):
        """Test cross-model verification."""
        router = ModelRouter()
        verifier = CrossModelVerifier(router)
        result = await verifier.verify_with_different_model(
            result="test result",
            primary_model="claude-sonnet-4-6",
            verification_prompt="verify this"
        )
        assert isinstance(result, VerificationResult)
        assert result.verification_model == "gpt-4o"

    def test_create_verification_prompt(self):
        """Test creating verification prompt."""
        router = ModelRouter()
        verifier = CrossModelVerifier(router)
        prompt = verifier.create_verification_prompt(
            original_task="analyze data",
            result="analysis complete",
            verification_criteria=["accuracy", "completeness"]
        )
        assert "analyze data" in prompt
        assert "analysis complete" in prompt
        assert "accuracy" in prompt
        assert "completeness" in prompt

    def test_compare_results_identical(self):
        """Test comparing identical results."""
        router = ModelRouter()
        verifier = CrossModelVerifier(router)
        discrepancies = verifier.compare_results("result", "result")
        assert len(discrepancies) == 0

    def test_compare_results_different(self):
        """Test comparing different results."""
        router = ModelRouter()
        verifier = CrossModelVerifier(router)
        discrepancies = verifier.compare_results("result1", "result2")
        assert len(discrepancies) > 0


# Prompt Optimizer Tests
class TestPromptOptimizer:
    """Tests for PromptOptimizer."""

    def test_optimize_for_claude(self):
        """Test optimizing prompt for Claude."""
        optimizer = PromptOptimizer()
        optimized = optimizer.optimize_for_claude("test prompt")
        assert "<task>" in optimized
        assert "test prompt" in optimized
        assert "<instructions>" in optimized

    def test_optimize_for_gpt(self):
        """Test optimizing prompt for GPT."""
        optimizer = PromptOptimizer()
        optimized = optimizer.optimize_for_gpt("test prompt")
        assert "test prompt" in optimized
        assert "step-by-step" in optimized

    def test_optimize_for_model_claude(self):
        """Test auto-optimization for Claude model."""
        optimizer = PromptOptimizer()
        optimized = optimizer.optimize_for_model("test prompt", "claude-sonnet-4-6")
        assert "<task>" in optimized

    def test_optimize_for_model_gpt(self):
        """Test auto-optimization for GPT model."""
        optimizer = PromptOptimizer()
        optimized = optimizer.optimize_for_model("test prompt", "gpt-4o")
        assert "step-by-step" in optimized

    def test_optimize_for_model_unknown(self):
        """Test optimization for unknown model returns base prompt."""
        optimizer = PromptOptimizer()
        optimized = optimizer.optimize_for_model("test prompt", "unknown-model")
        assert optimized == "test prompt"

    def test_add_output_format_json_claude(self):
        """Test adding JSON format for Claude."""
        optimizer = PromptOptimizer()
        formatted = optimizer.add_output_format("test", "json", "claude-sonnet-4-6")
        assert "<output_format>JSON</output_format>" in formatted

    def test_add_output_format_json_gpt(self):
        """Test adding JSON format for GPT."""
        optimizer = PromptOptimizer()
        formatted = optimizer.add_output_format("test", "json", "gpt-4o")
        assert "json format" in formatted

    def test_add_examples_claude(self):
        """Test adding examples for Claude."""
        optimizer = PromptOptimizer()
        examples = [("input1", "output1"), ("input2", "output2")]
        with_examples = optimizer.add_examples("test", examples, "claude-sonnet-4-6")
        assert "<example>" in with_examples
        assert "input1" in with_examples
        assert "output1" in with_examples

    def test_add_examples_gpt(self):
        """Test adding examples for GPT."""
        optimizer = PromptOptimizer()
        examples = [("input1", "output1")]
        with_examples = optimizer.add_examples("test", examples, "gpt-4o")
        assert "Example 1" in with_examples
        assert "input1" in with_examples

    def test_add_examples_empty(self):
        """Test adding empty examples returns original prompt."""
        optimizer = PromptOptimizer()
        with_examples = optimizer.add_examples("test", [], "claude-sonnet-4-6")
        assert with_examples == "test"


# Cost Optimizer Tests
class TestCostOptimizer:
    """Tests for CostOptimizer."""

    def test_estimate_cost_haiku(self):
        """Test cost estimation for Haiku."""
        optimizer = CostOptimizer()
        cost = optimizer.estimate_cost("claude-haiku-4-5", 1_000_000, 1_000_000)
        assert cost == 1.5  # 0.25 + 1.25

    def test_estimate_cost_sonnet(self):
        """Test cost estimation for Sonnet."""
        optimizer = CostOptimizer()
        cost = optimizer.estimate_cost("claude-sonnet-4-6", 1_000_000, 1_000_000)
        assert cost == 18.0  # 3.0 + 15.0

    def test_estimate_cost_unknown_model_raises_error(self):
        """Test that unknown model raises ValueError."""
        optimizer = CostOptimizer()
        with pytest.raises(ValueError, match="Unknown model"):
            optimizer.estimate_cost("unknown-model", 1000, 1000)

    def test_recommend_model_high_quality(self):
        """Test recommending model with high quality requirement."""
        optimizer = CostOptimizer()
        model = optimizer.recommend_model("analysis", 1.0, 0.95)
        assert model in ["claude-opus-4-7", "claude-sonnet-4-6"]

    def test_recommend_model_low_budget(self):
        """Test recommending model with low budget."""
        optimizer = CostOptimizer()
        model = optimizer.recommend_model("discovery", 0.001, 0.7)
        assert model in ["gpt-4o-mini", "claude-haiku-4-5"]

    def test_recommend_model_impossible_quality(self):
        """Test recommending model when no model meets quality."""
        optimizer = CostOptimizer()
        model = optimizer.recommend_model("analysis", 1.0, 1.0)
        # Should return highest quality model
        assert model == "claude-opus-4-7"

    def test_compare_costs(self):
        """Test comparing costs across models."""
        optimizer = CostOptimizer()
        costs = optimizer.compare_costs(
            ["claude-haiku-4-5", "claude-sonnet-4-6"],
            10_000,
            2_000
        )
        assert "claude-haiku-4-5" in costs
        assert "claude-sonnet-4-6" in costs
        assert costs["claude-haiku-4-5"] < costs["claude-sonnet-4-6"]

    def test_get_cost_per_quality(self):
        """Test calculating cost per quality ratio."""
        optimizer = CostOptimizer()
        ratio = optimizer.get_cost_per_quality("claude-haiku-4-5")
        assert ratio > 0

    def test_get_cost_per_quality_unknown_model(self):
        """Test cost per quality for unknown model returns infinity."""
        optimizer = CostOptimizer()
        ratio = optimizer.get_cost_per_quality("unknown-model")
        assert ratio == float('inf')


# Performance Tracker Tests
class TestModelPerformanceTracker:
    """Tests for ModelPerformanceTracker."""

    def test_record_execution(self):
        """Test recording execution metrics."""
        tracker = ModelPerformanceTracker()
        tracker.record_execution(
            model="claude-sonnet-4-6",
            role="analysis",
            latency_ms=1000.0,
            quality_score=0.9,
            cost=0.01
        )
        stats = tracker.get_stats("claude-sonnet-4-6", "analysis")
        assert stats.execution_count == 1
        assert stats.avg_latency_ms == 1000.0
        assert stats.avg_quality_score == 0.9
        assert stats.avg_cost == 0.01

    def test_record_multiple_executions(self):
        """Test recording multiple executions updates averages."""
        tracker = ModelPerformanceTracker()
        tracker.record_execution("claude-sonnet-4-6", "analysis", 1000.0, 0.9, 0.01)
        tracker.record_execution("claude-sonnet-4-6", "analysis", 2000.0, 0.8, 0.02)
        stats = tracker.get_stats("claude-sonnet-4-6", "analysis")
        assert stats.execution_count == 2
        assert abs(stats.avg_latency_ms - 1500.0) < 0.01
        assert abs(stats.avg_quality_score - 0.85) < 0.01
        assert abs(stats.avg_cost - 0.015) < 0.0001

    def test_get_best_model_for_role(self):
        """Test getting best model for a role."""
        tracker = ModelPerformanceTracker()
        tracker.record_execution("claude-haiku-4-5", "discovery", 500.0, 0.8, 0.001)
        tracker.record_execution("claude-sonnet-4-6", "discovery", 1000.0, 0.9, 0.01)
        best = tracker.get_best_model_for_role("discovery")
        assert best in ["claude-haiku-4-5", "claude-sonnet-4-6"]

    def test_get_best_model_no_data_raises_error(self):
        """Test that no data raises ValueError."""
        tracker = ModelPerformanceTracker()
        with pytest.raises(ValueError, match="No performance data"):
            tracker.get_best_model_for_role("analysis")

    def test_compare_models(self):
        """Test comparing models for a role."""
        tracker = ModelPerformanceTracker()
        tracker.record_execution("claude-haiku-4-5", "discovery", 500.0, 0.8, 0.001)
        tracker.record_execution("claude-sonnet-4-6", "discovery", 1000.0, 0.9, 0.01)
        comparison = tracker.compare_models("discovery")
        assert "claude-haiku-4-5" in comparison
        assert "claude-sonnet-4-6" in comparison

    def test_get_stats_no_data_raises_error(self):
        """Test that getting stats with no data raises ValueError."""
        tracker = ModelPerformanceTracker()
        with pytest.raises(ValueError, match="No stats"):
            tracker.get_stats("claude-sonnet-4-6", "analysis")

    def test_get_all_stats(self):
        """Test getting all statistics."""
        tracker = ModelPerformanceTracker()
        tracker.record_execution("claude-haiku-4-5", "discovery", 500.0, 0.8, 0.001)
        all_stats = tracker.get_all_stats()
        assert len(all_stats) == 1
        assert ("claude-haiku-4-5", "discovery") in all_stats

    def test_reset_stats_all(self):
        """Test resetting all statistics."""
        tracker = ModelPerformanceTracker()
        tracker.record_execution("claude-haiku-4-5", "discovery", 500.0, 0.8, 0.001)
        tracker.reset_stats()
        assert len(tracker.get_all_stats()) == 0

    def test_reset_stats_specific_model(self):
        """Test resetting statistics for specific model."""
        tracker = ModelPerformanceTracker()
        tracker.record_execution("claude-haiku-4-5", "discovery", 500.0, 0.8, 0.001)
        tracker.record_execution("claude-sonnet-4-6", "analysis", 1000.0, 0.9, 0.01)
        tracker.reset_stats(model="claude-haiku-4-5")
        assert len(tracker.get_all_stats()) == 1
        assert ("claude-sonnet-4-6", "analysis") in tracker.get_all_stats()

    def test_reset_stats_specific_role(self):
        """Test resetting statistics for specific role."""
        tracker = ModelPerformanceTracker()
        tracker.record_execution("claude-haiku-4-5", "discovery", 500.0, 0.8, 0.001)
        tracker.record_execution("claude-sonnet-4-6", "analysis", 1000.0, 0.9, 0.01)
        tracker.reset_stats(role="discovery")
        assert len(tracker.get_all_stats()) == 1
        assert ("claude-sonnet-4-6", "analysis") in tracker.get_all_stats()
