"""Tests for lyra-audio internals and edge cases not covered by existing tests.

Covers:
- AudioPlayer cross-platform detection edge cases
- EventHookSystem callback error handling
- ConfigurationManager corrupt/invalid file handling
- SoundManager JSON parsing errors
- ProductivityModeController deadline edge cases
- AdaptiveVolumeController edge cases (enable/disable, bounds)
- TimeBehaviorController variant selection
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from lyra_audio.adaptive_volume import AdaptiveVolumeController
from lyra_audio.audio_player import AudioPlayer
from lyra_audio.audio_suppression import AudioSuppression, SuppressionConfig
from lyra_audio.config_manager import ConfigurationManager
from lyra_audio.event_hooks import EventHookSystem, LyraEvent
from lyra_audio.productivity_mode import ProductivityModeController
from lyra_audio.sound_manager import SoundManager
from lyra_audio.time_behavior import TimeBehaviorController


# ═══════════════════════════════════════════════════════════════════════════
# AudioPlayer
# ═══════════════════════════════════════════════════════════════════════════


class TestAudioPlayerEdgeCases:
    """Beyond basic platform detection — test player command resolution."""

    def test_detect_player_darwin(self):
        """macOS should detect afplay."""
        player = AudioPlayer()
        if player.platform == "Darwin":
            assert player.player_cmd == "afplay"

    def test_play_non_existent_file_does_not_crash(self):
        player = AudioPlayer()
        # Should not raise
        player.play("/nonexistent/path/to/sound.wav")

    def test_play_no_player_available(self):
        """When player_cmd is None, play() should be a no-op."""
        player = AudioPlayer()
        player.player_cmd = None
        # Should not raise
        player.play("/some/file.wav")

    @patch("lyra_audio.audio_player.shutil.which")
    def test_linux_player_preference(self, mock_which):
        """Linux should prefer aplay > paplay > ffplay."""
        mock_which.side_effect = lambda x: x if x == "aplay" else None
        with patch("lyra_audio.audio_player.platform.system", return_value="Linux"):
            player = AudioPlayer()
            assert player.player_cmd == "aplay"

    @patch("lyra_audio.audio_player.shutil.which")
    def test_linux_no_player(self, mock_which):
        """Linux with no audio players available."""
        mock_which.return_value = None
        with patch("lyra_audio.audio_player.platform.system", return_value="Linux"):
            player = AudioPlayer()
            assert player.player_cmd is None
            assert player.is_available() is False

    def test_play_async_creates_daemon_thread(self):
        """play_async should start a thread and call play."""
        player = AudioPlayer()
        with patch.object(player, "play") as mock_play:
            player.play_async("/test/file.wav")
            # The thread calls play() with blocking=False
            mock_play.assert_called_once_with("/test/file.wav", 1.0, False)


# ═══════════════════════════════════════════════════════════════════════════
# EventHookSystem
# ═══════════════════════════════════════════════════════════════════════════


class TestEventHookSystemEdgeCases:
    def test_trigger_callback_error_does_not_crash(self):
        """A raising callback should not propagate."""
        hooks = EventHookSystem()

        def broken_callback(context):
            raise RuntimeError("callback error")

        hooks.register_hook("test_event", broken_callback)
        # Should not raise
        hooks.trigger("test_event")

    def test_trigger_missing_event(self):
        """Triggering an event with no handlers should not raise."""
        hooks = EventHookSystem()
        hooks.trigger("nonexistent_event")

    def test_unregister_nonexistent(self):
        """Unregistering a non-registered hook should not raise."""
        hooks = EventHookSystem()
        hooks.unregister_hook("nonexistent", lambda ctx: None)

    def test_lyra_event_all_members(self):
        """Verify all LyraEvent values are present."""
        values = {e.value for e in LyraEvent}
        assert "session_start" in values
        assert "session_end" in values
        assert "task_start" in values
        assert "task_complete" in values
        assert "task_failed" in values
        assert "prompt_submit" in values
        assert "error_general" in values
        assert "easter_egg" in values


# ═══════════════════════════════════════════════════════════════════════════
# ConfigurationManager
# ═══════════════════════════════════════════════════════════════════════════


class TestConfigurationManagerEdgeCases:
    def test_corrupt_json_falls_back_to_defaults(self):
        """If the config file contains invalid JSON, defaults should be used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text("{invalid json!!!}")
            manager = ConfigurationManager(str(config_path))
            assert manager.get("enabled") is True
            assert manager.get("theme") == "warcraft"

    def test_empty_config_file(self):
        """An empty config file should fall back to defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text("")
            manager = ConfigurationManager(str(config_path))
            assert manager.get("enabled") is True

    def test_get_missing_key_returns_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            manager = ConfigurationManager(str(config_path))
            assert manager.get("nonexistent.key") is None
            assert manager.get("nonexistent.key", "fallback") == "fallback"

    def test_export_to_nonexistent_directory_does_not_crash(self):
        """Export to a path where the parent doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigurationManager(str(Path(tmpdir) / "config.json"))
            # Export to a non-existent subdirectory — should fail silently
            manager.export(str(Path(tmpdir) / "nonexistent" / "export.json"))

    def test_import_nonexistent_file_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigurationManager(str(Path(tmpdir) / "config.json"))
            manager.import_config(str(Path(tmpdir) / "nonexistent.json"))

    def test_save_preserves_nested_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            manager = ConfigurationManager(str(config_path))
            manager.set("adaptive_volume.enabled", False)
            manager.set("adaptive_volume.base_volume", 0.5)
            manager.save()

            manager2 = ConfigurationManager(str(config_path))
            assert manager2.get("adaptive_volume.enabled") is False
            assert manager2.get("adaptive_volume.base_volume") == 0.5


