"""
Simplified integration tests for DeepSeek API integration.

Tests cover:
- ModelRouter configuration and API key validation
- Model routing decisions based on task complexity
- Cost tracking for single and multiple requests
- Budget limit enforcement
- Cost optimization and savings calculations
- Error handling and fallback mechanisms
"""

import pytest
from unittest.mock import Mock, patch

from lyra_research.deepseek_router import ModelRouter, CostTracker, RoutingDecision


class TestModelRouterConfiguration:
    """Test ModelRouter configuration and initialization."""

    def test_router_initialization_without_api_key(self):
        """Test router can be initialized without API key."""
        router = ModelRouter()
        assert router.api_key is None
        assert router.max_cost_per_request is None
        assert router.timeout == 30

    def test_router_initialization_with_api_key(self):
        """Test router initialization with valid API key."""
        router = ModelRouter(api_key="sk-test-key-123")
        assert router.api_key == "sk-test-key-123"

    def test_router_rejects_invalid_api_key(self):
        """Test router rejects invalid API key format."""
        with pytest.raises(ValueError, match="Invalid API key"):
            ModelRouter(api_key="invalid-key")

    def test_router_with_cost_constraint(self):
        """Test router with cost constraint."""
        router = ModelRouter(max_cost_per_request=0.01)
        assert router.max_cost_per_request == 0.01

    def test_router_with_latency_constraint(self):
        """Test router with latency constraint."""
        router = ModelRouter(max_latency_ms=500)
        assert router.max_latency_ms == 500


class TestModelRouting:
    """Test model routing decisions based on task complexity."""

    def test_route_simple_task(self):
        """Test routing simple task to deepseek-chat."""
        router = ModelRouter()
        decision = router.route_task("What is the status?")

        assert decision.selected_model == "deepseek-chat"
        assert decision.cost_tier == "low"
        assert decision.reasoning_depth == "simple"
        assert decision.estimated_cost > 0

    def test_route_complex_task(self):
        """Test routing complex task to deepseek-v4-pro."""
        router = ModelRouter()
        decision = router.route_task(
            "Analyze the comprehensive implications of multi-agent systems "
            "in distributed computing environments with deep synthesis of "
            "recent research findings and complex architectural patterns."
        )

        assert decision.selected_model == "deepseek-v4-pro"
        assert decision.cost_tier == "high"
        assert decision.reasoning_depth == "deep"

    def test_route_standard_task(self):
        """Test routing standard task to deepseek-v4-flash."""
        router = ModelRouter()
        decision = router.route_task(
            "Explain the key differences between synchronous and "
            "asynchronous programming patterns."
        )

        assert decision.selected_model == "deepseek-v4-flash"
        assert decision.cost_tier == "mid"
        assert decision.reasoning_depth == "standard"

    def test_route_with_cost_constraint(self):
        """Test routing downgrades model when cost constraint exceeded."""
        router = ModelRouter(max_cost_per_request=0.0001)
        decision = router.route_task(
            "Analyze complex multi-agent coordination mechanisms."
        )

        # Should downgrade to cheapest model due to cost constraint
        assert decision.selected_model == "deepseek-chat"
        assert decision.cost_tier == "low"

    def test_route_with_latency_constraint(self):
        """Test routing considers latency constraints."""
        router = ModelRouter(max_latency_ms=400)
        decision = router.route_task(
            "Analyze complex multi-agent systems in depth."
        )

        # Should not use slowest model (v4-pro) due to latency constraint
        assert decision.selected_model in ["deepseek-v4-flash", "deepseek-chat"]

    def test_fallback_models_provided(self):
        """Test routing decision includes fallback models."""
        router = ModelRouter()
        decision = router.route_task("Analyze complex systems.")

        assert isinstance(decision.fallback_models, list)
        if decision.selected_model == "deepseek-v4-pro":
            assert "deepseek-v4-flash" in decision.fallback_models
            assert "deepseek-chat" in decision.fallback_models


