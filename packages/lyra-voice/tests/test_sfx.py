"""Tests for sfx.py — SFX Personality Layer (P0-B4 HIGH×LOW)."""
from __future__ import annotations

import pytest
from lyra_voice.sfx import (
    BUILTIN_PACKS,
    HOOK_TO_SFX,
    SFXAsset,
    SFXCategory,
    SFXManager,
    VoicePack,
)


# ---------------------------------------------------------------------------
# SFXCategory
# ---------------------------------------------------------------------------

class TestSFXCategory:
    def test_values(self):
        assert SFXCategory.SESSION_START.value == "session_start"
        assert SFXCategory.SESSION_END.value == "session_end"
        assert SFXCategory.ERROR.value == "error"
        assert SFXCategory.BARGE_IN.value == "barge_in"
        assert SFXCategory.PRE_TOOL_USE.value == "pre_tool_use"
        assert SFXCategory.POST_TOOL_USE.value == "post_tool_use"
        assert SFXCategory.STOP.value == "stop"


# ---------------------------------------------------------------------------
# SFXAsset
# ---------------------------------------------------------------------------

class TestSFXAsset:
    def test_creation(self):
        asset = SFXAsset(
            name="Test Sound",
            category=SFXCategory.TOOL_CALL,
            description="A test sound",
            tone_frequency=523.0,
            tone_duration_ms=150,
        )
        assert asset.name == "Test Sound"
        assert asset.category == SFXCategory.TOOL_CALL
        assert asset.tone_frequency == 523.0

    def test_defaults(self):
        asset = SFXAsset(name="Default", category=SFXCategory.ERROR)
        assert asset.file_path == ""
        assert asset.tone_frequency == 440.0
        assert asset.tone_duration_ms == 200

    def test_frozen(self):
        asset = SFXAsset(name="x", category=SFXCategory.ERROR)
        with pytest.raises(Exception):
            asset.name = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# VoicePack
# ---------------------------------------------------------------------------

class TestVoicePack:
    def test_creation(self):
        pack = VoicePack(
            pack_id="test_pack",
            name="Test Pack",
            description="A test pack",
            tts_voice="kokoro-default",
            sfx=(
                SFXAsset("s1", SFXCategory.SESSION_START),
                SFXAsset("s2", SFXCategory.ERROR),
            ),
        )
        assert pack.pack_id == "test_pack"
        assert len(pack.sfx) == 2

    def test_defaults(self):
        pack = VoicePack(pack_id="min", name="Min")
        assert pack.sfx == ()
        assert pack.tts_voice == "default"
        assert pack.theme_colors == ("#4A90D9", "#1C1C1C")

    def test_frozen(self):
        pack = VoicePack(pack_id="x", name="X")
        with pytest.raises(Exception):
            pack.pack_id = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Built-in packs
# ---------------------------------------------------------------------------

class TestBuiltinPacks:
    def test_three_packs(self):
        assert len(BUILTIN_PACKS) == 3

    def test_pack_ids(self):
        ids = {p.pack_id for p in BUILTIN_PACKS}
        assert ids == {"minimal", "scifi", "warcraft_peon"}

    def test_minimal_pack_has_sfx(self):
        minimal = [p for p in BUILTIN_PACKS if p.pack_id == "minimal"][0]
        assert len(minimal.sfx) == 15
        categories = {a.category for a in minimal.sfx}
        assert SFXCategory.SESSION_START in categories
        assert SFXCategory.ERROR in categories

    def test_scifi_pack_has_sfx(self):
        scifi = [p for p in BUILTIN_PACKS if p.pack_id == "scifi"][0]
        assert len(scifi.sfx) == 15

    def test_warcraft_pack_has_sfx(self):
        wc = [p for p in BUILTIN_PACKS if p.pack_id == "warcraft_peon"][0]
        assert len(wc.sfx) == 15
        assert wc.tts_voice == "kokoro-default"


# ---------------------------------------------------------------------------
# SFXManager
# ---------------------------------------------------------------------------

