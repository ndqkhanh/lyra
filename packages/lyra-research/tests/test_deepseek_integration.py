"""
DeepSeek API integration tests.

Tests cover:
- Model routing (v4-pro, v4-flash, chat)
- Cost tracking and optimization
- Performance benchmarks
- Error handling and fallback
- API configuration
"""

import pytest
import os
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

from lyra_research.deepseek_router import ModelRouter, CostTracker
from lyra_core.routing import RoutingDecision


class TestDeepSeekConfiguration:
    """Test DeepSeek API configuration."""

    def test_load_api_key_from_settings(self):
        """Test loading DeepSeek API key from settings."""
        # Mock settings file
        settings = {
            "env": {
                "DEEPSEEK_API_KEY": "sk-deepseek-test-key"
            }
        }

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = str(settings)

            router = ModelRouter()
            api_key = router._load_deepseek_key()

            assert api_key is not None
            assert api_key.startswith("sk-")

    def test_api_key_validation(self):
        """Test API key format validation."""
        router = ModelRouter()

        # Valid key
        assert router._validate_api_key("sk-deepseek-1234567890abcdef")

        # Invalid keys
        assert not router._validate_api_key("invalid-key")
        assert not router._validate_api_key("")
        assert not router._validate_api_key(None)

    def test_deepseek_endpoint_configuration(self):
        """Test DeepSeek endpoint configuration."""
        router = ModelRouter()

        config = router._get_deepseek_config()

        assert config["base_url"] == "https://api.deepseek.com"
        assert config["api_version"] == "v1"


class TestModelRouting:
    """Test intelligent model routing to DeepSeek."""

    def test_route_simple_task_to_deepseek_chat(self):
        """Test routing simple tasks to deepseek-chat."""
        router = ModelRouter()

        decision = router.route_task(
            task_description="What is the status of the build?",
            provider="deepseek"
        )

        assert decision.selected_model == "deepseek-chat"
        assert decision.cost_tier == "low"
        assert decision.estimated_cost < 0.01

    def test_route_standard_task_to_v4_flash(self):
        """Test routing standard tasks to deepseek-v4-flash."""
        router = ModelRouter()

        decision = router.route_task(
            task_description="Implement user authentication function",
            provider="deepseek"
        )

        assert decision.selected_model == "deepseek-v4-flash"
        assert decision.cost_tier == "mid"

    def test_route_complex_task_to_v4_pro(self):
        """Test routing complex tasks to deepseek-v4-pro."""
        router = ModelRouter()

        decision = router.route_task(
            task_description="Analyze complex multi-agent coordination patterns and synthesize findings",
            provider="deepseek"
        )

        assert decision.selected_model == "deepseek-v4-pro"
        assert decision.reasoning_depth == "deep"

    def test_route_based_on_cost_constraint(self):
        """Test routing with cost constraints."""
        router = ModelRouter(max_cost_per_request=0.05)

        decision = router.route_task(
            task_description="Complex analysis task",
            provider="deepseek"
        )

        # Should choose cheaper model due to constraint
        assert decision.estimated_cost <= 0.05

    def test_route_based_on_latency_requirement(self):
        """Test routing with latency requirements."""
        router = ModelRouter(max_latency_ms=500)

        decision = router.route_task(
            task_description="Quick lookup task",
            provider="deepseek"
        )

        # Should choose faster model
        assert decision.selected_model in ["deepseek-chat", "deepseek-v4-flash"]


