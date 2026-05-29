"""
Token Budget Manager

Manages token budgets across different context layers.

Features:
- Layer-based budget allocation
- Dynamic budget adjustment
- Budget tracking and alerts
- Usage statistics
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class BudgetLayer(Enum):
    """Budget layers"""
    SYSTEM = "system"
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


@dataclass
class BudgetAllocation:
    """Budget allocation for a layer"""
    layer: BudgetLayer
    allocated: int
    used: int = 0
    reserved: int = 0

    @property
    def available(self) -> int:
        """Get available budget"""
        return self.allocated - self.used - self.reserved

    @property
    def utilization(self) -> float:
        """Get utilization percentage"""
        if self.allocated == 0:
            return 0.0
        return (self.used + self.reserved) / self.allocated


class TokenBudgetManager:
    """
    Token budget manager

    Manages token budgets across context layers.
    """

    def __init__(self, total_budget: int = 200000):
        self.total_budget = total_budget
        self.allocations: Dict[BudgetLayer, BudgetAllocation] = {}
        self._initialize_allocations()

    def _initialize_allocations(self):
        """Initialize default allocations"""
        # Default allocation percentages
        defaults = {
            BudgetLayer.SYSTEM: 0.10,      # 10% for system
            BudgetLayer.WORKING: 0.30,     # 30% for working memory
            BudgetLayer.EPISODIC: 0.25,    # 25% for episodic
            BudgetLayer.SEMANTIC: 0.25,    # 25% for semantic
            BudgetLayer.PROCEDURAL: 0.10   # 10% for procedural
        }

        for layer, percentage in defaults.items():
            allocated = int(self.total_budget * percentage)
            self.allocations[layer] = BudgetAllocation(
                layer=layer,
                allocated=allocated
            )

    def allocate(self, layer: BudgetLayer, tokens: int) -> bool:
        """Allocate tokens to a layer"""
        if layer not in self.allocations:
            return False

        allocation = self.allocations[layer]
        if allocation.available >= tokens:
            allocation.used += tokens
            return True
        return False

    def reserve(self, layer: BudgetLayer, tokens: int) -> bool:
        """Reserve tokens in a layer"""
        if layer not in self.allocations:
            return False

        allocation = self.allocations[layer]
        if allocation.available >= tokens:
            allocation.reserved += tokens
            return True
        return False

    def release(self, layer: BudgetLayer, tokens: int):
        """Release used tokens"""
        if layer in self.allocations:
            allocation = self.allocations[layer]
            allocation.used = max(0, allocation.used - tokens)

    def release_reservation(self, layer: BudgetLayer, tokens: int):
        """Release reserved tokens"""
        if layer in self.allocations:
            allocation = self.allocations[layer]
            allocation.reserved = max(0, allocation.reserved - tokens)

    def get_allocation(self, layer: BudgetLayer) -> Optional[BudgetAllocation]:
        """Get allocation for layer"""
        return self.allocations.get(layer)

    def get_total_used(self) -> int:
        """Get total tokens used"""
        return sum(a.used for a in self.allocations.values())

    def get_total_available(self) -> int:
        """Get total available tokens"""
        return sum(a.available for a in self.allocations.values())

    def get_utilization(self) -> float:
        """Get overall utilization"""
        total_used = self.get_total_used()
        return total_used / self.total_budget if self.total_budget > 0 else 0.0

    def rebalance(self):
        """Rebalance budgets based on usage"""
        # Calculate average utilization
        avg_util = sum(a.utilization for a in self.allocations.values()) / len(self.allocations)

        for layer, allocation in self.allocations.items():
            if allocation.utilization > avg_util * 1.5:
                # High utilization - increase budget
                increase = int(allocation.allocated * 0.1)
                allocation.allocated += increase
            elif allocation.utilization < avg_util * 0.5:
                # Low utilization - decrease budget
                decrease = int(allocation.allocated * 0.1)
                allocation.allocated = max(1000, allocation.allocated - decrease)

    def get_stats(self) -> Dict:
        """Get budget statistics"""
        return {
            'total_budget': self.total_budget,
            'total_used': self.get_total_used(),
            'total_available': self.get_total_available(),
            'utilization': self.get_utilization(),
            'layers': {
                layer.value: {
                    'allocated': alloc.allocated,
                    'used': alloc.used,
                    'reserved': alloc.reserved,
                    'available': alloc.available,
                    'utilization': alloc.utilization
                }
                for layer, alloc in self.allocations.items()
            }
        }

    def check_alerts(self) -> List[str]:
        """Check for budget alerts"""
        alerts = []

        # Overall budget alert
        if self.get_utilization() > 0.9:
            alerts.append("Overall budget utilization above 90%")

        # Layer-specific alerts
        for layer, allocation in self.allocations.items():
            if allocation.utilization > 0.95:
                alerts.append(f"{layer.value} layer utilization above 95%")
            elif allocation.available < 1000:
                alerts.append(f"{layer.value} layer has less than 1000 tokens available")

        return alerts


class DynamicBudgetManager(TokenBudgetManager):
    """
    Dynamic budget manager

    Automatically adjusts budgets based on usage patterns.
    """

    def __init__(self, total_budget: int = 200000):
        super().__init__(total_budget)
        self.usage_history: Dict[BudgetLayer, List[int]] = {
            layer: [] for layer in BudgetLayer
        }

    def allocate(self, layer: BudgetLayer, tokens: int) -> bool:
        """Allocate tokens and track usage"""
        success = super().allocate(layer, tokens)
        if success:
            self.usage_history[layer].append(tokens)
            # Keep only recent history
            if len(self.usage_history[layer]) > 100:
                self.usage_history[layer].pop(0)
        return success

    def get_average_usage(self, layer: BudgetLayer) -> float:
        """Get average usage for layer"""
        history = self.usage_history.get(layer, [])
        if not history:
            return 0.0
        return sum(history) / len(history)

    def auto_adjust(self):
        """Automatically adjust budgets based on usage patterns"""
        for layer in BudgetLayer:
            avg_usage = self.get_average_usage(layer)
            allocation = self.allocations[layer]

            # If average usage is high, increase allocation
            if avg_usage > allocation.allocated * 0.8:
                increase = int(allocation.allocated * 0.2)
                allocation.allocated += increase

            # If average usage is low, decrease allocation
            elif avg_usage < allocation.allocated * 0.3:
                decrease = int(allocation.allocated * 0.1)
                allocation.allocated = max(1000, allocation.allocated - decrease)
