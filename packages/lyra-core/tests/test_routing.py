"""
Tests for Model Router
"""

import pytest
from lyra_core.routing import (
    ModelRouter,
    ModelTier,
    TaskComplexity,
    RoutingDecision
)


class TestModelRouter:
    """Test Model Router functionality"""

    def test_initialization(self):
        """Test router initialization"""
        router = ModelRouter()
        assert len(router.models) == 3
        assert ModelTier.HAIKU in router.models
        assert ModelTier.SONNET in router.models
        assert ModelTier.OPUS in router.models

    def test_simple_task_routing(self):
        """Test routing for simple tasks"""
        router = ModelRouter()
        decision = router.route(TaskComplexity.SIMPLE)

        assert decision.model.tier == ModelTier.HAIKU
        assert decision.estimated_cost > 0
        assert decision.confidence > 0

    def test_moderate_task_routing(self):
        """Test routing for moderate tasks"""
        router = ModelRouter()
        decision = router.route(TaskComplexity.MODERATE)

        assert decision.model.tier == ModelTier.SONNET

    def test_complex_task_routing(self):
        """Test routing for complex tasks"""
        router = ModelRouter()
        decision = router.route(TaskComplexity.COMPLEX)

        assert decision.model.tier == ModelTier.OPUS

    def test_cost_constraint_routing(self):
        """Test routing with cost constraints"""
        router = ModelRouter()

        # Request expensive task with low budget
        decision = router.route(
            TaskComplexity.COMPLEX,
            estimated_tokens=10000,
            max_cost=5.0  # Low budget
        )

        # Should downgrade from Opus
        assert decision.model.tier in [ModelTier.SONNET, ModelTier.HAIKU]
        assert decision.estimated_cost <= 5.0

    def test_capability_routing(self):
        """Test routing based on required capabilities"""
        router = ModelRouter()

        decision = router.route(
            TaskComplexity.SIMPLE,
            required_capabilities=["reasoning"]
        )

        # Should upgrade from Haiku to model with reasoning
        assert decision.model.tier in [ModelTier.SONNET, ModelTier.OPUS]

    def test_routing_history(self):
        """Test routing history tracking"""
        router = ModelRouter()

        router.route(TaskComplexity.SIMPLE)
        router.route(TaskComplexity.MODERATE)
        router.route(TaskComplexity.COMPLEX)

        assert len(router.routing_history) == 3

    def test_routing_stats(self):
        """Test routing statistics"""
        router = ModelRouter()

        router.route(TaskComplexity.SIMPLE)
        router.route(TaskComplexity.MODERATE)

        stats = router.get_stats()
        assert stats['total_routes'] == 2
        assert 'by_model' in stats
        assert 'total_cost' in stats
        assert 'avg_cost' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
