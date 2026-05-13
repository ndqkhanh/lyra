"""Tests for cache_telemetry.py and prefix_stability.py (Phase 1)."""
from __future__ import annotations

import pytest

from lyra_core.context.cache_telemetry import (
    CacheTelemetry,
    CacheTurnRecord,
    CacheSessionSummary,
)
from lyra_core.context.prefix_stability import (
    PrefixStabilityChecker,
    StabilityIssue,
    StabilityReport,
)


# ---------------------------------------------------------------------------
# CacheTurnRecord
# ---------------------------------------------------------------------------


def test_turn_record_hit_ratio_full():
    rec = CacheTurnRecord(
        turn_id=0,
        input_tokens=1000,
        cache_creation_tokens=0,
        cache_read_tokens=1000,
        output_tokens=100,
    )
    assert rec.hit_ratio == pytest.approx(1.0)


def test_turn_record_hit_ratio_none():
    rec = CacheTurnRecord(
        turn_id=0,
        input_tokens=1000,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        output_tokens=100,
    )
    assert rec.hit_ratio == pytest.approx(0.0)


def test_turn_record_hit_ratio_partial():
    rec = CacheTurnRecord(
        turn_id=0,
        input_tokens=1000,
        cache_creation_tokens=0,
        cache_read_tokens=700,
        output_tokens=50,
    )
    assert rec.hit_ratio == pytest.approx(0.7)


def test_turn_record_hit_ratio_zero_input():
    rec = CacheTurnRecord(
        turn_id=0,
        input_tokens=0,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        output_tokens=0,
    )
    assert rec.hit_ratio == pytest.approx(0.0)


def test_turn_record_cost_multiplier_full_read():
    """Full cache hit: cost ≈ 0.1× base."""
    rec = CacheTurnRecord(
        turn_id=0,
        input_tokens=1000,
        cache_creation_tokens=0,
        cache_read_tokens=1000,
        output_tokens=0,
    )
    assert rec.effective_cost_multiplier == pytest.approx(0.1)


def test_turn_record_cost_multiplier_full_write():
    """Full cache write: cost ≈ 1.25× base."""
    rec = CacheTurnRecord(
        turn_id=0,
        input_tokens=1000,
        cache_creation_tokens=1000,
        cache_read_tokens=0,
        output_tokens=0,
    )
    assert rec.effective_cost_multiplier == pytest.approx(1.25)


def test_turn_record_cost_multiplier_zero_input():
    rec = CacheTurnRecord(
        turn_id=0, input_tokens=0, cache_creation_tokens=0,
        cache_read_tokens=0, output_tokens=0,
    )
    assert rec.effective_cost_multiplier == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# CacheTelemetry — basic recording
# ---------------------------------------------------------------------------


def test_telemetry_no_records():
    tel = CacheTelemetry()
    assert tel.hit_ratio() == pytest.approx(0.0)
    assert tel.last_hit_ratio() is None
    assert not tel.should_alert()


def test_telemetry_single_hit():
    tel = CacheTelemetry(alert_threshold=0.70)
    tel.record(input_tokens=1000, cache_read_tokens=900)
    assert tel.hit_ratio() == pytest.approx(0.9)
    assert not tel.should_alert()


def test_telemetry_single_miss_triggers_alert():
    tel = CacheTelemetry(alert_threshold=0.70)
    tel.record(input_tokens=1000, cache_read_tokens=100)
    assert tel.should_alert()


def test_telemetry_alert_based_on_last_turn():
    tel = CacheTelemetry(alert_threshold=0.70)
    tel.record(input_tokens=1000, cache_read_tokens=900)  # good
    assert not tel.should_alert()
    tel.record(input_tokens=1000, cache_read_tokens=100)  # bad
    assert tel.should_alert()
    tel.record(input_tokens=1000, cache_read_tokens=900)  # good again
    assert not tel.should_alert()