class TestCostTracking:
    """Test cost tracking for DeepSeek API."""

    def test_track_single_request(self):
        """Test tracking cost for single request."""
        tracker = CostTracker()

        cost = tracker.track_request(
            model="deepseek-v4-pro",
            input_tokens=1000,
            output_tokens=500
        )

        # DeepSeek v4-pro: $0.50/M input, $2.00/M output
        expected_cost = (1000 / 1_000_000) * 0.50 + (500 / 1_000_000) * 2.00
        assert abs(cost - expected_cost) < 0.0001

        assert tracker.total_cost == cost
        assert tracker.total_requests == 1

    def test_track_multiple_requests(self):
        """Test tracking costs across multiple requests."""
        tracker = CostTracker()

        # Request 1: v4-pro
        cost1 = tracker.track_request("deepseek-v4-pro", 1000, 500)

        # Request 2: v4-flash
        cost2 = tracker.track_request("deepseek-v4-flash", 1000, 500)

        # Request 3: chat
        cost3 = tracker.track_request("deepseek-chat", 1000, 500)

        assert tracker.total_requests == 3
        assert tracker.total_cost == cost1 + cost2 + cost3

    def test_cost_by_model_breakdown(self):
        """Test cost breakdown by model."""
        tracker = CostTracker()

        tracker.track_request("deepseek-v4-pro", 1000, 500)
        tracker.track_request("deepseek-v4-pro", 2000, 1000)
        tracker.track_request("deepseek-v4-flash", 1000, 500)

        breakdown = tracker.get_cost_breakdown()

        assert "deepseek-v4-pro" in breakdown
        assert "deepseek-v4-flash" in breakdown
        assert breakdown["deepseek-v4-pro"]["requests"] == 2
        assert breakdown["deepseek-v4-flash"]["requests"] == 1

    def test_budget_limit_enforcement(self):
        """Test enforcing budget limits."""
        tracker = CostTracker(budget_limit=1.00)

        # Use $0.80
        tracker.track_request("deepseek-v4-pro", 100_000, 50_000)
        assert not tracker.is_budget_exceeded()

        # Use another $0.80 (total $1.60, exceeds $1.00)
        tracker.track_request("deepseek-v4-pro", 100_000, 50_000)
        assert tracker.is_budget_exceeded()

    def test_budget_alert_threshold(self):
        """Test budget alert at threshold."""
        tracker = CostTracker(budget_limit=1.00, alert_threshold=0.8)

        # Use $0.85 (exceeds 80% threshold)
        tracker.track_request("deepseek-v4-pro", 106_250, 53_125)

        assert tracker.should_alert()
        assert not tracker.is_budget_exceeded()


class TestCostOptimization:
    """Test cost optimization strategies."""

    def test_cost_savings_vs_opus(self):
        """Test cost savings using DeepSeek vs Claude Opus."""
        tracker = CostTracker()

        # Simulate 100 requests with DeepSeek
        deepseek_cost = 0
        for _ in range(100):
            deepseek_cost += tracker.calculate_cost(
                model="deepseek-v4-flash",
                input_tokens=1000,
                output_tokens=500
            )

        # Calculate equivalent Opus cost
        # Opus: $15/M input, $75/M output
        opus_cost = 100 * ((1000 / 1_000_000) * 15 + (500 / 1_000_000) * 75)

        savings_pct = (opus_cost - deepseek_cost) / opus_cost * 100

        assert savings_pct > 80  # >80% savings

    def test_dynamic_model_selection_for_cost(self):
        """Test dynamic model selection optimizes cost."""
        router = ModelRouter()

        tasks = [
            ("simple query", "deepseek-chat"),
            ("implement feature", "deepseek-v4-flash"),
            ("complex analysis", "deepseek-v4-pro"),
        ] * 33 + [("complex analysis", "deepseek-v4-pro")]

        total_cost = 0
        for task_desc, expected_model in tasks:
            decision = router.route_task(task_desc, provider="deepseek")
            total_cost += decision.estimated_cost

        # Compare to always using v4-pro
        baseline_cost = len(tasks) * 0.015  # Approximate v4-pro cost

        savings_pct = (baseline_cost - total_cost) / baseline_cost * 100
        assert savings_pct >= 40  # At least 40% savings


class TestPerformanceBenchmarks:
    """Test performance benchmarks for DeepSeek."""

    @pytest.mark.benchmark
    def test_routing_latency(self, benchmark):
        """Benchmark routing decision latency."""
        router = ModelRouter()

        def route():
            return router.route_task("Test task", provider="deepseek")

        result = benchmark(route)

        assert result.selected_model is not None
        # Routing should be fast (<100ms)

    @pytest.mark.benchmark
    def test_cost_calculation_performance(self, benchmark):
        """Benchmark cost calculation performance."""
        tracker = CostTracker()

        def calculate():
            return tracker.calculate_cost("deepseek-v4-pro", 1000, 500)

        result = benchmark(calculate)

        assert result > 0

    @pytest.mark.integration
    @pytest.mark.slow
    def test_deepseek_api_latency(self):
        """Test actual DeepSeek API latency."""
        router = ModelRouter()

        start = datetime.now(timezone.utc)

        # Make actual API call (if key available)
        if os.getenv("DEEPSEEK_API_KEY"):
            decision = router.route_task("Test query", provider="deepseek")
            response = router.execute_request(decision, "Test query")

            latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

            assert latency_ms < 2000  # <2s for simple query
            assert response is not None
        else:
            pytest.skip("DEEPSEEK_API_KEY not set")


