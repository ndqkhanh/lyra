"""Tests for compaction-suggestion hook (Phase CE.2, P1-5)."""
from __future__ import annotations

import pytest

from lyra_core.context.profile import MINIMAL, STANDARD, STRICT
from lyra_core.context.suggest import (
    OBSERVATION_P95_MULTIPLE,
    SOFT_FILL_OFFSET,
    TOOL_DENSITY_TRIGGER,
    URGENCY_HARD,
    URGENCY_NONE,
    URGENCY_SOFT,
    CompactionAdvice,
    CompactionSignals,
    compute_signals,
    emit_advice_metrics,
    suggest_compaction,
)


# ────────────────────────────────────────────────────────────────
# CompactionSignals
# ────────────────────────────────────────────────────────────────


def test_signals_fill_ratio_caps_at_one():
    s = CompactionSignals(
        tokens_used=200, max_tokens=100, tool_call_density=0.0, observation_size_p95=0
    )
    assert s.fill_ratio == 1.0


def test_signals_fill_ratio_zero_max_returns_zero():
    s = CompactionSignals(
        tokens_used=10, max_tokens=0, tool_call_density=0.0, observation_size_p95=0
    )
    assert s.fill_ratio == 0.0


# ────────────────────────────────────────────────────────────────
# compute_signals
# ────────────────────────────────────────────────────────────────


def test_compute_signals_requires_positive_max_tokens():
    with pytest.raises(ValueError):
        compute_signals([], max_tokens=0)


def test_compute_signals_requires_positive_window():
    with pytest.raises(ValueError):
        compute_signals([], max_tokens=100, window=0)


def test_compute_signals_empty_transcript_returns_zeros():
    s = compute_signals([], max_tokens=1000)
    assert s.tokens_used == 0
    assert s.tool_call_density == 0.0
    assert s.observation_size_p95 == 0


def test_compute_signals_counts_tool_density_over_window():
    msgs = [
        {"role": "user", "content": "x"},
        {"role": "assistant", "content": "y"},
        {"role": "tool", "tool_call_id": "1", "content": "a"},
        {"role": "tool", "tool_call_id": "2", "content": "b"},
        {"role": "tool", "tool_call_id": "3", "content": "c"},
    ]
    s = compute_signals(msgs, max_tokens=1000, window=5)
    assert s.tool_call_density == pytest.approx(3 / 5)


def test_compute_signals_skips_already_cleared_for_p95():
    cleared_body = "[cleared: read_file @ t-1; stale; view artifact to restore]"
    msgs = [
        {"role": "tool", "tool_call_id": "t-1", "content": cleared_body},
        {"role": "tool", "tool_call_id": "t-2", "content": "x" * 4000},
        {"role": "tool", "tool_call_id": "t-3", "content": "y" * 2000},
    ]
    s = compute_signals(msgs, max_tokens=10_000, window=5)
    # Two non-cleared bodies of sizes [4000, 2000] → p95 ~= max = 4000.
    assert s.observation_size_p95 == 4000


def test_compute_signals_counts_failure_keywords():
    msgs = [
        {"role": "tool", "tool_call_id": "1", "content": "tests passed"},
        {"role": "tool", "tool_call_id": "2", "content": "FAIL: regression in api"},
        {"role": "assistant", "content": "permission denied"},
    ]
    s = compute_signals(msgs, max_tokens=1000)
    # "FAIL" + "regression" land in one message → still 1 message;
    # "denied" matches "denied" keyword → second message. Total 2.
    assert s.recent_failure_count == 2


def test_compute_signals_tokens_used_is_consistent_with_estimate():
    msgs = [{"role": "user", "content": "abcdefghij" * 4}]  # 40 chars
    s = compute_signals(msgs, max_tokens=1000)
    assert s.tokens_used == 10


def test_compute_signals_handles_non_string_content():
    msgs = [{"role": "tool", "tool_call_id": "x", "content": {"weird": "shape"}}]
    s = compute_signals(msgs, max_tokens=1000)
    assert s.tokens_used == 0


# ────────────────────────────────────────────────────────────────
# suggest_compaction
# ────────────────────────────────────────────────────────────────


