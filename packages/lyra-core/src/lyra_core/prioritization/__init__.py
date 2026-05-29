"""
Context Prioritization System

Prioritizes context items based on multiple factors.

Features:
- Multi-factor priority scoring
- Priority decay over time
- Boost mechanisms
- Priority-based sorting
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum
import time
import math


class PriorityFactor(Enum):
    """Priority factors"""
    RECENCY = "recency"
    FREQUENCY = "frequency"
    RELEVANCE = "relevance"
    IMPORTANCE = "importance"
    USER_BOOST = "user_boost"


@dataclass
class PriorityScore:
    """Priority score with breakdown"""
    total: float
    factors: Dict[PriorityFactor, float] = field(default_factory=dict)

    def add_factor(self, factor: PriorityFactor, score: float):
        """Add factor score"""
        self.factors[factor] = score
        self.total += score


@dataclass
class PrioritizedItem:
    """Item with priority"""
    id: str
    content: any
    priority: PriorityScore
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    boost: float = 1.0

    def touch(self):
        """Update access time and count"""
        self.accessed_at = time.time()
        self.access_count += 1


class PriorityCalculator:
    """
    Priority calculator

    Calculates priority scores based on multiple factors.
    """

    def __init__(
        self,
        weights: Optional[Dict[PriorityFactor, float]] = None
    ):
        self.weights = weights or {
            PriorityFactor.RECENCY: 0.3,
            PriorityFactor.FREQUENCY: 0.2,
            PriorityFactor.RELEVANCE: 0.3,
            PriorityFactor.IMPORTANCE: 0.15,
            PriorityFactor.USER_BOOST: 0.05
        }

    def calculate(
        self,
        item: PrioritizedItem,
        query: Optional[str] = None
    ) -> PriorityScore:
        """Calculate priority score"""
        score = PriorityScore(total=0.0)

        # Recency score
        recency = self._calculate_recency(item)
        score.add_factor(
            PriorityFactor.RECENCY,
            recency * self.weights[PriorityFactor.RECENCY]
        )

        # Frequency score
        frequency = self._calculate_frequency(item)
        score.add_factor(
            PriorityFactor.FREQUENCY,
            frequency * self.weights[PriorityFactor.FREQUENCY]
        )

        # Relevance score (if query provided)
        if query:
            relevance = self._calculate_relevance(item, query)
            score.add_factor(
                PriorityFactor.RELEVANCE,
                relevance * self.weights[PriorityFactor.RELEVANCE]
            )

        # Importance score (based on boost)
        importance = item.boost
        score.add_factor(
            PriorityFactor.IMPORTANCE,
            importance * self.weights[PriorityFactor.IMPORTANCE]
        )

        # User boost
        score.add_factor(
            PriorityFactor.USER_BOOST,
            item.boost * self.weights[PriorityFactor.USER_BOOST]
        )

        return score

    def _calculate_recency(self, item: PrioritizedItem) -> float:
        """Calculate recency score (0-1)"""
        current_time = time.time()
        time_diff = current_time - item.accessed_at

        # Exponential decay: score = e^(-time_diff / half_life)
        half_life = 3600  # 1 hour
        score = math.exp(-time_diff / half_life)

        return score

    def _calculate_frequency(self, item: PrioritizedItem) -> float:
        """Calculate frequency score (0-1)"""
        # Logarithmic scaling for frequency
        if item.access_count == 0:
            return 0.0

        # Score increases logarithmically with access count
        score = math.log(item.access_count + 1) / math.log(100)
        return min(1.0, score)

    def _calculate_relevance(
        self,
        item: PrioritizedItem,
        query: str
    ) -> float:
        """Calculate relevance score (0-1)"""
        # Simple keyword matching
        content_str = str(item.content).lower()
        query_terms = query.lower().split()

        if not query_terms:
            return 0.0

        matches = sum(1 for term in query_terms if term in content_str)
        score = matches / len(query_terms)

        return score


class PriorityQueue:
    """
    Priority queue for context items

    Maintains items sorted by priority.
    """

    def __init__(self, calculator: Optional[PriorityCalculator] = None):
        self.calculator = calculator or PriorityCalculator()
        self.items: List[PrioritizedItem] = []

    def add(self, item: PrioritizedItem):
        """Add item to queue"""
        self.items.append(item)
        self._resort()

    def remove(self, item_id: str) -> bool:
        """Remove item from queue"""
        for i, item in enumerate(self.items):
            if item.id == item_id:
                self.items.pop(i)
                return True
        return False

    def get_top(self, n: int = 10, query: Optional[str] = None) -> List[PrioritizedItem]:
        """Get top N items"""
        # Recalculate priorities
        self._recalculate_priorities(query)
        self._resort()

        return self.items[:n]

    def boost(self, item_id: str, boost: float):
        """Boost item priority"""
        for item in self.items:
            if item.id == item_id:
                item.boost = boost
                break

    def _recalculate_priorities(self, query: Optional[str] = None):
        """Recalculate all priorities"""
        for item in self.items:
            item.priority = self.calculator.calculate(item, query)

    def _resort(self):
        """Resort items by priority"""
        self.items.sort(key=lambda x: x.priority.total, reverse=True)

    def decay_priorities(self, decay_rate: float = 0.1):
        """Apply decay to all priorities"""
        for item in self.items:
            item.boost *= (1 - decay_rate)
            item.boost = max(0.1, item.boost)  # Minimum boost

    def get_stats(self) -> Dict:
        """Get queue statistics"""
        if not self.items:
            return {
                'total_items': 0,
                'avg_priority': 0.0
            }

        avg_priority = sum(item.priority.total for item in self.items) / len(self.items)

        return {
            'total_items': len(self.items),
            'avg_priority': avg_priority,
            'top_priority': self.items[0].priority.total if self.items else 0.0,
            'bottom_priority': self.items[-1].priority.total if self.items else 0.0
        }


class AdaptivePriorityQueue(PriorityQueue):
    """
    Adaptive priority queue

    Automatically adjusts weights based on usage patterns.
    """

    def __init__(self):
        super().__init__()
        self.access_patterns: Dict[str, int] = {}

    def get_top(self, n: int = 10, query: Optional[str] = None) -> List[PrioritizedItem]:
        """Get top items and track access patterns"""
        items = super().get_top(n, query)

        # Track which items are accessed
        for item in items:
            self.access_patterns[item.id] = self.access_patterns.get(item.id, 0) + 1

        return items

    def adjust_weights(self):
        """Adjust calculator weights based on access patterns"""
        # Analyze which items are accessed most
        # Items with high recency but low access might need weight adjustment

        if not self.items or not self.access_patterns:
            return

        # Calculate correlation between factors and access
        # This is a simplified version
        total_accesses = sum(self.access_patterns.values())

        for item in self.items:
            accesses = self.access_patterns.get(item.id, 0)
            if accesses > total_accesses * 0.1:  # Top 10% accessed
                # Increase weight of dominant factor
                max_factor = max(
                    item.priority.factors.items(),
                    key=lambda x: x[1]
                )[0]

                self.calculator.weights[max_factor] *= 1.05

        # Normalize weights
        total_weight = sum(self.calculator.weights.values())
        for factor in self.calculator.weights:
            self.calculator.weights[factor] /= total_weight
