"""Tests for sound pack CLI."""

import tempfile
from pathlib import Path

from lyra_audio.sound_cli import SoundPackCLI


def test_sound_cli_init():
    """Test CLI initialization."""
    cli = SoundPackCLI()
    assert cli.manager is not None
    assert cli.loader is not None


def test_sound_cli_on(capsys):
    """Test on command."""
    cli = SoundPackCLI()
    cli.run(["on"])
    captured = capsys.readouterr()
    assert "enabled" in captured.out.lower()


def test_sound_cli_off(capsys):
    """Test off command."""
    cli = SoundPackCLI()
    cli.run(["off"])
    captured = capsys.readouterr()
    assert "disabled" in captured.out.lower()


def test_sound_cli_list(capsys):
    """Test list command."""
    cli = SoundPackCLI()
    cli.run(["list"])
    captured = capsys.readouterr()
    # Should show available themes or "No themes found"
    assert "theme" in captured.out.lower() or "no themes" in captured.out.lower()


def test_sound_cli_status(capsys):
    """Test status command."""
    cli = SoundPackCLI()
    cli.run(["status"])
    captured = capsys.readouterr()
    assert "Sound System Status" in captured.out
    assert "Status:" in captured.out
    assert "Theme:" in captured.out


def test_sound_cli_create():
    """Test create command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cli = SoundPackCLI()
        cli.manager.sounds_dir = Path(tmpdir)
        cli.loader.sounds_dir = Path(tmpdir)

        cli.run(["create", "test_pack"])

        pack_dir = Path(tmpdir) / "test_pack"
        assert pack_dir.exists()
        assert (pack_dir / "manifest.json").exists()


def test_sound_cli_validate(capsys):
    """Test validate command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cli = SoundPackCLI()
        cli.manager.sounds_dir = Path(tmpdir)
        cli.loader.sounds_dir = Path(tmpdir)

        # Create valid pack
        cli.run(["create", "valid_pack"])

        # Create placeholder sound files
        pack_dir = Path(tmpdir) / "valid_pack"
        (pack_dir / "session_start.mp3").touch()
        (pack_dir / "task_complete.mp3").touch()
        (pack_dir / "error_general.mp3").touch()

        # Validate should pass
        cli.run(["validate", "valid_pack"])
        captured = capsys.readouterr()
        assert "valid" in captured.out.lower()


def test_sound_cli_test(capsys):
    """Test test command."""
    cli = SoundPackCLI()
    cli.run(["test", "task_complete"])
    captured = capsys.readouterr()
    assert "Testing sound" in captured.out
