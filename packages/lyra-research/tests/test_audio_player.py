"""
Tests for Audio Player (Funny Sounds Phase 0)

Tests cross-platform audio playback.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
from lyra_research.sounds.audio_player import AudioPlayer, AudioBackend


class TestAudioPlayer:
    """Test audio player"""

    @patch('platform.system')
    def test_backend_detection_macos(self, mock_system):
        """Test backend detection on macOS"""
        mock_system.return_value = "Darwin"
        player = AudioPlayer()
        assert player.backend == AudioBackend.AFPLAY

    @patch('platform.system')
    def test_backend_detection_linux_pulseaudio(self, mock_system):
        """Test backend detection on Linux with PulseAudio"""
        mock_system.return_value = "Linux"
        player = AudioPlayer()
        # Will be PAPLAY if paplay exists, otherwise APLAY
        assert player.backend in [AudioBackend.PAPLAY, AudioBackend.APLAY]

    @patch('platform.system')
    def test_backend_detection_windows(self, mock_system):
        """Test backend detection on Windows"""
        mock_system.return_value = "Windows"
        player = AudioPlayer()
        assert player.backend == AudioBackend.POWERSHELL

    def test_command_building_afplay(self):
        """Test command building for afplay (macOS)"""
        with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
            sound_path = Path(f.name)
            player = AudioPlayer()
            player.backend = AudioBackend.AFPLAY

            command = player._build_command(sound_path, 0.5)
            assert command[0] == "afplay"
            assert "-v" in command
            assert "0.5" in command
            assert str(sound_path) in command

    def test_command_building_paplay(self):
        """Test command building for paplay (Linux PulseAudio)"""
        with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
            sound_path = Path(f.name)
            player = AudioPlayer()
            player.backend = AudioBackend.PAPLAY

            command = player._build_command(sound_path, 0.5)
            assert command[0] == "paplay"
            assert "--volume" in command
            # 0.5 * 65536 = 32768
            assert "32768" in command

    def test_command_building_aplay(self):
        """Test command building for aplay (Linux ALSA)"""
        with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
            sound_path = Path(f.name)
            player = AudioPlayer()
            player.backend = AudioBackend.APLAY

            command = player._build_command(sound_path, 0.5)
            assert command[0] == "aplay"
            assert str(sound_path) in command

    def test_play_file_not_found(self):
        """Test play with non-existent file"""
        player = AudioPlayer()
        with pytest.raises(FileNotFoundError):
            player.play(Path("/nonexistent/file.mp3"))

    @patch('subprocess.Popen')
    def test_play_background(self, mock_popen):
        """Test play in background mode"""
        with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
            sound_path = Path(f.name)
            player = AudioPlayer()

            result = player.play(sound_path, volume=0.5, background=True)
            mock_popen.assert_called_once()
            # Returns process handle
            assert result is not None

    @patch('subprocess.run')
    def test_play_foreground(self, mock_run):
        """Test play in foreground mode"""
        with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
            sound_path = Path(f.name)
            player = AudioPlayer()

            result = player.play(sound_path, volume=0.5, background=False)
            mock_run.assert_called_once()
            # Returns None
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
