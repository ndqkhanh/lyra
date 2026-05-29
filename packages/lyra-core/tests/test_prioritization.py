"""
Tests for Context Prioritization System
"""

import pytest
import time
from lyra_core.prioritization import (
    PriorityFactor,
    PriorityScore,
    PrioritizedItem,
    PriorityCalculator,
    PriorityQueue,
    AdaptivePriorityQueue
)


class TestPriorityScore:
    """Test PriorityScore"""

    def test_initialization(self):
        """Test score initialization"""
        score = PriorityScore(total=0.0)
        assert score.total == 0.0
        assert len(score.factors) == 0

    def test_add_factor(self):
        """Test adding factors"""
        score = PriorityScore(total=0.0)
        score.add_factor(PriorityFactor.RECENCY, 0.5)

        assert PriorityFactor.RECENCY in score.factors
        assert score.total == 0.5


class TestPrioritizedItem:
    """Test PrioritizedItem"""

    def test_initialization(self):
        """Test item initialization"""
        score = PriorityScore(total=1.0)
        item = PrioritizedItem(
            id="test",
            content="test content",
            priority=score
        )
        assert item.id == "test"
        assert item.access_count == 0

    def test_touch(self):
        """Test touch updates"""
        score = PriorityScore(total=1.0)
        item = PrioritizedItem(id="test", content="test", priority=score)

        old_count = item.access_count
        item.touch()

        assert item.access_count == old_count + 1


class TestPriorityCalculator:
    """Test PriorityCalculator"""

    def test_initialization(self):
        """Test calculator initialization"""
        calc = PriorityCalculator()
        assert len(calc.weights) == 5

    def test_calculate_recency(self):
        """Test recency calculation"""
        calc = PriorityCalculator()
        score = PriorityScore(total=0.0)
        item = PrioritizedItem(id="test", content="test", priority=score)

        # Recent item should have high recency score
        recency = calc._calculate_recency(item)
        assert recency > 0.9

    def test_calculate_frequency(self):
        """Test frequency calculation"""
        calc = PriorityCalculator()
        score = PriorityScore(total=0.0)
        item = PrioritizedItem(id="test", content="test", priority=score)

        item.access_count = 10
        frequency = calc._calculate_frequency(item)
        assert frequency > 0.0

    def test_calculate_relevance(self):
        """Test relevance calculation"""
        calc = PriorityCalculator()
        score = PriorityScore(total=0.0)
        item = PrioritizedItem(
            id="test",
            content="python programming",
            priority=score
        )

        relevance = calc._calculate_relevance(item, "python")
        assert relevance == 1.0

    def test_calculate_full_score(self):
        """Test full score calculation"""
        calc = PriorityCalculator()
        score = PriorityScore(total=0.0)
        item = PrioritizedItem(id="test", content="test", priority=score)

        new_score = calc.calculate(item, "test")
        assert new_score.total > 0.0
        assert len(new_score.factors) > 0


class TestPriorityQueue:
    """Test PriorityQueue"""

    def test_initialization(self):
        """Test queue initialization"""
        queue = PriorityQueue()
        assert len(queue.items) == 0

    def test_add_item(self):
        """Test adding items"""
        queue = PriorityQueue()
        score = PriorityScore(total=1.0)
        item = PrioritizedItem(id="test", content="test", priority=score)

        queue.add(item)
        assert len(queue.items) == 1

    def test_remove_item(self):
        """Test removing items"""
        queue = PriorityQueue()
        score = PriorityScore(total=1.0)
        item = PrioritizedItem(id="test", content="test", priority=score)

        queue.add(item)
        success = queue.remove("test")

        assert success is True
        assert len(queue.items) == 0

    def test_get_top(self):
        """Test getting top items"""
        queue = PriorityQueue()

        # Add items with different priorities
        for i in range(5):
            score = PriorityScore(total=float(i))
            item = PrioritizedItem(id=f"item{i}", content=f"content{i}", priority=score)
            queue.add(item)

        top = queue.get_top(3)
        assert len(top) == 3
        # Should be sorted by priority (highest first)
        assert top[0].priority.total >= top[1].priority.total

    def test_boost(self):
        """Test boosting items"""
        queue = PriorityQueue()
        score = PriorityScore(total=1.0)
        item = PrioritizedItem(id="test", content="test", priority=score)

        queue.add(item)
        queue.boost("test", 2.0)

        assert item.boost == 2.0

    def test_decay_priorities(self):
        """Test priority decay"""
        queue = PriorityQueue()
        score = PriorityScore(total=1.0)
        item = PrioritizedItem(id="test", content="test", priority=score)
        item.boost = 1.0

        queue.add(item)
        queue.decay_priorities(decay_rate=0.1)

        assert item.boost < 1.0

    def test_get_stats(self):
        """Test statistics"""
        queue = PriorityQueue()
        score = PriorityScore(total=1.0)
        item = PrioritizedItem(id="test", content="test", priority=score)

        queue.add(item)
        stats = queue.get_stats()

        assert stats['total_items'] == 1
        assert 'avg_priority' in stats


class TestAdaptivePriorityQueue:
    """Test AdaptivePriorityQueue"""

    def test_initialization(self):
        """Test queue initialization"""
        queue = AdaptivePriorityQueue()
        assert len(queue.access_patterns) == 0

    def test_access_tracking(self):
        """Test access pattern tracking"""
        queue = AdaptivePriorityQueue()
        score = PriorityScore(total=1.0)
        item = PrioritizedItem(id="test", content="test", priority=score)

        queue.add(item)
        queue.get_top(1)

        assert "test" in queue.access_patterns
        assert queue.access_patterns["test"] == 1

    def test_adjust_weights(self):
        """Test weight adjustment"""
        queue = AdaptivePriorityQueue()

        # Add items and access them
        for i in range(5):
            score = PriorityScore(total=float(i))
            item = PrioritizedItem(id=f"item{i}", content=f"content{i}", priority=score)
            queue.add(item)

        # Access top items multiple times
        for _ in range(10):
            queue.get_top(2)

        old_weights = queue.calculator.weights.copy()
        queue.adjust_weights()

        # Weights should be adjusted
        # (may or may not change depending on patterns)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