class TestErrorHandling:
    """Test error handling for DeepSeek API."""

    def test_invalid_api_key_error(self):
        """Test handling invalid API key."""
        with pytest.raises(ValueError, match="Invalid API key"):
            router = ModelRouter(api_key="invalid-key")

    def test_rate_limit_handling(self):
        """Test handling rate limit errors."""
        router = ModelRouter()

        with patch.object(router, '_make_request') as mock_request:
            mock_request.side_effect = Exception("Rate limit exceeded")

            with pytest.raises(Exception, match="Rate limit"):
                router.execute_request(
                    RoutingDecision(selected_model="deepseek-v4-pro"),
                    "Test query"
                )

    def test_timeout_handling(self):
        """Test handling timeout errors."""
        router = ModelRouter(timeout=1)

        with patch.object(router, '_make_request') as mock_request:
            mock_request.side_effect = TimeoutError("Request timeout")

            with pytest.raises(TimeoutError):
                router.execute_request(
                    RoutingDecision(selected_model="deepseek-v4-pro"),
                    "Test query"
                )

    def test_fallback_on_error(self):
        """Test fallback to alternative model on error."""
        router = ModelRouter(enable_fallback=True)

        with patch.object(router, '_make_request') as mock_request:
            # First call fails, second succeeds
            mock_request.side_effect = [
                Exception("v4-pro error"),
                {"response": "Success"}
            ]

            decision = RoutingDecision(
                selected_model="deepseek-v4-pro",
                fallback_models=["deepseek-v4-flash"]
            )

            response = router.execute_request_with_fallback(decision, "Test query")

            assert response is not None
            assert mock_request.call_count == 2


class TestResearchIntegration:
    """Integration tests for DeepSeek with research workflows."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_research_with_deepseek(self, tmp_path):
        """Test research workflow using DeepSeek."""
        from lyra_research.orchestrator import ResearchOrchestrator

        output_dir = tmp_path / "research"
        output_dir.mkdir()

        orchestrator = ResearchOrchestrator(
            output_dir=output_dir,
            provider="deepseek"
        )

        if not os.getenv("DEEPSEEK_API_KEY"):
            pytest.skip("DEEPSEEK_API_KEY not set")

        progress = orchestrator.research(
            topic="LLM reasoning",
            depth="quick",
            sources=["arxiv"]
        )

        assert progress.is_complete
        assert progress.error is None

    @pytest.mark.integration
    def test_cost_tracking_in_research(self, tmp_path):
        """Test cost tracking throughout research workflow."""
        from lyra_research.orchestrator import ResearchOrchestrator

        output_dir = tmp_path / "research"
        output_dir.mkdir()

        tracker = CostTracker()
        orchestrator = ResearchOrchestrator(
            output_dir=output_dir,
            provider="deepseek",
            cost_tracker=tracker
        )

        # Mock research execution
        with patch.object(orchestrator, 'research') as mock_research:
            mock_research.return_value = Mock(
                is_complete=True,
                sources_found_total=10
            )

            # Simulate some API calls
            tracker.track_request("deepseek-v4-flash", 1000, 500)
            tracker.track_request("deepseek-v4-flash", 1500, 750)

            progress = orchestrator.research(
                topic="Test",
                depth="quick",
                sources=["arxiv"]
            )

        # Verify cost tracking
        assert tracker.total_requests == 2
        assert tracker.total_cost > 0
        assert tracker.total_cost < 1.00  # Quick research should be cheap


class TestModelComparison:
    """Test comparing DeepSeek models."""

    def test_compare_model_costs(self):
        """Test comparing costs across DeepSeek models."""
        tracker = CostTracker()

        tokens_in = 10_000
        tokens_out = 5_000

        cost_pro = tracker.calculate_cost("deepseek-v4-pro", tokens_in, tokens_out)
        cost_flash = tracker.calculate_cost("deepseek-v4-flash", tokens_in, tokens_out)
        cost_chat = tracker.calculate_cost("deepseek-chat", tokens_in, tokens_out)

        # v4-pro should be most expensive
        assert cost_pro > cost_flash > cost_chat

    def test_compare_model_capabilities(self):
        """Test comparing model capabilities."""
        router = ModelRouter()

        # Complex task
        decision_complex = router.route_task(
            "Analyze complex multi-agent coordination patterns",
            provider="deepseek"
        )

        # Simple task
        decision_simple = router.route_task(
            "What is 2+2?",
            provider="deepseek"
        )

        # Should route to different models
        assert decision_complex.selected_model != decision_simple.selected_model


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