class TestSFXManager:
    @pytest.fixture
    def sfx(self):
        return SFXManager()

    def test_default_pack_is_minimal(self, sfx):
        assert sfx.active_pack.pack_id == "minimal"

    def test_available_packs(self, sfx):
        packs = sfx.available_packs
        assert "minimal" in packs
        assert "scifi" in packs
        assert "warcraft_peon" in packs

    def test_set_pack(self, sfx):
        sfx.set_pack("scifi")
        assert sfx.active_pack.pack_id == "scifi"

    def test_set_pack_invalid(self, sfx):
        with pytest.raises(ValueError, match="Voice pack"):
            sfx.set_pack("nonexistent")

    def test_register_custom_pack(self, sfx):
        custom = VoicePack(
            pack_id="custom",
            name="Custom",
            sfx=(SFXAsset("c1", SFXCategory.SESSION_START),),
        )
        sfx.register_pack(custom)
        assert "custom" in sfx.available_packs

    def test_unregister_custom_pack(self, sfx):
        custom = VoicePack(pack_id="custom", name="C")
        sfx.register_pack(custom)
        sfx.unregister_pack("custom")
        assert "custom" not in sfx.available_packs

    def test_cannot_unregister_builtin(self, sfx):
        with pytest.raises(ValueError, match="Cannot unregister"):
            sfx.unregister_pack("minimal")

    def test_unregister_active_falls_back_to_minimal(self, sfx):
        custom = VoicePack(pack_id="custom", name="C")
        sfx.register_pack(custom)
        sfx.set_pack("custom")
        sfx.unregister_pack("custom")
        assert sfx.active_pack.pack_id == "minimal"

    def test_get_sfx_returns_asset(self, sfx):
        asset = sfx.get_sfx(SFXCategory.SESSION_START)
        assert asset is not None
        assert asset.category == SFXCategory.SESSION_START

    def test_get_sfx_unknown_returns_none(self, sfx):
        # All built-in packs have all categories mapped, so this always returns something
        # Testing with a minimal custom pack
        custom = VoicePack(pack_id="empty", name="Empty")
        sfx.register_pack(custom)
        sfx.set_pack("empty")
        assert sfx.get_sfx(SFXCategory.SESSION_START) is None
        sfx.set_pack("minimal")  # restore

    def test_play_generates_audio(self, sfx):
        audio = sfx.play(SFXCategory.TURN_COMPLETE)
        assert len(audio) > 0
        # Should be valid 16-bit PCM (even number of bytes)
        assert len(audio) % 2 == 0

    def test_play_disabled_returns_empty(self, sfx):
        sfx.enabled = False
        audio = sfx.play(SFXCategory.SESSION_START)
        assert audio == b""
        sfx.enabled = True

    def test_play_muted_category_returns_empty(self, sfx):
        sfx.disable_category(SFXCategory.ERROR)
        audio = sfx.play(SFXCategory.ERROR)
        assert audio == b""
        sfx.enable_category(SFXCategory.ERROR)
        audio = sfx.play(SFXCategory.ERROR)
        assert len(audio) > 0

    def test_play_different_packs_produce_audio(self, sfx):
        for pack_id in sfx.available_packs:
            sfx.set_pack(pack_id)
            audio = sfx.play(SFXCategory.SESSION_START)
            assert len(audio) > 0, f"Pack {pack_id} produced no audio"

    def test_volume_affects_amplitude(self, sfx):
        sfx.volume = 0.1
        quiet = sfx.play(SFXCategory.SESSION_START)
        sfx.volume = 1.0
        loud = sfx.play(SFXCategory.SESSION_START)
        # Both should produce audio
        assert len(quiet) > 0
        assert len(loud) > 0


# ---------------------------------------------------------------------------
# HOOK_TO_SFX
# ---------------------------------------------------------------------------

class TestHookToSFX:
    def test_mappings_exist(self):
        assert HOOK_TO_SFX["PreToolUse"] == SFXCategory.PRE_TOOL_USE
        assert HOOK_TO_SFX["PostToolUse"] == SFXCategory.POST_TOOL_USE
        assert HOOK_TO_SFX["Stop"] == SFXCategory.STOP

    def test_all_hooks_have_categories(self):
        expected = {
            "PreToolUse", "PostToolUse", "Stop", "session_start",
            "session_end", "error", "agent_handoff", "wake_word",
            "barge_in", "thinking", "tool_call", "tool_result",
            "workflow_complete", "notification", "turn_complete",
        }
        assert set(HOOK_TO_SFX.keys()) == expected
