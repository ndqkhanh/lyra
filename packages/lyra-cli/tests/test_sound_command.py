"""Tests for the /sound CLI command."""

import pytest
from typer.testing import CliRunner

from lyra_cli.cli.commands.sound import app
from lyra_cli.sound_effects import SoundEvent, get_sound_manager

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_sound_manager():
    """Reset the global sound manager before each test."""
    import lyra_cli.sound_effects as se

    se._sound_manager = None


class TestListPacks:
    def test_list_packs(self):
        result = runner.invoke(app, ["list-packs"])
        assert result.exit_code == 0
        assert "retro" in result.stdout
        assert "minimal" in result.stdout
        assert "sci-fi" in result.stdout

    def test_list_packs_shows_active(self):
        sm = get_sound_manager()
        sm.load_pack("retro")
        result = runner.invoke(app, ["list-packs"])
        assert result.exit_code == 0
        assert "(active)" in result.stdout


class TestSelect:
    def test_select_valid_pack(self):
        result = runner.invoke(app, ["select", "minimal"])
        assert result.exit_code == 0
        assert "selected" in result.stdout

    def test_select_invalid_pack(self):
        result = runner.invoke(app, ["select", "bogus"])
        assert result.exit_code == 0
        assert "Unknown pack" in result.stdout


class TestToggle:
    def test_toggle_on(self):
        sm = get_sound_manager()
        assert sm.enabled is False
        result = runner.invoke(app, ["toggle"])
        assert result.exit_code == 0
        assert sm.enabled is True
        assert "ON" in result.stdout

    def test_toggle_off(self):
        sm = get_sound_manager()
        sm.enable()
        result = runner.invoke(app, ["toggle"])
        assert result.exit_code == 0
        assert sm.enabled is False
        assert "OFF" in result.stdout


class TestOn:
    def test_on_command(self):
        sm = get_sound_manager()
        result = runner.invoke(app, ["on"])
        assert result.exit_code == 0
        assert sm.enabled is True


class TestOff:
    def test_off_command(self):
        sm = get_sound_manager()
        sm.enable()
        result = runner.invoke(app, ["off"])
        assert result.exit_code == 0
        assert sm.enabled is False


class TestPreview:
    def test_preview_valid_event(self):
        sm = get_sound_manager()
        sm.load_pack("retro")
        result = runner.invoke(app, ["preview", "session_start"])
        assert result.exit_code == 0

    def test_preview_invalid_event(self):
        sm = get_sound_manager()
        sm.load_pack("retro")
        result = runner.invoke(app, ["preview", "nonexistent"])
        assert result.exit_code == 1
        assert "Invalid event" in result.stdout

    def test_preview_no_active_pack(self):
        result = runner.invoke(app, ["preview", "stop"])
        assert result.exit_code == 1
        assert "No sound pack selected" in result.stdout

    def test_preview_default_event(self):
        sm = get_sound_manager()
        sm.load_pack("minimal")
        result = runner.invoke(app, ["preview"])
        assert result.exit_code == 0

    def test_preview_all_valid_events(self):
        sm = get_sound_manager()
        sm.load_pack("sci-fi")
        for event in SoundEvent:
            result = runner.invoke(app, ["preview", event.value])
            assert result.exit_code == 0


class TestSetup:
    def test_setup_creates_files(self, tmp_path, monkeypatch):
        import lyra_cli.generate_sounds as gs

        monkeypatch.setattr(gs, "generate_all_sounds", lambda target_dir=None: tmp_path)
        result = runner.invoke(app, ["setup"])
        assert result.exit_code == 0
        assert "Sound files generated" in result.stdout
