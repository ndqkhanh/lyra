"""Tests for SoundManager, SoundPack, AudioPlayer, and SoundEvent."""

import os
import tempfile
from unittest.mock import patch

from lyra_cli.sound_effects import (
    AudioPlayer,
    SoundEvent,
    SoundManager,
    SoundPack,
    get_sound_manager,
)


class TestSoundEvent:
    def test_event_values(self):
        assert SoundEvent.SESSION_START == "session_start"
        assert SoundEvent.USER_PROMPT == "user_prompt"
        assert SoundEvent.TOOL_START == "tool_start"
        assert SoundEvent.TOOL_SUCCESS == "tool_success"
        assert SoundEvent.TOOL_FAILURE == "tool_failure"
        assert SoundEvent.STOP == "stop"
        assert SoundEvent.PRE_COMPACT == "pre_compact"
        assert SoundEvent.ERROR == "error"
        assert SoundEvent.TASK_COMPLETE == "task_complete"

    def test_event_is_string(self):
        assert isinstance(SoundEvent.SESSION_START.value, str)


class TestSoundPack:
    def test_default_values(self):
        sp = SoundPack(name="test", description="test pack")
        assert sp.name == "test"
        assert sp.description == "test pack"
        assert sp.sounds == {}

    def test_get_existing_event(self):
        sp = SoundPack(
            name="test",
            description="desc",
            sounds={SoundEvent.SESSION_START: "/tmp/start.wav"},
        )
        assert sp.get(SoundEvent.SESSION_START) == "/tmp/start.wav"

    def test_get_missing_event(self):
        sp = SoundPack(name="test", description="desc")
        assert sp.get(SoundEvent.SESSION_START) is None

    def test_with_multiple_sounds(self):
        sp = SoundPack(
            name="full",
            description="full pack",
            sounds={
                SoundEvent.SESSION_START: "/tmp/start.wav",
                SoundEvent.STOP: "/tmp/stop.wav",
                SoundEvent.ERROR: "/tmp/error.wav",
            },
        )
        assert len(sp.sounds) == 3


class TestAudioPlayer:
    def test_detect_player(self):
        player = AudioPlayer()
        assert isinstance(player.available, bool)

    @patch("subprocess.Popen")
    def test_play_non_blocking(self, mock_popen):
        player = AudioPlayer()
        player._available = True
        player.play("/fake/path.wav")
        mock_popen.assert_called_once()

    @patch("subprocess.Popen", side_effect=OSError)
    def test_play_handles_error(self, _mock_popen):
        player = AudioPlayer()
        player._available = True
        player.play("/fake/path.wav")

    def test_play_when_unavailable(self):
        player = AudioPlayer()
        player._available = False
        player.play("/fake/path.wav")


class TestSoundManager:
    def _make_temp_wav(self) -> str:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.write(b"RIFF\x00\x00\x00\x00WAVE")
        tmp.close()
        return tmp.name

    def test_initial_state(self):
        sm = SoundManager()
        assert sm.enabled is False
        assert sm.active_pack_name is None
        assert len(sm.available_packs) >= 3

    def test_enable_disable_toggle(self):
        sm = SoundManager()
        assert sm.enabled is False
        sm.enable()
        assert sm.enabled is True
        sm.disable()
        assert sm.enabled is False

    def test_toggle(self):
        sm = SoundManager()
        assert sm.toggle() is True
        assert sm.enabled is True
        assert sm.toggle() is False
        assert sm.enabled is False

    def test_load_valid_pack(self):
        sm = SoundManager()
        assert sm.load_pack("retro") is True
        assert sm.active_pack_name == "retro"

    def test_load_invalid_pack(self):
        sm = SoundManager()
        assert sm.load_pack("nonexistent") is False
        assert sm.active_pack_name is None

    def test_dispatch_when_disabled(self):
        sm = SoundManager()
        sm.enable()
        sm.load_pack("retro")
        sm.disable()
        sm.dispatch(SoundEvent.SESSION_START)

    def test_dispatch_no_active_pack(self):
        sm = SoundManager()
        sm.enable()
        sm.dispatch(SoundEvent.SESSION_START)

    def test_dispatch_with_sound_file(self):
        sm = SoundManager()
        sm.enable()
        tmp_path = self._make_temp_wav()
        try:
            sp = SoundPack(
                name="test", description="test",
                sounds={SoundEvent.SESSION_START: tmp_path},
            )
            sm.register_pack(sp)
            sm.load_pack("test")
            sm.dispatch(SoundEvent.SESSION_START)
        finally:
            os.unlink(tmp_path)

    def test_register_custom_pack(self):
        sm = SoundManager()
        sp = SoundPack(name="custom", description="custom sounds")
        sm.register_pack(sp)
        assert "custom" in sm.available_packs

    def test_available_packs_includes_builtins(self):
        sm = SoundManager()
        packs = sm.available_packs
        assert "retro" in packs
        assert "minimal" in packs
        assert "sci-fi" in packs

    def test_on_event_hook(self):
        sm = SoundManager()
        called = []

        def hook():
            called.append(True)

        sm.on(SoundEvent.SESSION_START, hook)
        sm.enable()
        sm.load_pack("retro")
        sm.dispatch(SoundEvent.SESSION_START)
        assert len(called) == 1

    def test_event_hook_handles_exception(self):
        sm = SoundManager()
        called = []

        def good_hook():
            called.append(True)

        def bad_hook():
            raise RuntimeError("boom")

        sm.on(SoundEvent.SESSION_START, bad_hook)
        sm.on(SoundEvent.SESSION_START, good_hook)
        sm.enable()
        sm.load_pack("retro")
        sm.dispatch(SoundEvent.SESSION_START)
        assert len(called) == 1

    def test_generate_pack_skeleton(self):
        sm = SoundManager()
        with tempfile.TemporaryDirectory() as tmp:
            path = sm.generate_pack_skeleton("my-pack", tmp)
            assert path.exists()
            assert (path / "start.wav").exists()
            assert (path / "stop.wav").exists()
            assert (path / "README.md").exists()

    def test_load_pack_twice(self):
        sm = SoundManager()
        sm.load_pack("retro")
        sm.load_pack("minimal")
        assert sm.active_pack_name == "minimal"


class TestGetSoundManager:
    def test_returns_singleton(self):
        sm1 = get_sound_manager()
        sm2 = get_sound_manager()
        assert sm1 is sm2

    def test_initial_state_singleton(self):
        sm = get_sound_manager()
        assert isinstance(sm, SoundManager)