def test_telemetry_mean_hit_ratio():
    tel = CacheTelemetry()
    tel.record(input_tokens=1000, cache_read_tokens=1000)  # 1.0
    tel.record(input_tokens=1000, cache_read_tokens=0)     # 0.0
    assert tel.hit_ratio() == pytest.approx(0.5)


def test_telemetry_records_list():
    tel = CacheTelemetry()
    tel.record(input_tokens=500, cache_read_tokens=400)
    tel.record(input_tokens=600, cache_read_tokens=500)
    recs = tel.records()
    assert len(recs) == 2
    assert recs[0].turn_id == 0
    assert recs[1].turn_id == 1


# ---------------------------------------------------------------------------
# CacheTelemetry — summary
# ---------------------------------------------------------------------------


def test_telemetry_summary_empty():
    s = CacheTelemetry().summary()
    assert isinstance(s, CacheSessionSummary)
    assert s.turn_count == 0
    assert s.mean_hit_ratio == pytest.approx(0.0)
    assert s.alert_count == 0


def test_telemetry_summary_values():
    tel = CacheTelemetry(alert_threshold=0.70)
    tel.record(input_tokens=1000, cache_creation_tokens=200,
               cache_read_tokens=800, output_tokens=50)
    tel.record(input_tokens=1000, cache_creation_tokens=0,
               cache_read_tokens=500, output_tokens=60)
    s = tel.summary()
    assert s.turn_count == 2
    assert s.total_input_tokens == 2000
    assert s.total_cache_creation_tokens == 200
    assert s.total_cache_read_tokens == 1300
    assert s.total_output_tokens == 110
    assert s.mean_hit_ratio == pytest.approx(0.65)
    assert s.min_hit_ratio == pytest.approx(0.5)
    assert s.alert_count == 1  # only turn 2 (0.5) below 0.70; turn 1 (0.8) is fine


# ---------------------------------------------------------------------------
# CacheTelemetry — persistence
# ---------------------------------------------------------------------------


def test_telemetry_save_and_load(tmp_path):
    path = tmp_path / "cache_telemetry.json"
    tel = CacheTelemetry(store_path=path)
    tel.record(input_tokens=1000, cache_read_tokens=800)
    tel.record(input_tokens=500, cache_read_tokens=400)

    tel2 = CacheTelemetry(store_path=path)
    assert len(tel2.records()) == 2
    assert tel2.records()[0].input_tokens == 1000
    assert tel2.records()[1].cache_read_tokens == 400


def test_telemetry_load_corrupt_file(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("not json {{{{")
    tel = CacheTelemetry(store_path=path)
    assert tel.records() == []


# ---------------------------------------------------------------------------
# PrefixStabilityChecker — stable cases
# ---------------------------------------------------------------------------

def _make_msg(role: str, text: str, *, cache: bool = False) -> dict:
    if cache:
        return {
            "role": role,
            "content": [
                {"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}
            ],
        }
    return {"role": role, "content": text}


def test_stable_simple():
    checker = PrefixStabilityChecker()
    msgs = [
        _make_msg("system", "You are Lyra.", cache=True),
        _make_msg("user", "What is attention?"),
    ]
    report = checker.check(msgs)
    assert report.is_stable
    assert report.issues == ()


def test_stable_single_message():
    checker = PrefixStabilityChecker()
    report = checker.check([_make_msg("user", "hello")])
    # Single message: no missing_cache_control warning (threshold is >= 2 msgs)
    assert StabilityIssue.MISSING_CACHE_CONTROL not in report.issues


# ---------------------------------------------------------------------------
# PrefixStabilityChecker — timestamp detection
# ---------------------------------------------------------------------------


def test_detects_iso_timestamp_in_prefix():
    checker = PrefixStabilityChecker()
    msgs = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "Session started at 2026-05-14T10:30:00",
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        },
        _make_msg("user", "hello"),
    ]
    report = checker.check(msgs)
    assert StabilityIssue.TIMESTAMP_IN_PREFIX in report.issues


