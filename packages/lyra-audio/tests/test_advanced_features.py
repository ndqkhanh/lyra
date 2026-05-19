"""Tests for advanced features."""

from datetime import datetime, timedelta
import time

from lyra_audio.adaptive_volume import AdaptiveVolumeController
from lyra_audio.productivity_mode import ProductivityModeController
from lyra_audio.time_behavior import TimeBehaviorController


# Adaptive Volume Tests


def test_adaptive_volume_init():
    """Test adaptive volume initialization."""
    controller = AdaptiveVolumeController()
    assert controller.base_volume == 0.7
    assert controller.boost_amount == 0.3


def test_adaptive_volume_record_activity():
    """Test recording activity."""
    controller = AdaptiveVolumeController()
    initial_time = controller.last_activity_time
    time.sleep(0.1)
    controller.record_activity()
    assert controller.last_activity_time > initial_time


def test_adaptive_volume_get_current_volume():
    """Test getting current volume."""
    controller = AdaptiveVolumeController(base_volume=0.5, boost_amount=0.3)

    # Should return base volume when active
    controller.record_activity()
    assert controller.get_current_volume() == 0.5


def test_adaptive_volume_is_boosted():
    """Test boost detection."""
    controller = AdaptiveVolumeController()
    controller.set_inactivity_threshold(0.1)

    controller.record_activity()
    assert controller.is_boosted() is False

    time.sleep(0.2)
    assert controller.is_boosted() is True


# Time Behavior Tests


def test_time_behavior_init():
    """Test time behavior initialization."""
    controller = TimeBehaviorController()
    assert controller.ridiculous_start_hour == 17
    assert controller.enabled is True


def test_time_behavior_is_work_hours():
    """Test work hours detection."""
    controller = TimeBehaviorController()
    # Just check it returns a boolean
    assert isinstance(controller.is_work_hours(), bool)


def test_time_behavior_get_ridiculous_factor():
    """Test ridiculous factor calculation."""
    controller = TimeBehaviorController()
    factor = controller.get_ridiculous_factor()
    assert 0.0 <= factor <= 1.0


def test_time_behavior_enable_disable():
    """Test enable/disable."""
    controller = TimeBehaviorController()

    controller.disable()
    assert controller.is_enabled() is False

    controller.enable()
    assert controller.is_enabled() is True


# Productivity Mode Tests


def test_productivity_mode_init():
    """Test productivity mode initialization."""
    controller = ProductivityModeController()
    assert controller.enabled is False
    assert controller.focus_mode is False


def test_productivity_mode_set_deadline():
    """Test setting deadline."""
    controller = ProductivityModeController()
    deadline = datetime.now() + timedelta(hours=1)

    controller.set_deadline(deadline)
    assert controller.deadline == deadline


def test_productivity_mode_is_near_deadline():
    """Test near deadline detection."""
    controller = ProductivityModeController()

    # No deadline
    assert controller.is_near_deadline() is False

    # Deadline in 1 hour (within threshold)
    deadline = datetime.now() + timedelta(hours=1)
    controller.set_deadline(deadline)
    assert controller.is_near_deadline() is True


def test_productivity_mode_should_play_sound():
    """Test sound filtering."""
    controller = ProductivityModeController()

    # Disabled: all sounds allowed
    assert controller.should_play_sound("session_start") is True

    # Enabled with focus mode: only critical
    controller.enable()
    controller.enable_focus_mode()
    assert controller.should_play_sound("session_start") is False
    assert controller.should_play_sound("error_general") is True


def test_productivity_mode_is_critical_event():
    """Test critical event detection."""
    controller = ProductivityModeController()

    assert controller.is_critical_event("error_general") is True
    assert controller.is_critical_event("task_complete") is True
    assert controller.is_critical_event("session_start") is False
