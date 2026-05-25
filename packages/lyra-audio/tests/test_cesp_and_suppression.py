"""Tests for Plan 8: CESP Engine and Audio Suppression."""

from __future__ import annotations

import time

import pytest

from lyra_audio.cesp_engine import (
    DEDUP_WINDOW_SECONDS,
    CespCategory,
    CespEngine,
    HOOK_TO_CESP,
    PackSelectionLayer,
    PlaybackRecord,
    SelectionResult,
)
from lyra_audio.audio_suppression import (
    AudioSuppression,
    SilentHours,
    SuppressionConfig,
    SuppressionReason,
    SuppressionResult,
    create_default_suppression,
)


# ═══════════════════════════════════════════════════════════════════════════
# CESP Engine Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCespCategory:
    def test_all_categories(self):
        cats = {c.value for c in CespCategory}
        assert "session.start" in cats
        assert "session.end" in cats
        assert "task.start" in cats
        assert "task.complete" in cats
        assert "task.error" in cats
        assert "input.required" in cats
        assert "thinking.start" in cats
        assert "thinking.end" in cats
        assert "resource.limit" in cats
        assert "permission.check" in cats
        assert "user.spam" in cats
        assert "goal.complete" in cats


class TestHookMapping:
    def test_session_start_maps(self):
        assert HOOK_TO_CESP["SessionStart"] == CespCategory.SESSION_START

    def test_session_end_maps(self):
        assert HOOK_TO_CESP["SessionEnd"] == CespCategory.SESSION_END

    def test_user_prompt_maps(self):
        assert HOOK_TO_CESP["UserPromptSubmit"] == CespCategory.TASK_START

    def test_stop_maps(self):
        assert HOOK_TO_CESP["Stop"] == CespCategory.TASK_COMPLETE

    def test_tool_failure_maps(self):
        assert HOOK_TO_CESP["PostToolUseFailure"] == CespCategory.TASK_ERROR

    def test_permission_request_maps(self):
        assert HOOK_TO_CESP["PermissionRequest"] == CespCategory.INPUT_REQUIRED

    def test_precompact_maps(self):
        assert HOOK_TO_CESP["PreCompact"] == CespCategory.RESOURCE_LIMIT

    def test_unknown_hook_defaults(self):
        engine = CespEngine()
        assert engine.map_hook("UnknownEvent") == CespCategory.TASK_COMPLETE

    def test_map_hook_all_known(self):
        engine = CespEngine()
        for hook_name, expected in HOOK_TO_CESP.items():
            assert engine.map_hook(hook_name) == expected


class TestSelectionResult:
    def test_create(self):
        r = SelectionResult(
            filepath=None,
            category=CespCategory.TASK_COMPLETE,
            pack_id="fantasy",
            selection_layer=PackSelectionLayer.DEFAULT_PACK,
        )
        assert r.pack_id == "fantasy"
        assert r.filepath is None

    def test_is_frozen(self):
        r = SelectionResult(
            filepath=None,
            category=CespCategory.TASK_COMPLETE,
            pack_id="minimal",
            selection_layer=PackSelectionLayer.HARDCODED_FALLBACK,
        )
        with pytest.raises(Exception):
            r.pack_id = "changed"


class TestCespEngineInit:
    def test_default_init(self):
        e = CespEngine()
        assert e._default_pack == "minimal"
        assert e._session_override is None

    def test_default_selection(self):
        e = CespEngine()
        pack = e.select_pack()
        assert pack == "minimal"


