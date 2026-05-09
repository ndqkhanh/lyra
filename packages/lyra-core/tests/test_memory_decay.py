"""Decay + access-strengthening tests (steal #3 from agentmemory)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from lyra_core.memory.auto_memory import AutoMemory, MemoryKind
from lyra_core.memory.decay import (
    DEFAULT_HALF_LIFE_S,
    AccessStats,
    access_boost,
    ebbinghaus_decay,
    half_life_for,
    weighted_score,
)


# --- pure functions --------------------------------------------------


def test_ebbinghaus_decay_at_zero_age_is_one() -> None:
    assert ebbinghaus_decay(0.0, 86_400.0) == pytest.approx(1.0)


def test_ebbinghaus_decay_at_half_life_is_half() -> None:
    assert ebbinghaus_decay(86_400.0 * 7, 86_400.0 * 7) == pytest.approx(0.5, abs=1e-9)


def test_ebbinghaus_decay_at_two_half_lives_is_quarter() -> None:
    assert ebbinghaus_decay(86_400.0 * 14, 86_400.0 * 7) == pytest.approx(0.25, abs=1e-9)


def test_ebbinghaus_decay_inf_half_life_no_decay() -> None:
    assert ebbinghaus_decay(86_400.0 * 9999, float("inf")) == 1.0


def test_ebbinghaus_decay_negative_age_clamps() -> None:
    assert ebbinghaus_decay(-100.0, 86_400.0) == 1.0


def test_access_boost_zero_is_one() -> None:
    assert access_boost(0) == 1.0


def test_access_boost_monotonic_increasing() -> None:
    assert access_boost(1) > access_boost(0)
    assert access_boost(10) > access_boost(1)
    assert access_boost(100) > access_boost(10)


def test_access_boost_saturates() -> None:
    """Above the saturation knob, the marginal boost shrinks."""
    delta_low = access_boost(11) - access_boost(10)
    delta_high = access_boost(101) - access_boost(100)
    assert delta_high < delta_low


def test_weighted_score_combines_decay_and_boost() -> None:
    """7-day-old anchor → decay 0.5; no access boost → final 0.5."""
    half_life = 86_400.0 * 7
    score = weighted_score(
        base_score=1.0,
        last_accessed_ts=1.0,         # any positive anchor
        access_count=0,
        half_life_s=half_life,
        now_ts=1.0 + half_life,        # exactly one half-life later
    )
    assert score == pytest.approx(0.5, abs=1e-3)


def test_weighted_score_no_anchor_no_decay() -> None:
    """Both last_accessed_ts and fallback_ts unset → return base_score."""
    score = weighted_score(
        base_score=0.7, last_accessed_ts=0.0, access_count=0,
        half_life_s=86_400.0 * 7, now_ts=86_400.0 * 7,
        fallback_ts=0.0,
    )
    assert score == pytest.approx(0.7)


def test_weighted_score_unaccessed_uses_fallback() -> None:
    """Default fallback is 0; entry's created_ts should be passed in."""
    score = weighted_score(
        base_score=1.0, last_accessed_ts=0.0, access_count=0,
        half_life_s=86_400.0 * 7,
        now_ts=86_400.0 * 7, fallback_ts=86_400.0 * 7,  # just-now
    )
    assert score == pytest.approx(1.0)


def test_half_life_for_default_kinds() -> None:
    assert half_life_for("user") == float("inf")
    assert half_life_for("project") == float("inf")
    assert half_life_for("feedback") == 86_400.0 * 7
    assert half_life_for("reference") == 86_400.0 * 30


def test_half_life_overrides_apply() -> None:
    overrides = {"user": 86_400.0}
    assert half_life_for("user", overrides=overrides) == 86_400.0
    # Untouched kinds keep their default.
    assert half_life_for("reference", overrides=overrides) == 86_400.0 * 30


# --- AutoMemory plumbing --------------------------------------------


def test_retrieve_records_access_by_default(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path / "mem", project="demo")
    e = am.save(kind=MemoryKind.PROJECT, title="csv chart",
                body="generate a chart from CSV using pandas")
    assert am.access_stats(e.entry_id).access_count == 0
    am.retrieve("chart from csv", top_n=3)
    assert am.access_stats(e.entry_id).access_count == 1
    am.retrieve("chart from csv", top_n=3)
    assert am.access_stats(e.entry_id).access_count == 2


def test_retrieve_no_record_when_disabled(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path / "mem", project="demo")
    e = am.save(kind=MemoryKind.PROJECT, title="x",
                body="generate a chart from CSV")
    am.retrieve("chart", top_n=3, record_access=False)
    assert am.access_stats(e.entry_id).access_count == 0