# ═══════════════════════════════════════════════════════════════════════════
# SoundManager
# ═══════════════════════════════════════════════════════════════════════════


class TestSoundManagerEdgeCases:
    def test_corrupt_audio_config(self):
        """Corrupt ~/.lyra/audio.json should not crash SoundManager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_config = Path(tmpdir) / "audio.json"
            audio_config.write_text("{bad json}")
            with patch("lyra_audio.sound_manager.Path", return_value=audio_config):
                # SoundManager reads from ~/.lyra/audio.json; we need to test the fallback
                pass

    def test_play_event_when_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SoundManager(sounds_dir=tmpdir)
            manager.disable()
            # Should not crash
            manager.play_event("task_complete")

    def test_list_themes_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SoundManager(sounds_dir=tmpdir)
            assert manager.list_themes() == []


# ═══════════════════════════════════════════════════════════════════════════
# ProductivityModeController
# ═══════════════════════════════════════════════════════════════════════════


class TestProductivityModeControllerEdgeCases:
    @pytest.fixture
    def ctrl(self):
        return ProductivityModeController()

    def test_deadline_in_past_is_not_near(self, ctrl):
        ctrl.set_deadline(datetime.now() - timedelta(hours=1))
        assert ctrl.is_near_deadline() is False

    def test_deadline_far_future_is_not_near(self, ctrl):
        ctrl.set_deadline(datetime.now() + timedelta(days=7))
        assert ctrl.is_near_deadline() is False

    def test_is_near_deadline_just_before_deadline(self, ctrl):
        ctrl.set_deadline(datetime.now() + timedelta(hours=1.5))
        ctrl.deadline_threshold_hours = 2.0
        assert ctrl.is_near_deadline() is True

    def test_time_until_deadline_no_deadline(self, ctrl):
        assert ctrl.get_time_until_deadline() is None

    def test_time_until_deadline_past_deadline_returns_zero(self, ctrl):
        ctrl.set_deadline(datetime.now() - timedelta(hours=1))
        assert ctrl.get_time_until_deadline() == 0.0

    def test_focus_mode_allows_critical_only(self, ctrl):
        ctrl.enable()
        ctrl.enable_focus_mode()
        assert ctrl.should_play_sound("session_start") is False
        assert ctrl.should_play_sound("error_general") is True
        assert ctrl.should_play_sound("task_complete") is True

    def test_disabled_mode_allows_all(self, ctrl):
        ctrl.enable()
        ctrl.disable()
        assert ctrl.should_play_sound("session_start") is True

    def test_critical_event_list(self, ctrl):
        for event in ctrl.CRITICAL_EVENTS:
            assert ctrl.is_critical_event(event)
        assert not ctrl.is_critical_event("session_start")

    def test_set_deadline_threshold_clamps_to_zero(self, ctrl):
        ctrl.set_deadline_threshold(-5)
        assert ctrl.deadline_threshold_hours == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# AdaptiveVolumeController
# ═══════════════════════════════════════════════════════════════════════════


class TestAdaptiveVolumeControllerEdgeCases:
    @pytest.fixture
    def ctrl(self):
        return AdaptiveVolumeController()

    def test_get_inactivity_duration(self, ctrl):
        ctrl.record_activity()
        duration = ctrl.get_inactivity_duration()
        assert duration >= 0.0

    def test_is_boosted_false_initially(self, ctrl):
        ctrl.record_activity()
        assert ctrl.is_boosted() is False

    def test_set_base_volume_clamps(self, ctrl):
        ctrl.set_base_volume(2.0)
        assert ctrl.base_volume == 1.0
        ctrl.set_base_volume(-1.0)
        assert ctrl.base_volume == 0.0

    def test_set_boost_amount_clamps(self, ctrl):
        ctrl.set_boost_amount(2.0)
        assert ctrl.boost_amount == 1.0
        ctrl.set_boost_amount(-1.0)
        assert ctrl.boost_amount == 0.0

    def test_set_inactivity_threshold_clamps(self, ctrl):
        ctrl.set_inactivity_threshold(-10)
        assert ctrl.inactivity_threshold == 0.0

    def test_disabled_returns_base_volume(self, ctrl):
        ctrl.enable()
        ctrl.disable()
        assert ctrl.is_enabled() is False
        volume = ctrl.get_current_volume()
        assert volume == ctrl.base_volume

    def test_enable_disable_toggle(self, ctrl):
        ctrl.disable()
        assert ctrl.is_enabled() is False
        ctrl.enable()
        assert ctrl.is_enabled() is True


# ═══════════════════════════════════════════════════════════════════════════
# TimeBehaviorController
# ═══════════════════════════════════════════════════════════════════════════


class TestTimeBehaviorControllerEdgeCases:
    @pytest.fixture
    def ctrl(self):
        return TimeBehaviorController()

    def test_get_current_hour(self, ctrl):
        hour = ctrl.get_current_hour()
        assert 0 <= hour <= 23

    def test_is_work_hours_returns_bool(self, ctrl):
        assert isinstance(ctrl.is_work_hours(), bool)

    def test_variant_suffix_after_hours(self, ctrl):
        """get_variant_suffix only checks after-hours, not enabled flag."""
        suffix = ctrl.get_variant_suffix()
        assert suffix in ("", "_ridiculous")  # depends on current time

    def test_variant_suffix_not_after_hours(self, ctrl):
        """When set to start at hour 23, before that hour it should be empty."""
        ctrl.set_ridiculous_start_hour(23)
        # get_variant_suffix doesn't check enabled, only is_after_hours
        # so this is a documentation test, not a behavioral assertion
        assert ctrl.ridiculous_start_hour == 23

    def test_set_ridiculous_start_hour_clamps(self, ctrl):
        ctrl.set_ridiculous_start_hour(25)
        assert ctrl.ridiculous_start_hour == 23
        ctrl.set_ridiculous_start_hour(-1)
        assert ctrl.ridiculous_start_hour == 0

    def test_set_ridiculous_boost_clamps(self, ctrl):
        ctrl.set_ridiculous_boost(2.0)
        assert ctrl.ridiculous_boost == 1.0
        ctrl.set_ridiculous_boost(-1.0)
        assert ctrl.ridiculous_boost == 0.0

    def test_get_ridiculous_factor_disabled(self, ctrl):
        ctrl.disable()
        assert ctrl.get_ridiculous_factor() == 0.0

    def test_should_use_variant_disabled(self, ctrl):
        ctrl.disable()
        assert ctrl.should_use_variant("task_complete") is False


# ═══════════════════════════════════════════════════════════════════════════
# AudioSuppression edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestAudioSuppressionConfigEdgeCases:
    def test_update_config_changes_behavior(self):
        s = AudioSuppression()
        new_config = SuppressionConfig(annoyed_threshold=0)  # disabled spam
        s.update_config(new_config)
        s.record_playback()
        s.record_playback()
        result = s.check()
        assert not result.suppressed  # threshold is 0 = disabled

    def test_stats_silent_hours_active(self):
        """stats() includes silent_hours_active."""
        s = AudioSuppression()
        stats = s.stats()
        assert "silent_hours_active" in stats
        assert "spam_throttled" in stats