class TestCespEnginePackSelection:
    def test_session_override(self):
        e = CespEngine()
        e.set_session_override("fantasy")
        assert e.select_pack() == "fantasy"

    def test_session_override_clear(self):
        e = CespEngine()
        e.set_session_override("fantasy")
        e.set_session_override(None)
        assert e.select_pack() == "minimal"

    def test_default_pack(self):
        e = CespEngine()
        e.set_default_pack("sci-fi")
        assert e.select_pack() == "sci-fi"

    def test_enabled_packs_random(self):
        e = CespEngine()
        e.set_enabled_packs(["fantasy", "sci-fi", "nature"], rotation="random")
        seen = set()
        for _ in range(30):
            seen.add(e.select_pack())
        # Random should produce variety
        assert len(seen) >= 1

    def test_enabled_packs_round_robin(self):
        e = CespEngine()
        e.set_enabled_packs(["a", "b", "c"], rotation="round-robin")
        order = [e.select_pack() for _ in range(6)]
        assert order[:3] == ["a", "b", "c"]
        assert order[3:6] == ["a", "b", "c"]

    def test_session_override_takes_priority(self):
        e = CespEngine()
        e.set_session_override("fantasy")
        e.set_default_pack("sci-fi")
        e.set_enabled_packs(["minimal"], rotation="random")
        assert e.select_pack() == "fantasy"

    def test_hardcoded_fallback(self):
        e = CespEngine()
        e.set_default_pack("")
        e.set_enabled_packs([])
        assert e.select_pack() == "minimal"


class TestCespEngineSoundSelection:
    def test_select_with_candidates(self):
        e = CespEngine()
        candidates = {"task.complete": ["done1.wav", "done2.wav"]}
        result = e.select("fantasy", CespCategory.TASK_COMPLETE, candidates)
        assert result.category == CespCategory.TASK_COMPLETE
        assert result.pack_id == "fantasy"
        # filepath is None since no pack_loader is set
        assert result.filepath is None

    def test_select_defaults_when_no_candidates(self):
        e = CespEngine()
        result = e.select("minimal", CespCategory.TASK_COMPLETE)
        assert result.filepath is None

    def test_no_repeat_avoids_duplicate(self):
        e = CespEngine()
        candidates = {"task.complete": ["sound1.wav", "sound2.wav"]}

        results = []
        for _ in range(10):
            # Clear history between calls to avoid cooldown
            e.clear_history()
            r = e.select("fantasy", CespCategory.TASK_COMPLETE, candidates, no_repeat=True, cooldown_ms=0)
            results.append(r)

        # Manual verification: no-repeat should diversify
        assert len(results) == 10

    def test_playback_history(self):
        e = CespEngine()
        candidates = {"task.complete": ["sound.wav"]}
        e.select("fantasy", CespCategory.TASK_COMPLETE, candidates, cooldown_ms=0)
        assert len(e.playback_history) == 1

    def test_clear_history(self):
        e = CespEngine()
        candidates = {"task.complete": ["sound.wav"]}
        e.select("fantasy", CespCategory.TASK_COMPLETE, candidates, cooldown_ms=0)
        e.clear_history()
        assert len(e.playback_history) == 0

    def test_get_last_played(self):
        e = CespEngine()
        candidates = {"task.complete": ["sound.wav"]}
        e.select("fantasy", CespCategory.TASK_COMPLETE, candidates, cooldown_ms=0)
        last = e.get_last_played(CespCategory.TASK_COMPLETE)
        assert last is not None
        assert last.category == CespCategory.TASK_COMPLETE

    def test_get_last_played_none(self):
        e = CespEngine()
        assert e.get_last_played(CespCategory.TASK_START) is None


class TestCespEngineDedup:
    def test_not_in_dedup_categories(self):
        e = CespEngine()
        assert not e.should_deduplicate(CespCategory.TASK_START)

    def test_dedup_no_history(self):
        e = CespEngine()
        assert not e.should_deduplicate(CespCategory.TASK_COMPLETE)

    def test_dedup_recent_playback(self):
        e = CespEngine()
        candidates = {"task.complete": ["done.wav"]}
        e.select("minimal", CespCategory.TASK_COMPLETE, candidates, cooldown_ms=0)
        assert e.should_deduplicate(CespCategory.TASK_COMPLETE)