def test_access_stats_persist_across_reload(tmp_path: Path) -> None:
    am1 = AutoMemory(root=tmp_path / "mem", project="demo")
    e = am1.save(kind=MemoryKind.PROJECT, title="x",
                 body="generate a chart from CSV")
    am1.retrieve("chart from csv", top_n=3)
    am1.retrieve("chart from csv", top_n=3)
    assert am1.access_path.exists()

    # Re-open fresh.
    am2 = AutoMemory(root=tmp_path / "mem", project="demo")
    assert am2.access_stats(e.entry_id).access_count == 2


_NOW = 2_000_000_000.0   # realistic Unix epoch (2033-ish) for stable tests


def test_decay_demotes_stale_feedback(tmp_path: Path) -> None:
    """A `feedback` entry decays past a fresh tied-overlap entry."""
    am = AutoMemory(root=tmp_path / "mem", project="demo")
    stale = am.save(kind=MemoryKind.FEEDBACK,
                    title="stale", body="generate a chart from csv")
    fresh = am.save(kind=MemoryKind.FEEDBACK,
                    title="fresh", body="generate a chart from csv")
    stale_ts = _NOW - 86_400 * 60     # 60 days old → ~8 half-lives
    fresh_ts = _NOW - 86_400 * 0.5    # half a day old
    object.__setattr__(stale, "created_ts", stale_ts)
    object.__setattr__(fresh, "created_ts", fresh_ts)
    am._entries[stale.entry_id] = stale
    am._entries[fresh.entry_id] = fresh

    results = am.retrieve("chart from csv", top_n=2, now_ts=_NOW)
    assert results[0].entry_id == fresh.entry_id


def test_no_decay_mode_preserves_legacy_ranking(tmp_path: Path) -> None:
    am = AutoMemory(root=tmp_path / "mem", project="demo")
    older = am.save(kind=MemoryKind.FEEDBACK, title="older",
                    body="generate a chart from csv")
    newer = am.save(kind=MemoryKind.FEEDBACK, title="newer",
                    body="generate a chart from csv")
    object.__setattr__(older, "created_ts", _NOW - 86_400 * 60)
    object.__setattr__(newer, "created_ts", _NOW - 86_400 * 0.1)
    am._entries[older.entry_id] = older
    am._entries[newer.entry_id] = newer

    results = am.retrieve("chart from csv", top_n=2, decay=False)
    # Without decay, both have the same Jaccard; tie-break is created_ts
    # desc, so newer wins. Either way, ranking is unaffected by age.
    assert results[0].entry_id == newer.entry_id


def test_user_and_project_kinds_never_decay(tmp_path: Path) -> None:
    """``user`` and ``project`` half-lives are ∞ by default."""
    am = AutoMemory(root=tmp_path / "mem", project="demo")
    entry = am.save(kind=MemoryKind.USER, title="x",
                    body="prefers terse responses")
    object.__setattr__(entry, "created_ts", _NOW - 86_400 * 365)
    am._entries[entry.entry_id] = entry

    results = am.retrieve("terse responses", top_n=3, now_ts=_NOW)
    assert results and results[0].entry_id == entry.entry_id


def test_access_strengthening_lifts_hot_record(tmp_path: Path) -> None:
    """Two FEEDBACK entries — same age, but one has been accessed
    repeatedly. The hot one should rank above."""
    am = AutoMemory(root=tmp_path / "mem", project="demo")
    cold = am.save(kind=MemoryKind.FEEDBACK, title="cold",
                   body="generate a chart from csv")
    hot = am.save(kind=MemoryKind.FEEDBACK, title="hot",
                  body="generate a chart from csv")
    age_ts = _NOW - 86_400 * 5
    object.__setattr__(cold, "created_ts", age_ts)
    object.__setattr__(hot, "created_ts", age_ts)
    am._entries[cold.entry_id] = cold
    am._entries[hot.entry_id] = hot

    # Pre-warm 'hot' with 30 access bumps; persisted via _touch.
    for _ in range(30):
        am._touch([hot.entry_id], now=age_ts + 100)

    results = am.retrieve("chart from csv", top_n=2,
                          now_ts=_NOW, record_access=False)
    assert results[0].entry_id == hot.entry_id


def test_access_stats_corrupt_sidecar_recovers(tmp_path: Path) -> None:
    """A corrupted access_stats.json must not block memory load."""
    am1 = AutoMemory(root=tmp_path / "mem", project="demo")
    am1.save(kind=MemoryKind.PROJECT, title="x", body="something")
    # Corrupt the sidecar before reload.
    am1.access_path.write_text("{not valid json", encoding="utf-8")

    am2 = AutoMemory(root=tmp_path / "mem", project="demo")
    # Load succeeds; access stats start fresh.
    assert len(am2) == 1
    assert am2.access_stats("nonexistent").access_count == 0
