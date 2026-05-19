"""
Tests for Advanced Sound Features (Funny Sounds Phase 3)

Tests adaptive volume, productivity mode, and context-aware sounds.
"""

import pytest
import time
from datetime import date, timedelta
from pathlib import Path
from lyra_research.sounds.adaptive_volume import AdaptiveVolume
from lyra_research.sounds.productivity_mode import ProductivityMode
from lyra_research.sounds.context_aware import ContextAwareSounds
from lyra_research.sounds.theme_manager import ThemeManager


class TestAdaptiveVolume:
    """Test adaptive volume"""

    def test_base_volume_for_non_completion(self):
        """Test base volume for non-completion events"""
        adaptive = AdaptiveVolume(base_volume=0.5)
        assert adaptive.get_volume("task_start") == 0.5
        assert adaptive.get_volume("error") == 0.5

    def test_base_volume_for_first_completion(self):
        """Test base volume for first completion"""
        adaptive = AdaptiveVolume(base_volume=0.5)
        assert adaptive.get_volume("task_complete") == 0.5

    def test_increased_volume_after_no_response(self):
        """Test volume increases after no response"""
        adaptive = AdaptiveVolume(base_volume=0.5)
        adaptive.mark_completion()

        # Wait for threshold
        time.sleep(0.1)
        adaptive.no_response_threshold = timedelta(seconds=0.05)

        volume = adaptive.get_volume("task_complete")
        assert volume == 0.75  # 0.5 * 1.5

    def test_reset_on_response(self):
        """Test volume resets on user response"""
        adaptive = AdaptiveVolume(base_volume=0.5)
        adaptive.mark_completion()
        adaptive.mark_response()

        volume = adaptive.get_volume("task_complete")
        assert volume == 0.5

    def test_volume_capped_at_1_0(self):
        """Test volume is capped at 1.0"""
        adaptive = AdaptiveVolume(base_volume=0.8)
        adaptive.mark_completion()
        time.sleep(0.1)
        adaptive.no_response_threshold = timedelta(seconds=0.05)

        volume = adaptive.get_volume("task_complete")
        assert volume == 1.0  # Capped, not 1.2


class TestProductivityMode:
    """Test productivity mode"""

    def test_not_near_deadline_initially(self):
        """Test not near deadline initially"""
        prod = ProductivityMode()
        assert not prod.is_near_deadline()

    def test_near_deadline_detection(self):
        """Test near deadline detection"""
        prod = ProductivityMode()
        tomorrow = date.today() + timedelta(days=1)
        prod.add_deadline(tomorrow, "Project deadline")

        assert prod.is_near_deadline(days_threshold=3)

    def test_not_near_deadline_far_future(self):
        """Test not near deadline for far future"""
        prod = ProductivityMode()
        far_future = date.today() + timedelta(days=10)
        prod.add_deadline(far_future, "Future deadline")

        assert not prod.is_near_deadline(days_threshold=3)

    def test_focus_mode_reduces_sounds(self):
        """Test focus mode reduces sounds"""
        prod = ProductivityMode()
        prod.enable_focus_mode()

        assert prod.should_reduce_sounds()
        assert prod.get_volume_multiplier() == 0.3

    def test_deadline_reduces_sounds(self):
        """Test deadline reduces sounds"""
        prod = ProductivityMode()
        tomorrow = date.today() + timedelta(days=1)
        prod.add_deadline(tomorrow, "Deadline")

        assert prod.should_reduce_sounds()
        assert prod.get_volume_multiplier() == 0.3

    def test_normal_volume_when_not_reducing(self):
        """Test normal volume when not reducing"""
        prod = ProductivityMode()
        assert not prod.should_reduce_sounds()
        assert prod.get_volume_multiplier() == 1.0

    def test_disable_focus_mode(self):
        """Test disabling focus mode"""
        prod = ProductivityMode()
        prod.enable_focus_mode()
        prod.disable_focus_mode()

        assert not prod.focus_mode
        assert not prod.should_reduce_sounds()


class TestContextAwareSounds:
    """Test context-aware sounds"""

    def test_python_file_context(self):
        """Test Python file context"""
        manager = ThemeManager()
        context_aware = ContextAwareSounds(manager)

        context = {"file_path": "/path/to/script.py"}
        result = context_aware.get_context_sound("task_complete", context)

        assert result == "task_complete_python"

    def test_test_file_context(self):
        """Test test file context"""
        manager = ThemeManager()
        context_aware = ContextAwareSounds(manager)

        context = {"file_path": "/path/to/test_module.py"}
        result = context_aware.get_context_sound("task_complete", context)

        assert result == "task_complete_test"

    def test_evening_time_context(self):
        """Test evening time context"""
        manager = ThemeManager()
        context_aware = ContextAwareSounds(manager)

        from datetime import datetime
        evening_time = datetime(2026, 5, 20, 18, 0)  # 6 PM
        context = {"time": evening_time}
        result = context_aware.get_context_sound("task_complete", context)

        assert result == "task_complete_evening"

    def test_no_context_returns_none(self):
        """Test no context returns None"""
        manager = ThemeManager()
        context_aware = ContextAwareSounds(manager)

        result = context_aware.get_context_sound("task_complete", {})
        assert result is None

    def test_non_python_file_returns_none(self):
        """Test non-Python file returns None"""
        manager = ThemeManager()
        context_aware = ContextAwareSounds(manager)

        context = {"file_path": "/path/to/document.txt"}
        result = context_aware.get_context_sound("task_complete", context)

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