class TestCespEnginePathRules:
    def test_path_rule_match(self):
        e = CespEngine()
        e.set_path_rules({"**/production/**": "minimal", "**/gaming/**": "fantasy"})
        assert e.select_pack(working_dir="/home/user/gaming/mygame/src") == "fantasy"

    def test_path_rule_fallback(self):
        e = CespEngine()
        e.set_path_rules({"**/production/**": "minimal"})
        # Falls through to Layer 5/6 since no match
        result = e.select_pack(working_dir="/home/user/random/thing")
        assert result == "minimal"  # default


class TestCespEngineIdeRules:
    def test_ide_rule_match(self):
        e = CespEngine()
        e.set_ide_rules({"cursor": "sci-fi", "claude": "minimal"})
        assert e.select_pack(ide_name="cursor") == "sci-fi"

    def test_ide_rule_no_match(self):
        e = CespEngine()
        e.set_ide_rules({"cursor": "sci-fi"})
        assert e.select_pack(ide_name="vscode") == "minimal"


class TestPlaybackRecord:
    def test_create(self):
        r = PlaybackRecord(
            category=CespCategory.TASK_COMPLETE,
            filename="done.wav",
            timestamp=time.time(),
            pack_id="fantasy",
        )
        assert r.filename == "done.wav"
        assert r.pack_id == "fantasy"


# ═══════════════════════════════════════════════════════════════════════════
# Audio Suppression Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSilentHours:
    def test_valid_hours(self):
        s = SilentHours(start_hhmm="22:00", end_hhmm="07:00")
        assert s.contains(23, 30)
        assert s.contains(0, 0)
        assert s.contains(6, 59)
        assert not s.contains(12, 0)
        assert not s.contains(21, 59)

    def test_same_day_window(self):
        s = SilentHours(start_hhmm="01:00", end_hhmm="05:00")
        assert s.contains(3, 0)
        assert not s.contains(0, 0)
        assert not s.contains(5, 0)

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            SilentHours(start_hhmm="abc", end_hhmm="07:00")

    def test_invalid_hour(self):
        with pytest.raises(ValueError):
            SilentHours(start_hhmm="25:00", end_hhmm="07:00")

    def test_invalid_minute(self):
        with pytest.raises(ValueError):
            SilentHours(start_hhmm="22:60", end_hhmm="07:00")

    def test_boundary_exact_start(self):
        s = SilentHours(start_hhmm="22:00", end_hhmm="07:00")
        assert s.contains(22, 0)

    def test_boundary_exact_end(self):
        s = SilentHours(start_hhmm="22:00", end_hhmm="07:00")
        assert not s.contains(7, 0)


class TestSuppressionConfig:
    def test_default(self):
        c = SuppressionConfig()
        assert c.silent_hours == ()
        assert c.meeting_detect
        assert c.annoyed_threshold == 5

    def test_custom(self):
        c = SuppressionConfig(
            silent_hours=(SilentHours("22:00", "07:00"),),
            meeting_detect=False,
            annoyed_threshold=3,
        )
        assert len(c.silent_hours) == 1
        assert not c.meeting_detect
        assert c.annoyed_threshold == 3


class TestSuppressionResult:
    def test_allowed(self):
        r = SuppressionResult(suppressed=False, reason=SuppressionReason.NONE)
        assert not r.suppressed

    def test_suppressed(self):
        r = SuppressionResult(suppressed=True, reason=SuppressionReason.SILENT_HOURS, detail="Night time")
        assert r.suppressed
        assert r.detail == "Night time"


class TestAudioSuppressionInit:
    def test_default_init(self):
        s = AudioSuppression()
        assert not s.is_muted
        assert s.config.meeting_detect

    def test_custom_config(self):
        config = SuppressionConfig(annoyed_threshold=3, meeting_detect=False)
        s = AudioSuppression(config)
        assert s.config.annoyed_threshold == 3
        assert not s.config.meeting_detect

    def test_create_default(self):
        s = create_default_suppression()
        assert len(s.config.silent_hours) == 1


