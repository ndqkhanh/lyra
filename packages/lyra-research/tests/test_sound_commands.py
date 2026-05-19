"""
Tests for Sound CLI Commands (Funny Sounds Phase 4)

Tests command-line interface for sound management.
"""

import pytest
from click.testing import CliRunner
from pathlib import Path
import tempfile
from lyra_research.cli.sound_commands import sounds
from lyra_research.sounds.config import SoundConfig


class TestSoundCLI:
    """Test sound CLI commands"""

    def test_enable_command(self):
        """Test enable command"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(sounds, ['enable'])
            assert result.exit_code == 0
            assert "Sounds enabled" in result.output

    def test_disable_command(self):
        """Test disable command"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(sounds, ['disable'])
            assert result.exit_code == 0
            assert "Sounds disabled" in result.output

    def test_mute_command(self):
        """Test mute command"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(sounds, ['mute'])
            assert result.exit_code == 0
            assert "muted" in result.output.lower()

    def test_unmute_command(self):
        """Test unmute command"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(sounds, ['unmute'])
            assert result.exit_code == 0
            assert "unmuted" in result.output.lower()

    def test_theme_command_valid(self):
        """Test theme command with valid theme"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(sounds, ['theme', 'aoe'])
            assert result.exit_code == 0
            assert "Theme set to: aoe" in result.output

    def test_theme_command_invalid(self):
        """Test theme command with invalid theme"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(sounds, ['theme', 'nonexistent'])
            assert result.exit_code == 0
            assert "Unknown theme" in result.output

    def test_themes_command(self):
        """Test themes list command"""
        runner = CliRunner()
        result = runner.invoke(sounds, ['themes'])
        assert result.exit_code == 0
        assert "warcraft" in result.output
        assert "aoe" in result.output
        assert "memes" in result.output
        assert "minimal" in result.output

    def test_volume_command_valid(self):
        """Test volume command with valid value"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(sounds, ['volume', '0.7'])
            assert result.exit_code == 0
            assert "Volume set to: 0.7" in result.output

    def test_volume_command_too_high(self):
        """Test volume command with value too high"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(sounds, ['volume', '1.5'])
            assert result.exit_code == 0
            assert "must be between" in result.output

    def test_volume_command_too_low(self):
        """Test volume command with value too low"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Use '--' to separate options from arguments
            result = runner.invoke(sounds, ['volume', '--', '-0.5'])
            assert result.exit_code == 0
            assert "must be between" in result.output

    def test_test_command(self):
        """Test test play command"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(sounds, ['test', 'task_complete'])
            assert result.exit_code == 0
            assert "Playing: task_complete" in result.output

    def test_status_command(self):
        """Test status command"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(sounds, ['status'])
            assert result.exit_code == 0
            assert "Sounds:" in result.output
            assert "Theme:" in result.output
            assert "Volume:" in result.output
            assert "Muted:" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