class TestCostTracking:
    """Test cost tracking for DeepSeek API usage."""

    def test_tracker_initialization(self):
        """Test cost tracker initialization."""
        tracker = CostTracker()
        assert tracker.total_cost == 0.0
        assert tracker.total_requests == 0
        assert tracker.costs_by_model == {}

    def test_tracker_with_budget_limit(self):
        """Test tracker with budget limit."""
        tracker = CostTracker(budget_limit=10.0)
        assert tracker.budget_limit == 10.0
        assert tracker.alert_threshold == 0.8

    def test_track_single_request(self):
        """Test tracking single request cost."""
        tracker = CostTracker()
        cost = tracker.track_request(
            model="deepseek-chat",
            input_tokens=1000,
            output_tokens=500
        )

        assert cost > 0
        assert tracker.total_cost == cost
        assert tracker.total_requests == 1
        assert "deepseek-chat" in tracker.costs_by_model

    def test_track_multiple_requests(self):
        """Test tracking multiple requests."""
        tracker = CostTracker()

        cost1 = tracker.track_request("deepseek-chat", 1000, 500)
        cost2 = tracker.track_request("deepseek-v4-flash", 2000, 1000)
        cost3 = tracker.track_request("deepseek-chat", 1500, 750)

        assert tracker.total_cost == cost1 + cost2 + cost3
        assert tracker.total_requests == 3
        assert len(tracker.costs_by_model) == 2

    def test_cost_breakdown_by_model(self):
        """Test cost breakdown by model."""
        tracker = CostTracker()

        tracker.track_request("deepseek-chat", 1000, 500)
        tracker.track_request("deepseek-chat", 1000, 500)
        tracker.track_request("deepseek-v4-flash", 2000, 1000)

        breakdown = tracker.get_cost_breakdown()

        assert "deepseek-chat" in breakdown
        assert breakdown["deepseek-chat"]["requests"] == 2
        assert breakdown["deepseek-chat"]["input_tokens"] == 2000
        assert breakdown["deepseek-chat"]["output_tokens"] == 1000

        assert "deepseek-v4-flash" in breakdown
        assert breakdown["deepseek-v4-flash"]["requests"] == 1


class TestBudgetEnforcement:
    """Test budget limit enforcement."""

    def test_budget_not_exceeded_initially(self):
        """Test budget not exceeded initially."""
        tracker = CostTracker(budget_limit=10.0)
        assert not tracker.is_budget_exceeded()

    def test_budget_exceeded_detection(self):
        """Test budget exceeded detection."""
        tracker = CostTracker(budget_limit=0.001)

        # Track expensive request
        tracker.track_request("deepseek-v4-pro", 100000, 50000)

        assert tracker.is_budget_exceeded()

    def test_alert_threshold(self):
        """Test alert threshold detection."""
        tracker = CostTracker(budget_limit=0.1, alert_threshold=0.8)

        # Track requests up to 80% of budget (0.08)
        # deepseek-chat: $0.14/M input, $0.28/M output
        # Need ~286K input + 143K output to reach $0.08
        tracker.track_request("deepseek-chat", 286000, 143000)

        assert tracker.should_alert()
        assert not tracker.is_budget_exceeded()

    def test_no_alert_without_budget(self):
        """Test no alert when budget not set."""
        tracker = CostTracker()
        tracker.track_request("deepseek-chat", 1000000, 500000)

        assert not tracker.should_alert()
        assert not tracker.is_budget_exceeded()


class TestCostOptimization:
    """Test cost optimization and savings calculations."""

    def test_cost_calculation_accuracy(self):
        """Test cost calculation matches pricing."""
        tracker = CostTracker()

        # deepseek-chat: $0.14/M input, $0.28/M output
        cost = tracker.calculate_cost("deepseek-chat", 1_000_000, 1_000_000)
        expected = 0.14 + 0.28
        assert abs(cost - expected) < 0.001

    def test_model_cost_comparison(self):
        """Test cost comparison between models."""
        tracker = CostTracker()

        chat_cost = tracker.calculate_cost("deepseek-chat", 100000, 50000)
        flash_cost = tracker.calculate_cost("deepseek-v4-flash", 100000, 50000)
        pro_cost = tracker.calculate_cost("deepseek-v4-pro", 100000, 50000)

        # Verify pricing hierarchy
        assert chat_cost < flash_cost < pro_cost

    def test_savings_from_model_selection(self):
        """Test savings from selecting cheaper model."""
        router = ModelRouter()
        tracker = CostTracker()

        # Simple task routed to cheap model
        decision = router.route_task("What is the status?")
        cheap_cost = tracker.calculate_cost(
            decision.selected_model, 10000, 5000
        )

        # Cost if we used expensive model
        expensive_cost = tracker.calculate_cost("deepseek-v4-pro", 10000, 5000)

        savings = expensive_cost - cheap_cost
        assert savings > 0


