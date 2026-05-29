"""
Tests for token optimization module.
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from optimization.token_optimizer import (
    ContextCompressor,
    CostMetrics,
    LLMRequest,
    ModelSelector,
    ModelTier,
    OptimizedRequest,
    PromptCacheManager,
    TaskType,
    TokenOptimizer,
)


class TestTaskType:
    """Tests for TaskType enum."""

    def test_task_types(self):
        """Test all task types exist."""
        assert TaskType.CHAT.value == "chat"
        assert TaskType.TOOL_CALL.value == "tool_call"
        assert TaskType.SUMMARY.value == "summary"
        assert TaskType.PLANNING.value == "planning"
        assert TaskType.REASONING.value == "reasoning"
        assert TaskType.REVIEW.value == "review"
        assert TaskType.COMPLEX.value == "complex"
        assert TaskType.RESEARCH.value == "research"


class TestModelTier:
    """Tests for ModelTier enum."""

    def test_model_tiers(self):
        """Test all model tiers exist."""
        assert ModelTier.HAIKU.value == "haiku"
        assert ModelTier.SONNET.value == "sonnet"
        assert ModelTier.OPUS.value == "opus"


class TestLLMRequest:
    """Tests for LLMRequest dataclass."""

    def test_request_creation(self):
        """Test creating a request."""
        req = LLMRequest(
            prompt="Test prompt",
            task_type=TaskType.CHAT,
        )

        assert req.prompt == "Test prompt"
        assert req.task_type == TaskType.CHAT
        assert req.context == ""
        assert req.context_size == 0
        assert req.max_tokens is None
        assert req.cache_enabled is False

    def test_request_with_context(self):
        """Test request with context."""
        req = LLMRequest(
            prompt="Test",
            task_type=TaskType.PLANNING,
            context="Some context",
            context_size=1000,
        )

        assert req.context == "Some context"
        assert req.context_size == 1000


class TestOptimizedRequest:
    """Tests for OptimizedRequest dataclass."""

    def test_optimized_request_creation(self):
        """Test creating optimized request."""
        req = OptimizedRequest(
            model="claude-haiku-4.5",
            prompt="Test",
            context="Context",
            max_tokens=500,
            cache_enabled=True,
            estimated_cost=0.001,
            savings=0.005,
        )

        assert req.model == "claude-haiku-4.5"
        assert req.max_tokens == 500
        assert req.cache_enabled is True
        assert req.estimated_cost == 0.001
        assert req.savings == 0.005


class TestCostMetrics:
    """Tests for CostMetrics dataclass."""

    def test_metrics_creation(self):
        """Test creating metrics."""
        metrics = CostMetrics()

        assert metrics.total_tokens == 0
        assert metrics.input_tokens == 0
        assert metrics.output_tokens == 0
        assert metrics.cached_tokens == 0
        assert metrics.total_cost == 0.0
        assert metrics.estimated_savings == 0.0
        assert metrics.requests_count == 0

    def test_metrics_with_values(self):
        """Test metrics with values."""
        metrics = CostMetrics(
            total_tokens=1000,
            input_tokens=600,
            output_tokens=400,
            cached_tokens=200,
            total_cost=0.01,
            estimated_savings=0.05,
            requests_count=5,
        )

        assert metrics.total_tokens == 1000
        assert metrics.input_tokens == 600
        assert metrics.output_tokens == 400
        assert metrics.cached_tokens == 200
        assert metrics.total_cost == 0.01
        assert metrics.estimated_savings == 0.05
        assert metrics.requests_count == 5


class TestModelSelector:
    """Tests for ModelSelector."""

    def test_selector_creation(self):
        """Test creating model selector."""
        selector = ModelSelector()

        assert selector is not None
        assert len(selector.task_to_model) == 8

    def test_select_haiku_tasks(self):
        """Test selecting Haiku for cheap tasks."""
        selector = ModelSelector()

        assert selector.select_model(TaskType.CHAT) == "claude-haiku-4.5"
        assert selector.select_model(TaskType.TOOL_CALL) == "claude-haiku-4.5"
        assert selector.select_model(TaskType.SUMMARY) == "claude-haiku-4.5"

    def test_select_sonnet_tasks(self):
        """Test selecting Sonnet for reasoning tasks."""
        selector = ModelSelector()

        assert selector.select_model(TaskType.PLANNING) == "claude-sonnet-4.6"
        assert selector.select_model(TaskType.REASONING) == "claude-sonnet-4.6"
        assert selector.select_model(TaskType.REVIEW) == "claude-sonnet-4.6"

    def test_select_opus_tasks(self):
        """Test selecting Opus for complex tasks."""
        selector = ModelSelector()

        assert selector.select_model(TaskType.COMPLEX) == "claude-opus-4.7"
        assert selector.select_model(TaskType.RESEARCH) == "claude-opus-4.7"

    def test_estimate_cost_haiku(self):
        """Test cost estimation for Haiku."""
        selector = ModelSelector()

        cost = selector.estimate_cost(
            model="claude-haiku-4.5",
            input_tokens=1000,
            output_tokens=500,
        )

        # (1000 / 1M * 0.80) + (500 / 1M * 4.00)
        expected = 0.0008 + 0.002
        assert abs(cost - expected) < 0.0001

    def test_estimate_cost_sonnet(self):
        """Test cost estimation for Sonnet."""
        selector = ModelSelector()

        cost = selector.estimate_cost(
            model="claude-sonnet-4.6",
            input_tokens=1000,
            output_tokens=500,
        )

        # (1000 / 1M * 3.00) + (500 / 1M * 15.00)
        expected = 0.003 + 0.0075
        assert abs(cost - expected) < 0.0001

    def test_estimate_cost_opus(self):
        """Test cost estimation for Opus."""
        selector = ModelSelector()

        cost = selector.estimate_cost(
            model="claude-opus-4.7",
            input_tokens=1000,
            output_tokens=500,
        )

        # (1000 / 1M * 15.00) + (500 / 1M * 75.00)
        expected = 0.015 + 0.0375
        assert abs(cost - expected) < 0.0001

    def test_estimate_cost_with_cache(self):
        """Test cost estimation with caching."""
        selector = ModelSelector()

        cost = selector.estimate_cost(
            model="claude-sonnet-4.6",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=500,
        )

        # Cached tokens are 90% cheaper
        # effective_input = 1000 - (500 * 0.9) = 550
        # (550 / 1M * 3.00) + (500 / 1M * 15.00)
        expected = 0.00165 + 0.0075
        assert abs(cost - expected) < 0.0001


class TestContextCompressor:
    """Tests for ContextCompressor."""

    def test_compressor_creation(self):
        """Test creating compressor."""
        compressor = ContextCompressor()

        assert compressor.threshold == 8000

    def test_compressor_custom_threshold(self):
        """Test compressor with custom threshold."""
        compressor = ContextCompressor(threshold=5000)

        assert compressor.threshold == 5000

    def test_should_compress_below_threshold(self):
        """Test should not compress below threshold."""
        compressor = ContextCompressor(threshold=1000)

        assert not compressor.should_compress(500)
        assert not compressor.should_compress(1000)

    def test_should_compress_above_threshold(self):
        """Test should compress above threshold."""
        compressor = ContextCompressor(threshold=1000)

        assert compressor.should_compress(1001)
        assert compressor.should_compress(5000)

    def test_compress_small_context(self):
        """Test compressing small context (no change)."""
        compressor = ContextCompressor()

        context = "Small context"
        compressed = compressor.compress(context, target_size=1000)

        assert compressed == context

    def test_compress_large_context(self):
        """Test compressing large context."""
        compressor = ContextCompressor()

        # Create large context
        words = ["word"] * 10000
        context = " ".join(words)

        compressed = compressor.compress(context, target_size=1000)

        # Should be compressed
        assert len(compressed) < len(context)
        assert "[... context compressed ...]" in compressed

    def test_compress_keeps_start_and_end(self):
        """Test compression keeps start and end."""
        compressor = ContextCompressor()

        context = "START " + " ".join(["middle"] * 10000) + " END"
        compressed = compressor.compress(context, target_size=100)

        assert "START" in compressed
        assert "END" in compressed
        assert "[... context compressed ...]" in compressed


class TestPromptCacheManager:
    """Tests for PromptCacheManager."""

    def test_cache_manager_creation(self):
        """Test creating cache manager."""
        manager = PromptCacheManager()

        assert manager.cache_hits == 0
        assert manager.cache_misses == 0
        assert len(manager.cached_prompts) == 0

    def test_should_cache_small_context(self):
        """Test should not cache small context."""
        manager = PromptCacheManager()

        req = LLMRequest(
            prompt="Test",
            task_type=TaskType.CHAT,
            context_size=500,
        )

        assert not manager.should_cache(req)

    def test_should_cache_large_context(self):
        """Test should cache large context."""
        manager = PromptCacheManager()

        req = LLMRequest(
            prompt="Test",
            task_type=TaskType.CHAT,
            context_size=2000,
        )

        assert manager.should_cache(req)

    def test_cache_prompt(self):
        """Test caching a prompt."""
        manager = PromptCacheManager()

        prompt = "Test prompt"
        manager.cache_prompt(prompt)

        assert len(manager.cached_prompts) == 1
        assert manager.is_cached(prompt)

    def test_is_cached_false(self):
        """Test prompt not cached."""
        manager = PromptCacheManager()

        assert not manager.is_cached("Not cached")

    def test_cache_key_generation(self):
        """Test cache key generation."""
        manager = PromptCacheManager()

        key1 = manager.get_cache_key("prompt1")
        key2 = manager.get_cache_key("prompt2")
        key3 = manager.get_cache_key("prompt1")

        # Same prompt should have same key
        assert key1 == key3
        # Different prompts should have different keys
        assert key1 != key2

    def test_cache_hit_rate_no_requests(self):
        """Test cache hit rate with no requests."""
        manager = PromptCacheManager()

        assert manager.get_cache_hit_rate() == 0.0

    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        manager = PromptCacheManager()

        manager.cache_hits = 7
        manager.cache_misses = 3

        assert manager.get_cache_hit_rate() == 0.7


class TestTokenOptimizer:
    """Tests for TokenOptimizer."""

    def test_optimizer_creation(self):
        """Test creating optimizer."""
        optimizer = TokenOptimizer()

        assert optimizer.model_selector is not None
        assert optimizer.compressor is not None
        assert optimizer.cache_manager is not None
        assert optimizer.metrics is not None

    def test_optimize_chat_request(self):
        """Test optimizing chat request."""
        optimizer = TokenOptimizer()

        req = LLMRequest(
            prompt="Hello",
            task_type=TaskType.CHAT,
            context="Some context",
            context_size=500,
        )

        optimized = optimizer.optimize_request(req)

        assert optimized.model == "claude-haiku-4.5"
        assert optimized.max_tokens == 500
        assert optimized.estimated_cost > 0
        assert optimized.savings >= 0

    def test_optimize_planning_request(self):
        """Test optimizing planning request."""
        optimizer = TokenOptimizer()

        req = LLMRequest(
            prompt="Plan this feature",
            task_type=TaskType.PLANNING,
            context="Feature details",
            context_size=1000,
        )

        optimized = optimizer.optimize_request(req)

        assert optimized.model == "claude-sonnet-4.6"
        assert optimized.max_tokens == 1000

    def test_optimize_complex_request(self):
        """Test optimizing complex request."""
        optimizer = TokenOptimizer()

        req = LLMRequest(
            prompt="Solve complex problem",
            task_type=TaskType.COMPLEX,
            context="Problem details",
            context_size=2000,
        )

        optimized = optimizer.optimize_request(req)

        assert optimized.model == "claude-opus-4.7"
        assert optimized.max_tokens == 2000

    def test_optimize_with_large_context(self):
        """Test optimization with large context."""
        optimizer = TokenOptimizer()

        # Large context should be compressed
        large_context = " ".join(["word"] * 10000)
        req = LLMRequest(
            prompt="Test",
            task_type=TaskType.CHAT,
            context=large_context,
            context_size=10000,
        )

        optimized = optimizer.optimize_request(req)

        # Context should be compressed
        assert len(optimized.context) < len(large_context)

    def test_optimize_with_caching(self):
        """Test optimization with caching."""
        optimizer = TokenOptimizer()

        req = LLMRequest(
            prompt="Test",
            task_type=TaskType.CHAT,
            context="Large context",
            context_size=2000,
        )

        optimized = optimizer.optimize_request(req)

        # Should enable caching for large context
        assert optimized.cache_enabled is True

    def test_optimize_with_max_tokens(self):
        """Test optimization with explicit max_tokens."""
        optimizer = TokenOptimizer()

        req = LLMRequest(
            prompt="Test",
            task_type=TaskType.CHAT,
            max_tokens=300,
        )

        optimized = optimizer.optimize_request(req)

        # Should use provided max_tokens
        assert optimized.max_tokens == 300

    def test_track_usage(self):
        """Test tracking usage."""
        optimizer = TokenOptimizer()

        optimizer.track_usage(
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=200,
            cost=0.01,
        )

        metrics = optimizer.get_metrics()
        assert metrics.total_tokens == 1500
        assert metrics.input_tokens == 1000
        assert metrics.output_tokens == 500
        assert metrics.cached_tokens == 200
        assert metrics.total_cost == 0.01
        assert metrics.requests_count == 1

    def test_track_multiple_requests(self):
        """Test tracking multiple requests."""
        optimizer = TokenOptimizer()

        optimizer.track_usage(1000, 500, 100, 0.01)
        optimizer.track_usage(2000, 1000, 200, 0.02)

        metrics = optimizer.get_metrics()
        assert metrics.total_tokens == 4500
        assert metrics.input_tokens == 3000
        assert metrics.output_tokens == 1500
        assert metrics.cached_tokens == 300
        assert metrics.total_cost == 0.03
        assert metrics.requests_count == 2

    def test_get_savings_percentage_no_usage(self):
        """Test savings percentage with no usage."""
        optimizer = TokenOptimizer()

        assert optimizer.get_savings_percentage() == 0.0

    def test_get_savings_percentage_with_usage(self):
        """Test savings percentage with usage."""
        optimizer = TokenOptimizer()

        optimizer.track_usage(1000, 500, 0, 0.01)

        savings = optimizer.get_savings_percentage()
        # Should be around 65% (assuming 65% savings)
        assert 60 <= savings <= 70

    def test_reset_metrics(self):
        """Test resetting metrics."""
        optimizer = TokenOptimizer()

        optimizer.track_usage(1000, 500, 0, 0.01)
        optimizer.reset_metrics()

        metrics = optimizer.get_metrics()
        assert metrics.total_tokens == 0
        assert metrics.total_cost == 0.0
        assert metrics.requests_count == 0

    def test_estimate_tokens_needed(self):
        """Test estimating tokens needed."""
        optimizer = TokenOptimizer()

        # Test different task types
        chat_req = LLMRequest(prompt="Test", task_type=TaskType.CHAT)
        assert optimizer._estimate_tokens_needed(chat_req) == 500

        planning_req = LLMRequest(prompt="Test", task_type=TaskType.PLANNING)
        assert optimizer._estimate_tokens_needed(planning_req) == 1000

        complex_req = LLMRequest(prompt="Test", task_type=TaskType.COMPLEX)
        assert optimizer._estimate_tokens_needed(complex_req) == 2000


class TestTokenOptimizerIntegration:
    """Integration tests for token optimizer."""

    def test_full_optimization_workflow(self):
        """Test complete optimization workflow."""
        optimizer = TokenOptimizer()

        # Create request
        req = LLMRequest(
            prompt="Analyze this code",
            task_type=TaskType.REVIEW,
            context="Code to review",
            context_size=1500,
        )

        # Optimize
        optimized = optimizer.optimize_request(req)

        # Verify optimization
        assert optimized.model == "claude-sonnet-4.6"
        assert optimized.cache_enabled is True
        assert optimized.max_tokens == 600
        assert optimized.estimated_cost > 0
        assert optimized.savings >= 0

        # Track usage
        optimizer.track_usage(
            input_tokens=1500,
            output_tokens=600,
            cached_tokens=500,
            cost=optimized.estimated_cost,
        )

        # Verify metrics
        metrics = optimizer.get_metrics()
        assert metrics.requests_count == 1
        assert metrics.total_tokens == 2100

    def test_multiple_requests_workflow(self):
        """Test workflow with multiple requests."""
        optimizer = TokenOptimizer()

        requests = [
            LLMRequest(prompt="Chat", task_type=TaskType.CHAT, context_size=500),
            LLMRequest(
                prompt="Plan", task_type=TaskType.PLANNING, context_size=2000
            ),
            LLMRequest(
                prompt="Research", task_type=TaskType.RESEARCH, context_size=3000
            ),
        ]

        for req in requests:
            optimized = optimizer.optimize_request(req)
            optimizer.track_usage(
                input_tokens=req.context_size,
                output_tokens=optimized.max_tokens,
                cached_tokens=req.context_size // 2 if optimized.cache_enabled else 0,
                cost=optimized.estimated_cost,
            )

        metrics = optimizer.get_metrics()
        assert metrics.requests_count == 3
        assert metrics.total_cost > 0

    def test_cost_comparison(self):
        """Test cost comparison between models."""
        optimizer = TokenOptimizer()

        # Same request with different task types
        # Chat (Haiku)
        chat_req = LLMRequest(
            prompt="Test",
            task_type=TaskType.CHAT,
            context="Context",
            context_size=1000,
        )
        chat_opt = optimizer.optimize_request(chat_req)

        # Planning (Sonnet)
        plan_req = LLMRequest(
            prompt="Test",
            task_type=TaskType.PLANNING,
            context="Context",
            context_size=1000,
        )
        plan_opt = optimizer.optimize_request(plan_req)

        # Complex (Opus)
        complex_req = LLMRequest(
            prompt="Test",
            task_type=TaskType.COMPLEX,
            context="Context",
            context_size=1000,
        )
        complex_opt = optimizer.optimize_request(complex_req)

        # Haiku should be cheapest
        assert chat_opt.estimated_cost < plan_opt.estimated_cost
        assert plan_opt.estimated_cost < complex_opt.estimated_cost


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
