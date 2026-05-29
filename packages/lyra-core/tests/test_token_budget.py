"""
Tests for Token Budget Manager
"""

import pytest
from lyra_core.token_budget import (
    BudgetLayer,
    BudgetAllocation,
    TokenBudgetManager,
    DynamicBudgetManager
)


class TestBudgetAllocation:
    """Test BudgetAllocation"""

    def test_initialization(self):
        """Test allocation initialization"""
        alloc = BudgetAllocation(
            layer=BudgetLayer.WORKING,
            allocated=1000
        )
        assert alloc.allocated == 1000
        assert alloc.used == 0

    def test_available(self):
        """Test available calculation"""
        alloc = BudgetAllocation(
            layer=BudgetLayer.WORKING,
            allocated=1000,
            used=300,
            reserved=200
        )
        assert alloc.available == 500

    def test_utilization(self):
        """Test utilization calculation"""
        alloc = BudgetAllocation(
            layer=BudgetLayer.WORKING,
            allocated=1000,
            used=500
        )
        assert alloc.utilization == 0.5


class TestTokenBudgetManager:
    """Test TokenBudgetManager"""

    def test_initialization(self):
        """Test manager initialization"""
        manager = TokenBudgetManager(total_budget=10000)
        assert manager.total_budget == 10000
        assert len(manager.allocations) == 5

    def test_allocate(self):
        """Test token allocation"""
        manager = TokenBudgetManager()
        success = manager.allocate(BudgetLayer.WORKING, 1000)
        assert success is True

        alloc = manager.get_allocation(BudgetLayer.WORKING)
        assert alloc.used == 1000

    def test_allocate_exceeds_budget(self):
        """Test allocation exceeding budget"""
        manager = TokenBudgetManager(total_budget=1000)
        # Try to allocate more than available
        success = manager.allocate(BudgetLayer.WORKING, 10000)
        assert success is False

    def test_reserve(self):
        """Test token reservation"""
        manager = TokenBudgetManager()
        success = manager.reserve(BudgetLayer.WORKING, 500)
        assert success is True

        alloc = manager.get_allocation(BudgetLayer.WORKING)
        assert alloc.reserved == 500

    def test_release(self):
        """Test token release"""
        manager = TokenBudgetManager()
        manager.allocate(BudgetLayer.WORKING, 1000)
        manager.release(BudgetLayer.WORKING, 500)

        alloc = manager.get_allocation(BudgetLayer.WORKING)
        assert alloc.used == 500

    def test_release_reservation(self):
        """Test reservation release"""
        manager = TokenBudgetManager()
        manager.reserve(BudgetLayer.WORKING, 500)
        manager.release_reservation(BudgetLayer.WORKING, 200)

        alloc = manager.get_allocation(BudgetLayer.WORKING)
        assert alloc.reserved == 300

    def test_get_total_used(self):
        """Test total used calculation"""
        manager = TokenBudgetManager()
        manager.allocate(BudgetLayer.WORKING, 1000)
        manager.allocate(BudgetLayer.SEMANTIC, 500)

        assert manager.get_total_used() == 1500

    def test_get_utilization(self):
        """Test utilization calculation"""
        manager = TokenBudgetManager(total_budget=10000)
        # Allocate within the layer's budget
        working_alloc = manager.get_allocation(BudgetLayer.WORKING)
        manager.allocate(BudgetLayer.WORKING, working_alloc.allocated)

        util = manager.get_utilization()
        # Should be 30% (working layer gets 30% of total)
        assert util > 0.25 and util < 0.35

    def test_rebalance(self):
        """Test budget rebalancing"""
        manager = TokenBudgetManager()

        # Create high utilization in one layer
        working_alloc = manager.get_allocation(BudgetLayer.WORKING)
        manager.allocate(BudgetLayer.WORKING, int(working_alloc.allocated * 0.9))

        old_allocated = working_alloc.allocated
        manager.rebalance()

        # High utilization layer should get more budget
        assert working_alloc.allocated > old_allocated

    def test_get_stats(self):
        """Test statistics"""
        manager = TokenBudgetManager()
        manager.allocate(BudgetLayer.WORKING, 1000)

        stats = manager.get_stats()
        assert 'total_budget' in stats
        assert 'total_used' in stats
        assert 'layers' in stats

    def test_check_alerts(self):
        """Test alert checking"""
        manager = TokenBudgetManager(total_budget=1000)

        # Use most of the budget
        for layer in BudgetLayer:
            alloc = manager.get_allocation(layer)
            manager.allocate(layer, int(alloc.allocated * 0.96))

        alerts = manager.check_alerts()
        assert len(alerts) > 0


class TestDynamicBudgetManager:
    """Test DynamicBudgetManager"""

    def test_initialization(self):
        """Test manager initialization"""
        manager = DynamicBudgetManager()
        assert len(manager.usage_history) == 5

    def test_usage_tracking(self):
        """Test usage history tracking"""
        manager = DynamicBudgetManager()
        manager.allocate(BudgetLayer.WORKING, 1000)
        manager.allocate(BudgetLayer.WORKING, 500)

        history = manager.usage_history[BudgetLayer.WORKING]
        assert len(history) == 2
        assert history[0] == 1000
        assert history[1] == 500

    def test_get_average_usage(self):
        """Test average usage calculation"""
        manager = DynamicBudgetManager()
        manager.allocate(BudgetLayer.WORKING, 1000)
        manager.allocate(BudgetLayer.WORKING, 2000)

        avg = manager.get_average_usage(BudgetLayer.WORKING)
        assert avg == 1500

    def test_auto_adjust(self):
        """Test automatic adjustment"""
        manager = DynamicBudgetManager()

        # Simulate high usage
        working_alloc = manager.get_allocation(BudgetLayer.WORKING)
        for _ in range(10):
            manager.allocate(BudgetLayer.WORKING, int(working_alloc.allocated * 0.85))
            manager.release(BudgetLayer.WORKING, int(working_alloc.allocated * 0.85))

        old_allocated = working_alloc.allocated
        manager.auto_adjust()

        # Should increase allocation due to high usage
        assert working_alloc.allocated > old_allocated


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