class TestErrorHandling:
    """Test error handling and fallback mechanisms."""

    def test_execute_request_mock(self):
        """Test execute_request returns mock response."""
        router = ModelRouter()
        decision = RoutingDecision(
            selected_model="deepseek-chat",
            cost_tier="low",
            reasoning_depth="simple",
            estimated_cost=0.001,
        )

        response = router.execute_request(decision, "test query")
        assert "response" in response
        assert "deepseek-chat" in response["response"]

    def test_fallback_on_error(self):
        """Test fallback to alternative model on error."""
        router = ModelRouter(enable_fallback=True)
        decision = RoutingDecision(
            selected_model="deepseek-v4-pro",
            cost_tier="high",
            reasoning_depth="deep",
            estimated_cost=0.01,
            fallback_models=["deepseek-v4-flash", "deepseek-chat"],
        )

        # Mock execute_request to fail first time
        with patch.object(router, 'execute_request', side_effect=[Exception("API error"), {"response": "fallback"}]):
            response = router.execute_request_with_fallback(decision, "test query")
            assert response == {"response": "fallback"}

    def test_fallback_raises_when_no_fallbacks(self):
        """Test error raised when no fallback models available."""
        router = ModelRouter(enable_fallback=True)
        decision = RoutingDecision(
            selected_model="deepseek-chat",
            cost_tier="low",
            reasoning_depth="simple",
            estimated_cost=0.001,
            fallback_models=[],
        )

        with patch.object(router, 'execute_request', side_effect=Exception("API error")):
            with pytest.raises(Exception, match="API error"):
                router.execute_request_with_fallback(decision, "test query")


class TestIntegrationWorkflow:
    """Integration tests for complete routing + tracking workflow."""

    def test_route_and_track_workflow(self):
        """Test complete workflow: route task → track cost."""
        router = ModelRouter()
        tracker = CostTracker(budget_limit=1.0)

        # Route task
        decision = router.route_task("Explain multi-agent systems.")

        # Simulate request and track cost
        cost = tracker.track_request(
            model=decision.selected_model,
            input_tokens=5000,
            output_tokens=2500,
        )

        assert cost > 0
        assert tracker.total_requests == 1
        assert not tracker.is_budget_exceeded()

    def test_multiple_tasks_with_budget_tracking(self):
        """Test multiple tasks with budget tracking."""
        router = ModelRouter()
        tracker = CostTracker(budget_limit=0.1)

        tasks = [
            "What is the status?",
            "Explain the architecture.",
            "Analyze complex systems in depth.",
        ]

        for task in tasks:
            decision = router.route_task(task)
            tracker.track_request(decision.selected_model, 10000, 5000)

        assert tracker.total_requests == 3
        assert len(tracker.costs_by_model) >= 1

    def test_cost_optimization_workflow(self):
        """Test cost optimization across multiple requests."""
        router = ModelRouter(max_cost_per_request=0.0001)
        tracker = CostTracker()

        # All tasks should be routed to cheap model due to strict cost constraint
        tasks = [
            "What is status?",
            "Show list",
            "Quick check",
        ]

        for task in tasks:
            decision = router.route_task(task)
            # With very strict cost constraint, should use cheapest model
            assert decision.selected_model == "deepseek-chat"
            tracker.track_request(decision.selected_model, 5000, 2500)

        # Verify total cost is low
        assert tracker.total_cost < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