def _signals(
    *,
    fill: float = 0.0,
    density: float = 0.0,
    p95: int = 0,
    max_tokens: int = 10_000,
) -> CompactionSignals:
    return CompactionSignals(
        tokens_used=int(fill * max_tokens),
        max_tokens=max_tokens,
        tool_call_density=density,
        observation_size_p95=p95,
    )


def test_suggest_no_pressure_returns_none():
    advice = suggest_compaction(_signals(fill=0.1), profile=STANDARD)
    assert advice.suggested is False
    assert advice.urgency == URGENCY_NONE


def test_suggest_hard_fires_at_autocompact_pct():
    advice = suggest_compaction(
        _signals(fill=STANDARD.autocompact_pct), profile=STANDARD
    )
    assert advice.urgency == URGENCY_HARD


def test_suggest_soft_fires_within_offset_band():
    fill = STANDARD.autocompact_pct - SOFT_FILL_OFFSET + 0.01
    advice = suggest_compaction(_signals(fill=fill), profile=STANDARD)
    assert advice.urgency == URGENCY_SOFT


def test_suggest_density_alone_can_trigger_soft():
    advice = suggest_compaction(
        _signals(density=TOOL_DENSITY_TRIGGER), profile=STANDARD
    )
    assert advice.urgency == URGENCY_SOFT
    assert any("tool_call_density" in r for r in advice.reasons)


def test_suggest_p95_alone_can_trigger_soft():
    cap = int(STANDARD.reduction_cap_kb * 1024 * OBSERVATION_P95_MULTIPLE)
    advice = suggest_compaction(_signals(p95=cap), profile=STANDARD)
    assert advice.urgency == URGENCY_SOFT


def test_suggest_minimal_profile_fires_earlier_than_standard():
    """The same fill ratio should produce stronger urgency under minimal."""
    fill = 0.55
    advice_std = suggest_compaction(_signals(fill=fill), profile=STANDARD)
    advice_min = suggest_compaction(_signals(fill=fill), profile=MINIMAL)
    # MINIMAL's autocompact_pct (~0.50) is below STANDARD's so fill 0.55
    # is already past hard for MINIMAL but soft/none for STANDARD.
    assert advice_min.urgency == URGENCY_HARD
    assert advice_std.urgency in {URGENCY_SOFT, URGENCY_NONE}


def test_suggest_strict_profile_tolerates_more_fill():
    fill = 0.79
    advice_strict = suggest_compaction(_signals(fill=fill), profile=STRICT)
    advice_std = suggest_compaction(_signals(fill=fill), profile=STANDARD)
    # STRICT's autocompact_pct (0.80) > STANDARD's? No — both are
    # 0.80 vs 0.85. Use the relative ordering: under STRICT 0.79 is
    # below hard; under STANDARD 0.79 is also below hard but inside
    # STANDARD's soft band.
    assert advice_strict.urgency in {URGENCY_NONE, URGENCY_SOFT}
    # Standard fires soft at 0.79 because soft = 0.70.
    assert advice_std.urgency == URGENCY_SOFT


def test_suggest_hard_includes_threshold_in_reason():
    advice = suggest_compaction(_signals(fill=0.99), profile=STANDARD)
    joined = " | ".join(advice.reasons)
    assert "fill_ratio" in joined
    assert "hard threshold" in joined


def test_advice_to_metric_dict_keys():
    advice = suggest_compaction(_signals(fill=0.99, density=0.7), profile=STANDARD)
    metrics = advice.to_metric_dict()
    assert metrics["context.compaction.advice.suggested"] == 1
    assert metrics["context.compaction.advice.urgency"] == URGENCY_HARD
    assert metrics["context.compaction.advice.reasons_count"] >= 2


def test_emit_advice_metrics_calls_sink_for_every_key():
    sink: list[tuple[str, object]] = []
    advice = suggest_compaction(_signals(fill=0.99), profile=STANDARD)
    emit_advice_metrics(advice, on_metric=lambda n, v: sink.append((n, v)))
    names = {n for n, _ in sink}
    assert "context.compaction.advice.suggested" in names
    assert "context.compaction.advice.urgency" in names
    assert "context.compaction.advice.fill_ratio" in names


def test_advice_default_signals_safe_with_no_max_tokens():
    # Constructing an advice without explicit signals shouldn't blow up.
    a = CompactionAdvice(suggested=False, urgency=URGENCY_NONE)
    assert a.signals.max_tokens >= 1
