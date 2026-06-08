"""Comprehensive tests for the voice pack / sound effects module.

Tests SoundMapping, VoicePack, SoundEffectEngine, HookEvent,
and all bundled voice packs.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lyra.voice.sound_effects import (
    BUNDLED_PACKS,
    HookEvent,
    SoundEffectEngine,
    SoundMapping,
    VoicePack,
)


# ===================================================================
# HookEvent tests
# ===================================================================


class TestHookEvent:
    """Tests for the HookEvent enum."""

    def test_values(self) -> None:
        assert HookEvent.SESSION_START.value == "session_start"
        assert HookEvent.ANSWER_COMPLETE.value == "answer_complete"
        assert HookEvent.ERROR.value == "error"
        assert HookEvent.LONG_TASK_DONE.value == "long_task_done"
        assert HookEvent.TOOL_CALL.value == "tool_call"
        assert HookEvent.TOOL_RESULT.value == "tool_result"
        assert HookEvent.AGENT_PAUSED.value == "agent_paused"
        assert HookEvent.AGENT_NEEDS_INPUT.value == "agent_needs_input"
        assert HookEvent.SESSION_END.value == "session_end"

    def test_all_events_unique(self) -> None:
        values = [e.value for e in HookEvent]
        assert len(values) == len(set(values))

    def test_is_str_enum(self) -> None:
        assert issubclass(HookEvent, str)


# ===================================================================
# SoundMapping tests
# ===================================================================


class TestSoundMapping:
    """Tests for the SoundMapping dataclass."""

    def test_audio_file_only(self) -> None:
        sm = SoundMapping(event=HookEvent.SESSION_START, audio_file="chimes/start.wav")
        assert sm.event == HookEvent.SESSION_START
        assert sm.audio_file == "chimes/start.wav"
        assert sm.tts_phrase is None
        assert sm.volume == 1.0

    def test_tts_phrase_only(self) -> None:
        sm = SoundMapping(event=HookEvent.ERROR, tts_phrase="Something went wrong")
        assert sm.tts_phrase == "Something went wrong"
        assert sm.audio_file is None

    def test_both_set_uses_audio_file(self) -> None:
        """When both audio_file and tts_phrase are set, audio_file takes priority."""
        sm = SoundMapping(
            event=HookEvent.SESSION_START,
            audio_file="beep.wav",
            tts_phrase="Starting",
        )
        assert sm.audio_file == "beep.wav"
        assert sm.tts_phrase == "Starting"

    def test_neither_set_raises(self) -> None:
        with pytest.raises(ValueError, match="must have"):
            SoundMapping(event=HookEvent.SESSION_START)

    def test_custom_volume(self) -> None:
        sm = SoundMapping(event=HookEvent.ERROR, tts_phrase="Error", volume=0.5)
        assert sm.volume == 0.5

    def test_is_frozen(self) -> None:
        sm = SoundMapping(event=HookEvent.SESSION_START, audio_file="beep.wav")
        with pytest.raises(AttributeError):
            sm.event = HookEvent.ERROR  # type: ignore[misc]


# ===================================================================
# VoicePack tests
# ===================================================================


class TestVoicePack:
    """Tests for the VoicePack dataclass."""

    def test_fields(self) -> None:
        pack = VoicePack(name="test", display_name="Test Pack")
        assert pack.name == "test"
        assert pack.display_name == "Test Pack"
        assert pack.description == ""
        assert pack.sounds == []

    def test_get_sound_found(self) -> None:
        sm = SoundMapping(event=HookEvent.SESSION_START, tts_phrase="Hello")
        pack = VoicePack(name="test", display_name="Test", sounds=[sm])
        result = pack.get_sound(HookEvent.SESSION_START)
        assert result is sm

    def test_get_sound_not_found(self) -> None:
        pack = VoicePack(name="test", display_name="Test")
        result = pack.get_sound(HookEvent.ERROR)
        assert result is None

    def test_get_sound_multiple_events(self) -> None:
        sounds = [
            SoundMapping(event=HookEvent.SESSION_START, tts_phrase="Start"),
            SoundMapping(event=HookEvent.ERROR, tts_phrase="Error"),
            SoundMapping(event=HookEvent.ANSWER_COMPLETE, tts_phrase="Done"),
        ]
        pack = VoicePack(name="test", display_name="Test", sounds=sounds)
        assert pack.get_sound(HookEvent.ERROR).tts_phrase == "Error"  # type: ignore[union-attr]
        assert pack.get_sound(HookEvent.SESSION_END) is None

    def test_to_dict(self) -> None:
        sm = SoundMapping(
            event=HookEvent.SESSION_START,
            audio_file="start.wav",
            volume=0.8,
        )
        pack = VoicePack(
            name="test",
            display_name="Test Pack",
            description="A test pack.",
            sounds=[sm],
        )
        d = pack.to_dict()
        assert d["name"] == "test"
        assert d["display_name"] == "Test Pack"
        assert d["description"] == "A test pack."
        assert len(d["sounds"]) == 1
        assert d["sounds"][0]["event"] == "session_start"
        assert d["sounds"][0]["audio_file"] == "start.wav"
        assert d["sounds"][0]["volume"] == 0.8

    def test_from_dict(self) -> None:
        data = {
            "name": "custom",
            "display_name": "Custom",
            "description": "Custom pack",
            "sounds": [
                {
                    "event": "session_start",
                    "audio_file": "beep.wav",
                    "volume": 0.5,
                },
                {
                    "event": "error",
                    "tts_phrase": "Oops!",
                },
            ],
        }
        pack = VoicePack.from_dict(data)
        assert pack.name == "custom"
        assert pack.display_name == "Custom"
        assert len(pack.sounds) == 2
        assert pack.sounds[0].event == HookEvent.SESSION_START
        assert pack.sounds[0].audio_file == "beep.wav"
        assert pack.sounds[0].volume == 0.5
        assert pack.sounds[1].event == HookEvent.ERROR
        assert pack.sounds[1].tts_phrase == "Oops!"

    def test_from_dict_missing_description(self) -> None:
        data = {
            "name": "min",
            "display_name": "Min",
            "sounds": [],
        }
        pack = VoicePack.from_dict(data)
        assert pack.description == ""

    def test_from_dict_missing_optional_fields(self) -> None:
        """get() should default missing optional fields."""
        data = {
            "name": "test",
            "display_name": "Test",
            "sounds": [
                {"event": "session_start", "tts_phrase": "Hello"},
            ],
        }
        pack = VoicePack.from_dict(data)
        assert pack.sounds[0].audio_file is None
        assert pack.sounds[0].volume == 1.0  # default volume

    def test_from_dict_missing_required_fields_raises(self) -> None:
        """If both audio_file and tts_phrase are missing, should raise."""
        data = {
            "name": "test",
            "display_name": "Test",
            "sounds": [
                {"event": "session_start"},
            ],
        }
        with pytest.raises(ValueError, match="must have"):
            VoicePack.from_dict(data)


# ===================================================================
# Bundled voice pack tests
# ===================================================================


class TestBundledPacks:
    """Tests for all bundled voice packs."""

    def test_all_bundled_packs_have_name(self) -> None:
        for name, pack in BUNDLED_PACKS.items():
            assert pack.name == name
            assert pack.display_name

    def test_all_bundled_packs_have_sounds(self) -> None:
        for name, pack in BUNDLED_PACKS.items():
            assert len(pack.sounds) > 0, f"Pack '{name}' has no sounds"

    def test_warcraft_peon_pack(self) -> None:
        pack = BUNDLED_PACKS["warcraft-peon"]
        assert pack.name == "warcraft-peon"
        assert pack.get_sound(HookEvent.SESSION_START) is not None
        assert pack.get_sound(HookEvent.ANSWER_COMPLETE) is not None
        assert pack.get_sound(HookEvent.ERROR) is not None
        assert pack.get_sound(HookEvent.LONG_TASK_DONE) is not None
        assert pack.get_sound(HookEvent.SESSION_END) is not None
        # All sounds use TTS phrases
        for s in pack.sounds:
            assert s.tts_phrase is not None

    def test_jarvis_pack(self) -> None:
        pack = BUNDLED_PACKS["jarvis"]
        assert pack.name == "jarvis"
        assert pack.get_sound(HookEvent.AGENT_NEEDS_INPUT) is not None
        assert pack.get_sound(HookEvent.TOOL_RESULT) is None  # Not mapped

    def test_samantha_pack(self) -> None:
        pack = BUNDLED_PACKS["samantha"]
        assert pack.name == "samantha"
        for s in pack.sounds:
            assert s.tts_phrase is not None

    def test_minimal_pack(self) -> None:
        pack = BUNDLED_PACKS["minimal"]
        assert pack.name == "minimal"
        # Minimal uses audio files, not TTS phrases
        for s in pack.sounds:
            assert s.audio_file is not None
            assert s.tts_phrase is None

    def test_minimal_pack_volumes(self) -> None:
        pack = BUNDLED_PACKS["minimal"]
        for s in pack.sounds:
            assert 0.0 <= s.volume <= 1.0
        assert pack.get_sound(HookEvent.ERROR).volume > pack.get_sound(HookEvent.ANSWER_COMPLETE).volume

    def test_all_bundled_pack_names(self) -> None:
        expected = {"warcraft-peon", "jarvis", "samantha", "minimal"}
        assert set(BUNDLED_PACKS.keys()) == expected


# ===================================================================
# SoundEffectEngine tests
# ===================================================================


class TestSoundEffectEngine:
    """Tests for the SoundEffectEngine."""

    @pytest.fixture
    def engine(self) -> SoundEffectEngine:
        return SoundEffectEngine(active_pack="minimal")

    def test_default_pack(self) -> None:
        engine = SoundEffectEngine()
        assert engine.active_pack == "minimal"

    def test_custom_pack(self) -> None:
        engine = SoundEffectEngine(active_pack="jarvis")
        assert engine.active_pack == "jarvis"

    def test_on_event_returns_sound(self, engine: SoundEffectEngine) -> None:
        result = engine.on_event(HookEvent.SESSION_START)
        assert isinstance(result, SoundMapping)
        assert result.event == HookEvent.SESSION_START

    def test_on_event_unmapped(self, engine: SoundEffectEngine) -> None:
        """Events not in the active pack should return None."""
        # Minimal pack doesn't have TOOL_CALL
        result = engine.on_event(HookEvent.TOOL_CALL)
        assert result is None

    def test_on_event_no_pack(self) -> None:
        """With no matching pack, return None."""
        engine = SoundEffectEngine(active_pack="nonexistent")
        # Since _custom_packs is empty, this should return None
        result = engine.on_event(HookEvent.SESSION_START)
        assert result is None

    def test_set_pack(self, engine: SoundEffectEngine) -> None:
        engine.set_pack("jarvis")
        assert engine.active_pack == "jarvis"

    def test_set_pack_unknown_raises(self, engine: SoundEffectEngine) -> None:
        with pytest.raises(ValueError, match="Unknown voice pack"):
            engine.set_pack("nonexistent")

    def test_set_pack_to_same(self, engine: SoundEffectEngine) -> None:
        engine.set_pack("minimal")  # Should not raise

    def test_set_pack_after_custom(self, engine: SoundEffectEngine) -> None:
        """Should be able to switch back to bundled after setting custom."""
        # Register a custom pack first
        pack = VoicePack(name="custom-pack", display_name="Custom")
        engine._custom_packs["custom-pack"] = pack
        engine.set_pack("custom-pack")
        assert engine.active_pack == "custom-pack"
        # Switch back
        engine.set_pack("minimal")
        assert engine.active_pack == "minimal"

    def test_load_custom_pack_json(self, engine: SoundEffectEngine) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({
                "name": "custom-pack",
                "display_name": "Custom Pack",
                "description": "A custom pack",
                "sounds": [
                    {
                        "event": "session_start",
                        "tts_phrase": "Custom start!",
                        "volume": 0.8,
                    },
                ],
            }, f)
            path = Path(f.name)

        try:
            pack = engine.load_custom_pack(path)
            assert pack.name == "custom-pack"
            assert "custom-pack" in engine._custom_packs
            assert pack.sounds[0].tts_phrase == "Custom start!"
        finally:
            path.unlink()

    def test_load_custom_pack_not_found(self, engine: SoundEffectEngine) -> None:
        with pytest.raises(FileNotFoundError):
            engine.load_custom_pack(Path("/nonexistent/pack.json"))

    def test_load_custom_pack_malformed(self, engine: SoundEffectEngine) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("not valid json{")
            path = Path(f.name)

        try:
            with pytest.raises(json.JSONDecodeError):
                engine.load_custom_pack(path)
        finally:
            path.unlink()

    def test_load_custom_pack_missing_name(self, engine: SoundEffectEngine) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"display_name": "No Name", "sounds": []}, f)
            path = Path(f.name)

        try:
            with pytest.raises(KeyError):
                engine.load_custom_pack(path)
        finally:
            path.unlink()

    def test_register_tts_callback(self, engine: SoundEffectEngine) -> None:
        callback = MagicMock()
        engine.register_tts_callback(callback)
        assert engine._tts_callback is callback

    def test_play_triggers_tts_callback(self) -> None:
        """When a TTS phrase is mapped, the callback should be called."""
        callback = MagicMock()
        engine = SoundEffectEngine(active_pack="jarvis")
        engine.register_tts_callback(callback)

        engine.on_event(HookEvent.SESSION_START)
        callback.assert_called_once()
        args = callback.call_args[0][0]
        assert isinstance(args, str)

    def test_play_audio_file_does_not_call_tts(self) -> None:
        """When audio_file is used, TTS callback should NOT be called."""
        callback = MagicMock()
        engine = SoundEffectEngine(active_pack="minimal")
        engine.register_tts_callback(callback)

        engine.on_event(HookEvent.SESSION_START)
        callback.assert_not_called()

    def test_list_packs(self, engine: SoundEffectEngine) -> None:
        packs = engine.list_packs()
        assert len(packs) >= 4  # At least the bundled ones
        names = [p["name"] for p in packs]
        assert "minimal" in names
        assert "jarvis" in names
        assert "warcraft-peon" in names
        assert "samantha" in names

    def test_list_packs_includes_custom(self, engine: SoundEffectEngine) -> None:
        engine._custom_packs["my-pack"] = VoicePack(
            name="my-pack", display_name="My Pack"
        )
        packs = engine.list_packs()
        custom = [p for p in packs if p["source"] == "custom"]
        assert len(custom) == 1
        assert custom[0]["name"] == "my-pack"

    def test_on_event_with_sound(self, engine: SoundEffectEngine) -> None:
        """on_event with a matching event should trigger audio or TTS."""
        engine.active_pack = "jarvis"
        engine._tts_callback = MagicMock()
        result = engine.on_event(HookEvent.SESSION_START)
        assert result is not None
        engine._tts_callback.assert_called_once()


# ===================================================================
# Edge cases
# ===================================================================


class TestSoundEffectsEdgeCases:
    def test_default_engine_no_pack_changes(self) -> None:
        engine = SoundEffectEngine()
        assert engine.active_pack == "minimal"

    def test_on_event_with_unregistered_pack(self) -> None:
        engine = SoundEffectEngine(active_pack="made-up")
        result = engine.on_event(HookEvent.SESSION_START)
        assert result is None

    def test_get_active_pack_bundled(self) -> None:
        engine = SoundEffectEngine(active_pack="minimal")
        pack = engine._get_active_pack()
        assert pack.name == "minimal"

    def test_get_active_pack_custom(self) -> None:
        engine = SoundEffectEngine(active_pack="custom-x")
        engine._custom_packs["custom-x"] = VoicePack(
            name="custom-x", display_name="Custom X"
        )
        pack = engine._get_active_pack()
        assert pack.name == "custom-x"

    def test_get_active_pack_none(self) -> None:
        engine = SoundEffectEngine(active_pack="ghost")
        pack = engine._get_active_pack()
        assert pack is None