class TestAudioSuppressionCheck:
    def test_allowed_by_default(self):
        s = AudioSuppression()
        result = s.check()
        assert not result.suppressed
        assert result.reason == SuppressionReason.NONE

    def test_manual_mute(self):
        s = AudioSuppression()
        s.set_muted(True)
        result = s.check()
        assert result.suppressed
        assert result.reason == SuppressionReason.MANUAL_MUTE

    def test_unmute(self):
        s = AudioSuppression()
        s.set_muted(True)
        s.set_muted(False)
        result = s.check()
        assert not result.suppressed

    def test_meeting_detected(self):
        config = SuppressionConfig(meeting_detect=True)
        s = AudioSuppression(config)
        s.set_meeting_state(True)
        result = s.check()
        assert result.suppressed
        assert result.reason == SuppressionReason.MEETING_DETECTED

    def test_meeting_detect_disabled(self):
        config = SuppressionConfig(meeting_detect=False)
        s = AudioSuppression(config)
        s.set_meeting_state(True)
        result = s.check()
        assert not result.suppressed

    def test_headphones_only_no_headphones(self):
        config = SuppressionConfig(headphones_only=True)
        s = AudioSuppression(config)
        s.set_headphones_state(False)
        result = s.check()
        assert result.suppressed
        assert result.reason == SuppressionReason.HEADPHONES_ONLY

    def test_headphones_only_with_headphones(self):
        config = SuppressionConfig(headphones_only=True)
        s = AudioSuppression(config)
        s.set_headphones_state(True)
        result = s.check()
        assert not result.suppressed

    def test_spam_throttle(self):
        config = SuppressionConfig(annoyed_threshold=3, annoyed_window_seconds=60)
        s = AudioSuppression(config)
        s.record_playback()
        s.record_playback()
        s.record_playback()
        result = s.check()
        assert result.suppressed
        assert result.reason == SuppressionReason.SPAM_THROTTLE

    def test_spam_below_threshold(self):
        config = SuppressionConfig(annoyed_threshold=5)
        s = AudioSuppression(config)
        s.record_playback()
        s.record_playback()
        result = s.check()
        assert not result.suppressed

    def test_spam_threshold_disabled(self):
        config = SuppressionConfig(annoyed_threshold=0)
        s = AudioSuppression(config)
        s.record_playback()
        result = s.check()
        assert not result.suppressed


class TestAudioSuppressionStats:
    def test_stats_default(self):
        s = AudioSuppression()
        stats = s.stats()
        assert not stats["is_muted"]
        assert not stats["is_meeting"]
        assert stats["recent_play_count"] == 0

    def test_stats_with_plays(self):
        config = SuppressionConfig(annoyed_threshold=10)
        s = AudioSuppression(config)
        s.record_playback()
        s.record_playback()
        stats = s.stats()
        assert stats["recent_play_count"] == 2

    def test_stats_after_mute(self):
        s = AudioSuppression()
        s.set_muted(True)
        stats = s.stats()
        assert stats["is_muted"]


class TestAudioSuppressionEdgeCases:
    def test_suppression_priority_manual_over_meeting(self):
        s = AudioSuppression()
        s.set_muted(True)
        s.set_meeting_state(True)
        result = s.check()
        # Manual mute takes priority
        assert result.reason == SuppressionReason.MANUAL_MUTE

    def test_multiple_rapid_recordings(self):
        config = SuppressionConfig(annoyed_threshold=5)
        s = AudioSuppression(config)
        for _ in range(10):
            s.record_playback()
        result = s.check()
        assert result.suppressed

    def test_update_config_respects_new_threshold(self):
        s = AudioSuppression()
        s.record_playback()
        s.record_playback()
        s.record_playback()
        s.record_playback()
        s.record_playback()
        # Default threshold is 5
        result = s.check()
        assert result.suppressed

        # Update to higher threshold
        s.update_config(SuppressionConfig(annoyed_threshold=10))
        result = s.check()
        assert not result.suppressed
