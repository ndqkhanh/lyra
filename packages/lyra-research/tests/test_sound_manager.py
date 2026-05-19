"""
Tests for Sound Manager (Funny Sounds Phase 0)

Tests main sound management system.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
from lyra_research.sounds.sound_manager import SoundManager
from lyra_research.sounds.config import SoundConfig


class TestSoundManager:
    """Test sound manager"""

    def test_initialization(self):
        """Test sound manager initialization"""
        manager = SoundManager()
        assert manager.config is not None
        assert manager.player is not None
        assert manager.theme_manager is not None
        assert manager.muted is False

    def test_mute_unmute(self):
        """Test mute and unmute"""
        manager = SoundManager()

        # Initially not muted
        assert not manager.muted

        # Mute
        manager.mute()
        assert manager.muted

        # Unmute
        manager.unmute()
        assert not manager.muted

    def test_toggle_mute(self):
        """Test toggle mute"""
        manager = SoundManager()

        # Toggle to muted
        result = manager.toggle_mute()
        assert result is True
        assert manager.muted

        # Toggle to unmuted
        result = manager.toggle_mute()
        assert result is False
        assert not manager.muted

    def test_set_volume(self):
        """Test setting volume"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sounds_config.json"
            config = SoundConfig(config_path)
            manager = SoundManager(config)

            manager.set_volume(0.7)
            assert manager.config.volume == 0.7

    def test_set_volume_clamps_to_range(self):
        """Test volume is clamped to 0.0-1.0"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sounds_config.json"
            config = SoundConfig(config_path)
            manager = SoundManager(config)

            # Too high
            manager.set_volume(1.5)
            assert manager.config.volume == 1.0

            # Too low
            manager.set_volume(-0.5)
            assert manager.config.volume == 0.0

    def test_set_theme(self):
        """Test setting theme"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sounds_config.json"
            config = SoundConfig(config_path)
            manager = SoundManager(config)

            manager.set_theme("aoe")
            assert manager.config.theme == "aoe"

    def test_set_invalid_theme_ignored(self):
        """Test setting invalid theme is ignored"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sounds_config.json"
            config = SoundConfig(config_path)
            manager = SoundManager(config)

            original_theme = manager.config.theme
            manager.set_theme("nonexistent")
            # Theme should not change
            assert manager.config.theme == original_theme

    @patch('lyra_research.sounds.sound_manager.AudioPlayer')
    def test_play_event_when_muted(self, mock_audio_player):
        """Test play event when muted"""
        manager = SoundManager()
        manager.mute()

        manager.play_event("task_complete")

        # Should not play
        mock_audio_player.return_value.play.assert_not_called()

    @patch('lyra_research.sounds.sound_manager.AudioPlayer')
    def test_play_event_when_disabled(self, mock_audio_player):
        """Test play event when disabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sounds_config.json"
            config = SoundConfig(config_path)
            config.enabled = False
            manager = SoundManager(config)

            manager.play_event("task_complete")

            # Should not play
            mock_audio_player.return_value.play.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
