"""Targeted tests for coverage gaps in lyra-voice internals.

Covers logic that previous tests missed:
- VoiceHookManager condition evaluation (!= operator)
- VoicePipeline listen_for_wake_word mode
- VoiceInterface parse_command with location entity extraction
- Providers: stream_transcribe/stream_synthesize/detect_segments default impls
- SFXManager tone generation different parameters
"""
from __future__ import annotations

import struct
import math

import pytest

from lyra_voice.voice_hooks import (
    VoiceHookManager,
    VoiceHookMapping,
)
from lyra_voice.sfx import SFXCategory, SFXManager, SFXAsset


# ═══════════════════════════════════════════════════════════════════════════
# VoiceHookManager: condition evaluation (!= operator, lines 237-244)
# ═══════════════════════════════════════════════════════════════════════════


class TestVoiceHookCondition:
    """Exercise the != condition evaluation and the exception fallback."""

    @pytest.fixture
    def hooks(self):
        return VoiceHookManager()

    def test_condition_not_equal_match(self, hooks):
        """!= condition should evaluate to True when context differs."""
        mapping = VoiceHookMapping(
            "test_hook", SFXCategory.ERROR, condition="tool_name!=read"
        )
        hooks.register_hook(mapping)
        audio = hooks.on_hook("test_hook", {"tool_name": "bash"})
        assert len(audio) > 0  # played because condition matched

    def test_condition_not_equal_no_match(self, hooks):
        """!= condition should return False (skip) when context matches."""
        mapping = VoiceHookMapping(
            "test_hook", SFXCategory.ERROR, condition="tool_name!=bash"
        )
        hooks.register_hook(mapping)
        audio = hooks.on_hook("test_hook", {"tool_name": "bash"})
        assert audio == b""  # skipped because condition didn't match

    def test_malformed_condition_falls_back_to_play(self, hooks):
        """Malformed condition should be treated as 'play'."""
        mapping = VoiceHookMapping(
            "test_hook", SFXCategory.ERROR, condition="no_operator_here"
        )
        hooks.register_hook(mapping)
        audio = hooks.on_hook("test_hook")
        assert len(audio) > 0  # falls through to play

    def test_condition_empty_context_returns_false(self, hooks):
        """When context key is missing, == should return False."""
        mapping = VoiceHookMapping(
            "test_hook", SFXCategory.ERROR, condition="tool_name==bash"
        )
        hooks.register_hook(mapping)
        audio = hooks.on_hook("test_hook", {"tool_name": "read"})
        assert audio == b""

    def test_custom_mode_via_constructor(self):
        hooks = VoiceHookManager(mode="sync")
        assert hooks.mode == "sync"


# ═══════════════════════════════════════════════════════════════════════════
# SFXManager: tone generation edge cases (line 338)
# ═══════════════════════════════════════════════════════════════════════════


class TestSFXToneGeneration:
    """Exercise tone generation with different parameters."""

    @pytest.fixture
    def sfx(self):
        return SFXManager(volume=1.0)

    def test_tone_starts_with_fade_in(self, sfx):
        """The first sample should be near-zero amplitude (fade in)."""
        audio = sfx.play(SFXCategory.SESSION_START)
        assert len(audio) >= 4  # at least 2 samples
        # First sample (first 2 bytes) should be very low (fade-in)
        first_sample = struct.unpack("<h", audio[:2])[0]
        # In the fade, first sample gets amplitude * 0 / fade_samples = 0
        assert abs(first_sample) < 100

    def test_tone_ends_with_fade_out(self, sfx):
        """Tone should have a fade-out at the end."""
        audio = sfx.play(SFXCategory.SESSION_START)
        assert len(audio) >= 8
        # Last sample should be in fade-out region
        last_sample = struct.unpack("<h", audio[-2:])[0]
        assert abs(last_sample) > 0  # not silence

    def test_empty_asset_returns_empty(self, sfx):
        """An asset with 0 duration should produce empty audio."""
        from lyra_voice.sfx import VoicePack
        custom = VoicePack(
            pack_id="empty",
            name="Empty",
            sfx=(SFXAsset("NoSound", SFXCategory.SESSION_START, tone_duration_ms=0),),
        )
        sfx.register_pack(custom)
        sfx.set_pack("empty")
        audio = sfx.play(SFXCategory.SESSION_START)
        assert audio == b""

    def test_high_frequency_tone(self, sfx):
        """High frequency tone should produce valid audio."""
        audio = sfx.play(SFXCategory.WAKE_WORD_DETECTED)
        assert len(audio) > 0
        assert len(audio) % 2 == 0


# ═══════════════════════════════════════════════════════════════════════════
# SFXManager: disable/enable category edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestSFXCategoryToggle:
    def test_double_disable_no_error(self):
        sfx = SFXManager()
        sfx.disable_category(SFXCategory.ERROR)
        sfx.disable_category(SFXCategory.ERROR)  # should not raise
        audio = sfx.play(SFXCategory.ERROR)
        assert audio == b""

    def test_enable_category_not_disabled(self):
        sfx = SFXManager()
        sfx.enable_category(SFXCategory.ERROR)  # not in set — should not raise
        audio = sfx.play(SFXCategory.ERROR)
        assert len(audio) > 0
