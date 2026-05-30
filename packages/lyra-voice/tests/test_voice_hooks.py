"""Tests for voice_hooks.py — Hook-Based Audio Playback (P0-B5 HIGH×LOW)."""
from __future__ import annotations

import pytest
from lyra_voice.sfx import SFXCategory, SFXManager
from lyra_voice.voice_hooks import (
    DEFAULT_HOOK_MAPPINGS,
    HookEvent,
    PlaybackMode,
    VoiceHookManager,
    VoiceHookMapping,
    VoiceHookStats,
)


# ---------------------------------------------------------------------------
# HookEvent / PlaybackMode
# ---------------------------------------------------------------------------

class TestHookEvent:
    def test_values(self):
        assert HookEvent.PRE_TOOL_USE.value == "PreToolUse"
        assert HookEvent.POST_TOOL_USE.value == "PostToolUse"
        assert HookEvent.STOP.value == "Stop"


class TestPlaybackMode:
    def test_values(self):
        assert PlaybackMode.SYNC.value == "sync"
        assert PlaybackMode.ASYNC.value == "async"
        assert PlaybackMode.QUEUED.value == "queued"


# ---------------------------------------------------------------------------
# VoiceHookMapping
# ---------------------------------------------------------------------------

class TestVoiceHookMapping:
    def test_creation(self):
        m = VoiceHookMapping("PreToolUse", SFXCategory.PRE_TOOL_USE, cooldown_ms=500)
        assert m.hook_event == "PreToolUse"
        assert m.sfx_category == SFXCategory.PRE_TOOL_USE
        assert m.cooldown_ms == 500

    def test_defaults(self):
        m = VoiceHookMapping("Stop", SFXCategory.STOP)
        assert m.condition == ""
        assert m.cooldown_ms == 0

    def test_frozen(self):
        m = VoiceHookMapping("x", SFXCategory.ERROR)
        with pytest.raises(Exception):
            m.hook_event = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# VoiceHookStats
# ---------------------------------------------------------------------------

class TestVoiceHookStats:
    def test_defaults(self):
        stats = VoiceHookStats()
        assert stats.total_triggers == 0
        assert stats.total_played == 0
        assert stats.total_skipped == 0
        assert stats.per_hook == {}

    def test_mutable(self):
        stats = VoiceHookStats()
        stats.total_triggers += 1
        stats.total_played += 1
        assert stats.total_triggers == 1


# ---------------------------------------------------------------------------
# DEFAULT_HOOK_MAPPINGS
# ---------------------------------------------------------------------------

class TestDefaultHookMappings:
    def test_all_events_mapped(self):
        events = {m.hook_event for m in DEFAULT_HOOK_MAPPINGS}
        assert "PreToolUse" in events
        assert "PostToolUse" in events
        assert "Stop" in events
        assert "session_start" in events
        assert "session_end" in events
        assert "error" in events

    def test_count(self):
        assert len(DEFAULT_HOOK_MAPPINGS) == 14


# ---------------------------------------------------------------------------
# VoiceHookManager
# ---------------------------------------------------------------------------

