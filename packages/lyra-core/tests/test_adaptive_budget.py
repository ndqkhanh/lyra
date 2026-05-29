"""
Tests for Adaptive Budget System
"""

import pytest
from lyra_core.adaptive_budget import (
    LayerType,
    LayerUsage,
    AdaptiveBudget,
    AdaptiveBudgetManager
)


class TestLayerUsage:
    """Test LayerUsage"""

    def test_initialization(self):
        """Test usage initialization"""
        usage = LayerUsage(layer=LayerType.SYSTEM)
        assert usage.layer == LayerType.SYSTEM
        assert usage.current_tokens == 0
        assert usage.access_count == 0

    def test_record_usage(self):
        """Test recording usage"""
        usage = LayerUsage(layer=LayerType.SYSTEM)
        usage.record_usage(100)

        assert usage.current_tokens == 100
        assert usage.peak_tokens == 100
        assert usage.access_count == 1

    def test_utilization(self):
        """Test utilization calculation"""
        usage = LayerUsage(layer=LayerType.SYSTEM)
        usage.record_usage(50)

        assert usage.get_utilization(100) == 0.5
        assert usage.get_utilization(200) == 0.25


class TestAdaptiveBudget:
    """Test AdaptiveBudget"""

    def test_initialization(self):
        """Test budget initialization"""
        budget = AdaptiveBudget(
            layer=LayerType.SYSTEM,
            initial_budget=1000,
            current_budget=1000,
            min_budget=500,
            max_budget=2000
        )
        assert budget.current_budget == 1000

    def test_adjust_within_bounds(self):
        """Test budget adjustment within bounds"""
        budget = AdaptiveBudget(
            layer=LayerType.SYSTEM,
            initial_budget=1000,
            current_budget=1000,
            min_budget=500,
            max_budget=2000
        )

        # Increase
        budget.adjust(500)
        assert budget.current_budget == 1500

        # Decrease
        budget.adjust(-300)
        assert budget.current_budget == 1200

    def test_adjust_bounds_enforcement(self):
        """Test budget bounds enforcement"""
        budget = AdaptiveBudget(
            layer=LayerType.SYSTEM,
            initial_budget=1000,
            current_budget=1000,
            min_budget=500,
            max_budget=2000
        )

        # Try to exceed max
        budget.adjust(2000)
        assert budget.current_budget == 2000  # Capped at max

        # Try to go below min
        budget.adjust(-2000)
        assert budget.current_budget == 500  # Capped at min


class TestAdaptiveBudgetManager:
    """Test AdaptiveBudgetManager"""

    def test_initialization(self):
        """Test manager initialization"""
        manager = AdaptiveBudgetManager(total_budget=100000)
        assert manager.total_budget == 100000
        assert len(manager.budgets) == 8  # 8 layers

    def test_record_usage(self):
        """Test recording usage"""
        manager = AdaptiveBudgetManager()
        manager.record_usage(LayerType.SYSTEM, 500)

        budget = manager.budgets[LayerType.SYSTEM]
        assert budget.usage.current_tokens == 500
        assert budget.usage.access_count == 1

    def test_rebalance_high_utilization(self):
        """Test rebalancing with high utilization"""
        manager = AdaptiveBudgetManager(total_budget=10000)

        # Simulate high utilization for SYSTEM layer
        system_budget = manager.budgets[LayerType.SYSTEM]
        for _ in range(10):
            manager.record_usage(LayerType.SYSTEM, int(system_budget.current_budget * 0.95))

        old_budget = system_budget.current_budget
        manager.rebalance()

        # Budget should increase
        assert system_budget.current_budget >= old_budget

    def test_rebalance_low_utilization(self):
        """Test rebalancing with low utilization"""
        manager = AdaptiveBudgetManager(total_budget=10000)

        # Simulate low utilization for DYNAMIC layer
        dynamic_budget = manager.budgets[LayerType.DYNAMIC]
        for _ in range(10):
            manager.record_usage(LayerType.DYNAMIC, int(dynamic_budget.current_budget * 0.1))

        old_budget = dynamic_budget.current_budget
        manager.rebalance()

        # Budget should decrease
        assert dynamic_budget.current_budget <= old_budget

    def test_get_stats(self):
        """Test statistics collection"""
        manager = AdaptiveBudgetManager()
        manager.record_usage(LayerType.SYSTEM, 500)
        manager.record_usage(LayerType.SESSION, 1000)

        stats = manager.get_stats()
        assert 'total_budget' in stats
        assert 'total_used' in stats
        assert 'layers' in stats
        assert stats['total_used'] == 1500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
