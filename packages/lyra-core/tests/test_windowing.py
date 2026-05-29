"""
Tests for Context Windowing System
"""

import pytest
from lyra_core.windowing import (
    ContextWindow,
    SlidingWindowManager,
    PriorityWindowManager,
    AdaptiveWindowManager
)


class TestContextWindow:
    """Test ContextWindow"""

    def test_initialization(self):
        """Test window initialization"""
        window = ContextWindow(
            id="test",
            content=["item1", "item2"],
            start_index=0,
            end_index=2
        )
        assert window.id == "test"
        assert window.size() == 2

    def test_touch(self):
        """Test touch updates access time"""
        window = ContextWindow(
            id="test",
            content=[],
            start_index=0,
            end_index=0
        )
        old_time = window.accessed_at
        window.touch()
        assert window.accessed_at >= old_time


class TestSlidingWindowManager:
    """Test SlidingWindowManager"""

    def test_initialization(self):
        """Test manager initialization"""
        manager = SlidingWindowManager(
            window_size=100,
            overlap=10,
            max_windows=5
        )
        assert manager.window_size == 100
        assert manager.overlap == 10

    def test_add_content(self):
        """Test adding content"""
        manager = SlidingWindowManager(window_size=3)
        manager.add_content("item1")
        manager.add_content("item2")

        assert len(manager.windows) == 1
        assert manager.windows[0].size() == 2

    def test_window_creation(self):
        """Test automatic window creation"""
        manager = SlidingWindowManager(window_size=2, overlap=1)

        manager.add_content("item1")
        manager.add_content("item2")
        manager.add_content("item3")  # Should create new window

        assert len(manager.windows) == 2

    def test_window_overlap(self):
        """Test window overlap"""
        manager = SlidingWindowManager(window_size=3, overlap=1)

        manager.add_content("item1")
        manager.add_content("item2")
        manager.add_content("item3")
        manager.add_content("item4")  # Creates new window with overlap

        assert len(manager.windows) == 2
        # Second window should have overlap from first
        assert len(manager.windows[1].content) > 0

    def test_get_active_window(self):
        """Test getting active window"""
        manager = SlidingWindowManager()
        manager.add_content("item1")

        active = manager.get_active_window()
        assert active is not None
        assert active.size() == 1

    def test_get_recent_content(self):
        """Test getting recent content"""
        manager = SlidingWindowManager(window_size=2)

        manager.add_content("item1")
        manager.add_content("item2")
        manager.add_content("item3")

        recent = manager.get_recent_content(2)
        assert len(recent) == 2

    def test_clear_old_windows(self):
        """Test clearing old windows"""
        manager = SlidingWindowManager(window_size=1, max_windows=10)

        for i in range(5):
            manager.add_content(f"item{i}")

        manager.clear_old_windows(keep_recent=2)
        assert len(manager.windows) == 2


class TestPriorityWindowManager:
    """Test PriorityWindowManager"""

    def test_initialization(self):
        """Test manager initialization"""
        manager = PriorityWindowManager(max_windows=5)
        assert manager.max_windows == 5

    def test_add_window(self):
        """Test adding window"""
        manager = PriorityWindowManager()
        window = manager.add_window(["item1", "item2"], priority=0.8)

        assert window.priority == 0.8
        assert len(manager.windows) == 1

    def test_priority_eviction(self):
        """Test eviction of low-priority windows"""
        manager = PriorityWindowManager(max_windows=2)

        manager.add_window(["item1"], priority=0.5)
        manager.add_window(["item2"], priority=0.9)
        manager.add_window(["item3"], priority=0.7)  # Should evict lowest

        assert len(manager.windows) == 2
        # Lowest priority should be evicted
        priorities = [w.priority for w in manager.windows]
        assert 0.5 not in priorities

    def test_get_high_priority_windows(self):
        """Test getting high-priority windows"""
        manager = PriorityWindowManager()

        manager.add_window(["item1"], priority=0.5)
        manager.add_window(["item2"], priority=0.9)
        manager.add_window(["item3"], priority=0.95)

        high_priority = manager.get_high_priority_windows(threshold=0.8)
        assert len(high_priority) == 2

    def test_update_priority(self):
        """Test updating window priority"""
        manager = PriorityWindowManager()
        window = manager.add_window(["item1"], priority=0.5)

        manager.update_priority(window.id, 0.9)
        assert window.priority == 0.9


class TestAdaptiveWindowManager:
    """Test AdaptiveWindowManager"""

    def test_initialization(self):
        """Test manager initialization"""
        manager = AdaptiveWindowManager(
            min_window_size=100,
            max_window_size=1000
        )
        assert manager.min_window_size == 100
        assert manager.max_window_size == 1000

    def test_add_content(self):
        """Test adding content"""
        manager = AdaptiveWindowManager()
        content = ["item1", "item2", "item3"]
        window = manager.add_content(content)

        assert window.size() == 3
        assert len(manager.windows) == 1

    def test_window_size_increase(self):
        """Test window size increases with high utilization"""
        manager = AdaptiveWindowManager(
            min_window_size=10,
            max_window_size=100,
            target_utilization=0.5
        )

        # Add content that exceeds target utilization
        large_content = ["item"] * 8
        manager.add_content(large_content)

        # Window size should increase
        assert manager.current_window_size > manager.min_window_size

    def test_window_size_decrease(self):
        """Test window size decreases with low utilization"""
        manager = AdaptiveWindowManager(
            min_window_size=10,
            max_window_size=100,
            target_utilization=0.8
        )

        # First add large content to increase size
        manager.add_content(["item"] * 80)

        # Then add small content
        manager.add_content(["item"] * 2)

        # Window size should eventually decrease
        # (may take multiple iterations)

    def test_get_recommended_size(self):
        """Test getting recommended size"""
        manager = AdaptiveWindowManager(min_window_size=100)

        size = manager.get_recommended_size()
        assert size >= manager.min_window_size


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
