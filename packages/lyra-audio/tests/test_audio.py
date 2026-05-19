"""Tests for audio system."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lyra_audio import AudioPlayer, EventHookSystem, LyraEvent, SoundManager


# Audio Player Tests


def test_audio_player_init():
    """Test audio player initialization."""
    player = AudioPlayer()
    assert player.platform in ["Darwin", "Linux", "Windows"]


def test_audio_player_platform_detection():
    """Test platform detection."""
    player = AudioPlayer()
    platform = player.get_platform()
    assert platform in ["Darwin", "Linux", "Windows"]


def test_audio_player_is_available():
    """Test player availability check."""
    player = AudioPlayer()
    # Should return True or False depending on platform
    assert isinstance(player.is_available(), bool)


@patch("subprocess.run")
def test_audio_player_play_blocking(mock_run):
    """Test blocking audio playback."""
    with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp:
        player = AudioPlayer()
        if player.platform == "Darwin":
            player.play(tmp.name, blocking=True)
            if player.is_available():
                mock_run.assert_called_once()


@patch("subprocess.Popen")
def test_audio_player_play_async_method(mock_popen):
    """Test async playback method."""
    with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp:
        player = AudioPlayer()
        if player.platform in ["Darwin", "Linux"]:
            player.play_async(tmp.name)
            # Give thread time to start
            import time
            time.sleep(0.1)


# Sound Manager Tests


def test_sound_manager_init():
    """Test sound manager initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SoundManager(sounds_dir=tmpdir)
        assert manager.sounds_dir == Path(tmpdir)


def test_sound_manager_enable_disable():
    """Test enabling and disabling sounds."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SoundManager(sounds_dir=tmpdir)

        manager.disable()
        assert manager.is_enabled() is False

        manager.enable()
        assert manager.is_enabled() is True


def test_sound_manager_volume():
    """Test volume control."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SoundManager(sounds_dir=tmpdir)

        manager.set_volume(0.5)
        assert manager.get_volume() == 0.5

        # Test clamping
        manager.set_volume(1.5)
        assert manager.get_volume() == 1.0

        manager.set_volume(-0.5)
        assert manager.get_volume() == 0.0


def test_sound_manager_theme():
    """Test theme management."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SoundManager(sounds_dir=tmpdir)

        # Create test theme
        theme_dir = Path(tmpdir) / "test_theme"
        theme_dir.mkdir()

        manager.set_theme("test_theme")
        assert manager.get_theme() == "test_theme"


def test_sound_manager_list_themes():
    """Test listing themes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SoundManager(sounds_dir=tmpdir)

        # Create test themes
        (Path(tmpdir) / "theme1").mkdir()
        (Path(tmpdir) / "theme2").mkdir()

        themes = manager.list_themes()
        assert "theme1" in themes
        assert "theme2" in themes


def test_sound_manager_play_event():
    """Test playing event sound."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SoundManager(sounds_dir=tmpdir)

        # Create test theme and sound file
        theme_dir = Path(tmpdir) / "default"
        theme_dir.mkdir()
        sound_file = theme_dir / "task_complete.mp3"
        sound_file.touch()

        # Should not raise error
        manager.play_event("task_complete")


# Event Hook System Tests


def test_event_hook_system_init():
    """Test event hook system initialization."""
    hooks = EventHookSystem()
    assert len(hooks.hooks) == 0


def test_event_hook_system_register():
    """Test registering hooks."""
    hooks = EventHookSystem()

    def callback(context):
        pass

    hooks.register_hook("test_event", callback)
    assert "test_event" in hooks.hooks
    assert callback in hooks.hooks["test_event"]


def test_event_hook_system_unregister():
    """Test unregistering hooks."""
    hooks = EventHookSystem()

    def callback(context):
        pass

    hooks.register_hook("test_event", callback)
    hooks.unregister_hook("test_event", callback)
    assert callback not in hooks.hooks.get("test_event", [])


def test_event_hook_system_trigger():
    """Test triggering events."""
    hooks = EventHookSystem()

    called = []

    def callback(context):
        called.append(context)

    hooks.register_hook("test_event", callback)
    hooks.trigger("test_event", {"data": "test"})

    assert len(called) == 1
    assert called[0]["data"] == "test"


def test_event_hook_system_clear():
    """Test clearing hooks."""
    hooks = EventHookSystem()

    def callback(context):
        pass

    hooks.register_hook("event1", callback)
    hooks.register_hook("event2", callback)

    hooks.clear_hooks("event1")
    assert "event1" not in hooks.hooks
    assert "event2" in hooks.hooks

    hooks.clear_hooks()
    assert len(hooks.hooks) == 0


def test_event_hook_system_list_events():
    """Test listing events."""
    hooks = EventHookSystem()

    def callback(context):
        pass

    hooks.register_hook("event1", callback)
    hooks.register_hook("event2", callback)

    events = hooks.list_events()
    assert "event1" in events
    assert "event2" in events


def test_lyra_event_enum():
    """Test LyraEvent enum."""
    assert LyraEvent.SESSION_START.value == "session_start"
    assert LyraEvent.TASK_COMPLETE.value == "task_complete"
    assert LyraEvent.ERROR_GENERAL.value == "error_general"
    assert LyraEvent.MILESTONE_10.value == "milestone_10"


# Integration Tests


def test_integration_sound_manager_with_hooks():
    """Test sound manager integration with hooks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SoundManager(sounds_dir=tmpdir)
        hooks = EventHookSystem()
        hooks.sound_manager = manager

        # Create test theme and sound
        theme_dir = Path(tmpdir) / "default"
        theme_dir.mkdir()
        sound_file = theme_dir / "task_complete.mp3"
        sound_file.touch()

        # Trigger event
        hooks.trigger("task_complete")
        # Should not raise error


def test_integration_custom_callback():
    """Test custom callback with sound manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SoundManager(sounds_dir=tmpdir)
        hooks = EventHookSystem()
        hooks.sound_manager = manager

        called = []

        def callback(context):
            called.append(context)

        hooks.register_hook("custom_event", callback)
        hooks.trigger("custom_event", {"test": "data"})

        assert len(called) == 1
        assert called[0]["test"] == "data"