def test_detects_unix_epoch_in_prefix():
    checker = PrefixStabilityChecker()
    msgs = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "epoch=1715683200",
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        },
        _make_msg("user", "hi"),
    ]
    report = checker.check(msgs)
    assert StabilityIssue.TIMESTAMP_IN_PREFIX in report.issues


# ---------------------------------------------------------------------------
# PrefixStabilityChecker — thinking block toggle
# ---------------------------------------------------------------------------


def test_detects_thinking_block_toggle():
    checker = PrefixStabilityChecker()
    msgs = [
        {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "..."},
                {"type": "text", "text": "answer A"},
            ],
        },
        {
            "role": "assistant",
            "content": "answer B",  # no thinking block
        },
    ]
    report = checker.check(msgs)
    assert StabilityIssue.THINKING_BLOCK_TOGGLE in report.issues


def test_consistent_thinking_blocks_no_issue():
    checker = PrefixStabilityChecker()
    msgs = [
        {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "..."},
                {"type": "text", "text": "A"},
            ],
        },
        {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "..."},
                {"type": "text", "text": "B"},
            ],
        },
    ]
    report = checker.check(msgs)
    assert StabilityIssue.THINKING_BLOCK_TOGGLE not in report.issues


# ---------------------------------------------------------------------------
# PrefixStabilityChecker — breakpoint shift
# ---------------------------------------------------------------------------


def test_detects_breakpoint_shift():
    checker = PrefixStabilityChecker()
    msgs = [
        _make_msg("system", "rules", cache=True),
        _make_msg("user", "question"),
    ]
    report = checker.check(msgs, previous_breakpoint=5)
    assert StabilityIssue.BREAKPOINT_SHIFT in report.issues


def test_no_breakpoint_shift_when_same():
    checker = PrefixStabilityChecker()
    msgs = [
        _make_msg("system", "rules", cache=True),
        _make_msg("user", "question"),
    ]
    report = checker.check(msgs, previous_breakpoint=1)
    assert StabilityIssue.BREAKPOINT_SHIFT not in report.issues


# ---------------------------------------------------------------------------
# PrefixStabilityChecker — missing cache_control
# ---------------------------------------------------------------------------


def test_detects_missing_cache_control():
    checker = PrefixStabilityChecker()
    msgs = [
        _make_msg("system", "You are Lyra."),
        _make_msg("user", "question"),
    ]
    report = checker.check(msgs)
    assert StabilityIssue.MISSING_CACHE_CONTROL in report.issues


# ---------------------------------------------------------------------------
# PrefixStabilityChecker — recommended_breakpoint
# ---------------------------------------------------------------------------


def test_recommended_breakpoint_after_cache_msg():
    checker = PrefixStabilityChecker()
    msgs = [
        _make_msg("system", "rules", cache=True),  # idx 0
        _make_msg("user", "question"),              # idx 1
    ]
    report = checker.check(msgs)
    assert report.recommended_breakpoint == 1


def test_recommended_breakpoint_no_cache():
    checker = PrefixStabilityChecker()
    msgs = [_make_msg("system", "rules"), _make_msg("user", "q")]
    report = checker.check(msgs)
    assert report.recommended_breakpoint == 0


# ---------------------------------------------------------------------------
# StabilityReport.summary()
# ---------------------------------------------------------------------------


def test_summary_stable():
    report = StabilityReport(
        is_stable=True, issues=(), details=(), recommended_breakpoint=2
    )
    assert "cache-stable" in report.summary()
    assert "2" in report.summary()


def test_summary_unstable():
    report = StabilityReport(
        is_stable=False,
        issues=(StabilityIssue.TIMESTAMP_IN_PREFIX,),
        details=("found 2026-05-14T10:00:00",),
        recommended_breakpoint=0,
    )
    s = report.summary()
    assert "timestamp_in_prefix" in s
    assert "found 2026" in s