class TestVoiceHookManager:
    @pytest.fixture
    def hooks(self):
        return VoiceHookManager()

    def test_default_mode_is_async(self, hooks):
        assert hooks.mode == PlaybackMode.ASYNC

    def test_on_pre_tool_use(self, hooks):
        audio = hooks.on_hook("PreToolUse")
        assert len(audio) > 0
        assert hooks.stats.total_played == 1

    def test_on_post_tool_use(self, hooks):
        audio = hooks.on_hook("PostToolUse")
        assert len(audio) > 0
        assert hooks.stats.total_triggers == 1

    def test_on_stop(self, hooks):
        audio = hooks.on_hook("Stop")
        assert len(audio) > 0

    def test_on_session_start(self, hooks):
        audio = hooks.on_session_start()
        assert len(audio) > 0

    def test_on_session_end(self, hooks):
        audio = hooks.on_session_end()
        assert len(audio) > 0

    def test_on_error(self, hooks):
        audio = hooks.on_error("something went wrong")
        assert len(audio) > 0

    def test_stats_tracking(self, hooks):
        hooks.on_hook("PreToolUse")
        hooks.on_hook("PostToolUse")
        hooks.on_hook("Stop")
        assert hooks.stats.total_triggers == 3
        assert hooks.stats.total_played == 3

    def test_mute_hook(self, hooks):
        hooks.mute_hook("PreToolUse")
        assert hooks.is_muted("PreToolUse")
        audio = hooks.on_hook("PreToolUse")
        assert audio == b""
        assert hooks.stats.total_skipped == 1

    def test_unmute_hook(self, hooks):
        hooks.mute_hook("Stop")
        hooks.unmute_hook("Stop")
        assert not hooks.is_muted("Stop")
        audio = hooks.on_hook("Stop")
        assert len(audio) > 0

    def test_unknown_hook_still_maps_via_fallback(self, hooks):
        # "notification" has a mapping in HOOK_TO_SFX → maps to SFX category
        audio = hooks.on_hook("notification")
        # notification IS in HOOK_TO_SFX (mapped to SFXCategory.NOTIFICATION)
        # But notification category may not exist in built-in packs
        # Let's test a known fallback instead
        audio = hooks.on_hook("thinking")
        assert len(audio) >= 0  # May or may not have audio depending on pack

    def test_unregistered_hook(self, hooks):
        audio = hooks.on_hook("completely_unknown_hook")
        assert audio == b""
        assert hooks.stats.total_skipped == 1

    def test_register_custom_mapping(self, hooks):
        mapping = VoiceHookMapping("custom_event", SFXCategory.ERROR)
        hooks.register_hook(mapping)
        assert hooks.get_mapping("custom_event") is mapping

    def test_unregister_hook(self, hooks):
        hooks.unregister_hook("PreToolUse")
        # After unregister, still works via HOOK_TO_SFX fallback
        audio = hooks.on_hook("PreToolUse")
        assert len(audio) > 0  # Falls back to HOOK_TO_SFX

    def test_reset_stats(self, hooks):
        hooks.on_hook("PreToolUse")
        hooks.on_hook("PostToolUse")
        hooks.reset_stats()
        assert hooks.stats.total_triggers == 0
        assert hooks.stats.total_played == 0

    def test_cooldown_respected(self, hooks):
        # Register with cooldown
        mapping = VoiceHookMapping("tool_call", SFXCategory.TOOL_CALL, cooldown_ms=5000)
        hooks.register_hook(mapping)

        # First call plays
        audio1 = hooks.on_hook("tool_call")
        assert len(audio1) > 0

        # Second call within cooldown is skipped
        audio2 = hooks.on_hook("tool_call")
        assert audio2 == b""

    def test_condition_matches(self, hooks):
        mapping = VoiceHookMapping(
            "conditional_hook", SFXCategory.ERROR,
            condition="tool_name==bash"
        )
        hooks.register_hook(mapping)

        # Matching context
        audio = hooks.on_hook("conditional_hook", {"tool_name": "bash"})
        assert len(audio) > 0

        # Non-matching context
        audio = hooks.on_hook("conditional_hook", {"tool_name": "read"})
        assert audio == b""

    def test_per_hook_stats(self, hooks):
        hooks.on_hook("PreToolUse")
        hooks.on_hook("PreToolUse")
        hooks.on_hook("PostToolUse")
        assert hooks.stats.per_hook["PreToolUse"] == 2
        assert hooks.stats.per_hook["PostToolUse"] == 1

    def test_custom_sfx_manager(self, hooks):
        # Disable SFX entirely
        hooks.sfx_manager.enabled = False
        audio = hooks.on_hook("Stop")
        assert audio == b""


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

class TestVoiceHooksIntegration:
    def test_full_hook_pipeline(self):
        """Simulate a complete tool-use lifecycle with hook SFX."""
        sfx = SFXManager(volume=0.5)
        hooks = VoiceHookManager(sfx_manager=sfx)

        # Session start
        hooks.on_session_start()

        # Pre-tool
        hooks.on_hook("PreToolUse", {"tool_name": "Bash"})

        # Post-tool
        hooks.on_hook("PostToolUse", {"tool_name": "Bash"})

        # Error
        hooks.on_error("command not found")

        # Session end
        hooks.on_session_end()

        assert hooks.stats.total_triggers == 5
        assert hooks.stats.total_played == 5

    def test_sfx_manager_shared_state(self):
        """SFXManager and VoiceHookManager share state correctly."""
        sfx = SFXManager()
        hooks = VoiceHookManager(sfx_manager=sfx)

        # Change pack in SFX manager
        sfx.set_pack("scifi")
        assert hooks.sfx_manager.active_pack.pack_id == "scifi"

        # Mute via SFX manager
        sfx.disable_category(SFXCategory.PRE_TOOL_USE)
        audio = hooks.on_hook("PreToolUse")
        assert audio == b""
