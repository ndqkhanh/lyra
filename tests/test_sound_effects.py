"""Tests for voice pack / sound effects system."""

from lyra.voice.sound_effects import (
    SoundEffectEngine,
    VoicePack,
    SoundMapping,
    HookEvent,
    BUNDLED_PACKS,
)


class TestVoicePacks:
    """Bundled voice pack tests."""

    def test_all_bundled_packs_loaded(self):
        assert "warcraft-peon" in BUNDLED_PACKS
        assert "jarvis" in BUNDLED_PACKS
        assert "samantha" in BUNDLED_PACKS
        assert "minimal" in BUNDLED_PACKS

    def test_warcraft_peon_has_session_start(self):
        pack = BUNDLED_PACKS["warcraft-peon"]
        sound = pack.get_sound(HookEvent.SESSION_START)
        assert sound is not None
        assert sound.tts_phrase == "Work complete!"

    def test_jarvis_has_answer_complete(self):
        pack = BUNDLED_PACKS["jarvis"]
        sound = pack.get_sound(HookEvent.ANSWER_COMPLETE)
        assert sound is not None
        assert sound.tts_phrase is not None
        assert "Task accomplished" in sound.tts_phrase

    def test_minimal_has_no_speech(self):
        pack = BUNDLED_PACKS["minimal"]
        for sound in pack.sounds:
            assert sound.tts_phrase is None  # Audio files only

    def test_unknown_event_returns_none(self):
        pack = BUNDLED_PACKS["warcraft-peon"]
        assert pack.get_sound(HookEvent.TOOL_CALL) is None

    def test_serialization_roundtrip(self):
        pack = BUNDLED_PACKS["jarvis"]
        d = pack.to_dict()
        restored = VoicePack.from_dict(d)
        assert restored.name == pack.name
        assert restored.display_name == pack.display_name
        assert len(restored.sounds) == len(pack.sounds)


class TestSoundEffectEngine:
    """Sound effect engine tests."""

    def test_default_pack_is_minimal(self):
        engine = SoundEffectEngine()
        assert engine.active_pack == "minimal"

    def test_set_pack_valid(self):
        engine = SoundEffectEngine()
        engine.set_pack("warcraft-peon")
        assert engine.active_pack == "warcraft-peon"

    def test_set_pack_invalid_raises(self):
        engine = SoundEffectEngine()
        try:
            engine.set_pack("nonexistent")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "nonexistent" in str(e)

    def test_on_event_returns_sound_mapping(self):
        engine = SoundEffectEngine()
        engine.set_pack("jarvis")
        result = engine.on_event(HookEvent.SESSION_START)
        assert result is not None
        assert result.tts_phrase == "At your service."

    def test_on_event_unmapped_returns_none(self):
        engine = SoundEffectEngine()
        engine.set_pack("minimal")
        result = engine.on_event(HookEvent.AGENT_NEEDS_INPUT)
        assert result is None

    def test_list_packs(self):
        engine = SoundEffectEngine()
        packs = engine.list_packs()
        assert len(packs) >= 4
        names = {p["name"] for p in packs}
        assert "warcraft-peon" in names
        assert "jarvis" in names


class TestSoundMapping:
    """Sound mapping tests."""

    def test_tts_only(self):
        sm = SoundMapping(
            event=HookEvent.SESSION_START,
            tts_phrase="Hello!",
        )
        assert sm.audio_file is None
        assert sm.tts_phrase == "Hello!"

    def test_audio_only(self):
        sm = SoundMapping(
            event=HookEvent.SESSION_START,
            audio_file="chimes/start.wav",
        )
        assert sm.tts_phrase is None
        assert sm.audio_file == "chimes/start.wav"

    def test_both_requires_one(self):
        try:
            SoundMapping(event=HookEvent.SESSION_START)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_default_volume(self):
        sm = SoundMapping(
            event=HookEvent.SESSION_START,
            tts_phrase="Hello",
        )
        assert sm.volume == 1.0
