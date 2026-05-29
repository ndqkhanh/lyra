"""
Adaptive Budget System

Dynamically adjusts context layer budgets based on usage patterns.

Features:
- Usage-based budget adjustment
- Layer priority management
- Automatic rebalancing
- Performance tracking
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import time


class LayerType(Enum):
    """Context layer types"""
    SYSTEM = "system"
    SESSION = "session"
    MEMORY = "memory"
    DYNAMIC = "dynamic"
    TOOLS = "tools"
    RESULTS = "results"
    PROVENANCE = "provenance"
    METADATA = "metadata"


@dataclass
class LayerUsage:
    """Track usage statistics for a layer"""
    layer: LayerType
    current_tokens: int = 0
    peak_tokens: int = 0
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    utilization_history: List[float] = field(default_factory=list)

    def record_usage(self, tokens: int):
        """Record token usage"""
        self.current_tokens = tokens
        self.peak_tokens = max(self.peak_tokens, tokens)
        self.access_count += 1
        self.last_accessed = time.time()

    def get_utilization(self, budget: int) -> float:
        """Get current utilization percentage"""
        if budget == 0:
            return 0.0
        return self.current_tokens / budget

    def get_avg_utilization(self) -> float:
        """Get average utilization"""
        if not self.utilization_history:
            return 0.0
        return sum(self.utilization_history) / len(self.utilization_history)


@dataclass
class AdaptiveBudget:
    """
    Adaptive budget for a context layer

    Automatically adjusts based on usage patterns
    """
    layer: LayerType
    initial_budget: int
    current_budget: int
    min_budget: int
    max_budget: int
    usage: LayerUsage = field(init=False)

    def __post_init__(self):
        self.usage = LayerUsage(layer=self.layer)

    def adjust(self, adjustment: int) -> int:
        """Adjust budget within min/max bounds"""
        new_budget = self.current_budget + adjustment
        new_budget = max(self.min_budget, min(self.max_budget, new_budget))
        old_budget = self.current_budget
        self.current_budget = new_budget
        return new_budget - old_budget

    def get_available(self) -> int:
        """Get available tokens"""
        return max(0, self.current_budget - self.usage.current_tokens)

    def is_over_budget(self) -> bool:
        """Check if over budget"""
        return self.usage.current_tokens > self.current_budget


class AdaptiveBudgetManager:
    """
    Manages adaptive budgets across all context layers

    Features:
    - Automatic budget adjustment based on usage
    - Priority-based rebalancing
    - Performance tracking
    - Budget enforcement
    """

    def __init__(self, total_budget: int = 200000):
        self.total_budget = total_budget
        self.budgets: Dict[LayerType, AdaptiveBudget] = {}
        self._initialize_budgets()

    def _initialize_budgets(self):
        """Initialize default budgets for all layers"""
        # Default budget allocation (percentages of total)
        allocations = {
            LayerType.SYSTEM: 0.10,      # 10% - System instructions
            LayerType.SESSION: 0.30,     # 30% - Current conversation
            LayerType.MEMORY: 0.25,      # 25% - Retrieved memories
            LayerType.DYNAMIC: 0.15,     # 15% - Dynamic context
            LayerType.TOOLS: 0.10,       # 10% - Tool definitions
            LayerType.RESULTS: 0.05,     # 5% - Tool results
            LayerType.PROVENANCE: 0.03,  # 3% - Provenance tracking
            LayerType.METADATA: 0.02,    # 2% - Metadata
        }

        for layer, allocation in allocations.items():
            initial = int(self.total_budget * allocation)
            self.budgets[layer] = AdaptiveBudget(
                layer=layer,
                initial_budget=initial,
                current_budget=initial,
                min_budget=int(initial * 0.5),   # Min 50% of initial
                max_budget=int(initial * 2.0)    # Max 200% of initial
            )

    def record_usage(self, layer: LayerType, tokens: int):
        """Record token usage for a layer"""
        if layer in self.budgets:
            budget = self.budgets[layer]
            budget.usage.record_usage(tokens)

            # Record utilization
            utilization = budget.usage.get_utilization(budget.current_budget)
            budget.usage.utilization_history.append(utilization)

            # Keep only recent history (last 100 records)
            if len(budget.usage.utilization_history) > 100:
                budget.usage.utilization_history.pop(0)

    def rebalance(self):
        """
        Rebalance budgets based on usage patterns

        Strategy:
        - Increase budgets for high-utilization layers
        - Decrease budgets for low-utilization layers
        - Maintain total budget constraint
        """
        # Calculate adjustments needed
        adjustments: Dict[LayerType, int] = {}

        for layer, budget in self.budgets.items():
            avg_util = budget.usage.get_avg_utilization()

            if avg_util > 0.9:  # Over 90% utilization
                # Increase budget by 10%
                adjustment = int(budget.current_budget * 0.1)
                adjustments[layer] = adjustment
            elif avg_util < 0.3:  # Under 30% utilization
                # Decrease budget by 10%
                adjustment = -int(budget.current_budget * 0.1)
                adjustments[layer] = adjustment
            else:
                adjustments[layer] = 0

        # Apply adjustments while maintaining total budget
        total_adjustment = sum(adjustments.values())

        if total_adjustment != 0:
            # Normalize adjustments to maintain total budget
            scale = 1.0 if total_adjustment == 0 else -total_adjustment / sum(
                abs(a) for a in adjustments.values() if a < 0
            )

            for layer, adjustment in adjustments.items():
                if adjustment < 0:
                    # Scale down reductions
                    adjustment = int(adjustment * scale)
                self.budgets[layer].adjust(adjustment)

    def get_stats(self) -> Dict:
        """Get budget statistics"""
        total_used = sum(b.usage.current_tokens for b in self.budgets.values())
        total_allocated = sum(b.current_budget for b in self.budgets.values())

        return {
            'total_budget': self.total_budget,
            'total_allocated': total_allocated,
            'total_used': total_used,
            'utilization': total_used / total_allocated if total_allocated > 0 else 0,
            'layers': {
                layer.value: {
                    'budget': budget.current_budget,
                    'used': budget.usage.current_tokens,
                    'utilization': budget.usage.get_utilization(budget.current_budget),
                    'avg_utilization': budget.usage.get_avg_utilization(),
                    'access_count': budget.usage.access_count
                }
                for layer, budget in self.budgets.items()
            }
        }
