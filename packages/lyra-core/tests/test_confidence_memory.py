"""Tests for L311-8 — confidence-scored auto-memory tracker."""
from __future__ import annotations

import time

import pytest

from lyra_core.memory import (
    ConfidenceRecord,
    ConfidenceTracker,
    DemotionEvent,
    PromotionEvent,
)


# ---- record validation -----------------------------------------------


def test_record_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        ConfidenceRecord(entry_id="x", confidence=1.5)


def test_record_age_days_zero_when_uncreated():
    r = ConfidenceRecord(entry_id="x")
    assert r.age_days == 0.0


def test_record_round_trip_json():
    r = ConfidenceRecord(
        entry_id="x", confidence=0.7, seen_count=2, last_seen_ts=100.0,
        created_ts=50.0, extracted_by="test"
    )
    r2 = ConfidenceRecord.from_json(r.to_json())
    assert r2.confidence == 0.7
    assert r2.seen_count == 2
    assert r2.entry_id == "x"


# ---- tracker basic --------------------------------------------------


def test_tracker_record_pattern_creates(tmp_path):
    t = ConfidenceTracker(root=tmp_path)
    rec = t.record_pattern(entry_id="a", confidence=0.6)
    assert rec.confidence == 0.6
    assert rec.seen_count == 1
    assert t.get("a") is not None


def test_tracker_observe_bumps_count_and_confidence(tmp_path):
    t = ConfidenceTracker(root=tmp_path)
    t.record_pattern(entry_id="a", confidence=0.5)
    rec = t.observe(entry_id="a", delta_confidence=0.1)
    assert rec.seen_count == 2
    assert abs(rec.confidence - 0.6) < 1e-9


def test_tracker_observe_clamps_at_one(tmp_path):
    t = ConfidenceTracker(root=tmp_path)
    t.record_pattern(entry_id="a", confidence=0.95)
    rec = t.observe(entry_id="a", delta_confidence=0.5)
    assert rec.confidence == 1.0


def test_tracker_decay_lowers_confidence(tmp_path):
    t = ConfidenceTracker(root=tmp_path)
    t.record_pattern(entry_id="a", confidence=0.6)
    rec = t.decay(entry_id="a", delta_confidence=0.4)
    assert abs(rec.confidence - 0.2) < 1e-9


def test_tracker_decay_clamps_at_zero(tmp_path):
    t = ConfidenceTracker(root=tmp_path)
    t.record_pattern(entry_id="a", confidence=0.1)
    rec = t.decay(entry_id="a", delta_confidence=0.5)
    assert rec.confidence == 0.0


def test_tracker_observe_unknown_raises(tmp_path):
    t = ConfidenceTracker(root=tmp_path)
    with pytest.raises(KeyError):
        t.observe(entry_id="ghost")


def test_tracker_record_rejects_invalid_confidence(tmp_path):
    t = ConfidenceTracker(root=tmp_path)
    with pytest.raises(ValueError):
        t.record_pattern(entry_id="x", confidence=2.0)


# ---- promotion / demotion candidates --------------------------------


def test_promotion_candidate_after_three_observes(tmp_path):
    t = ConfidenceTracker(root=tmp_path)
    t.record_pattern(entry_id="a", confidence=0.7)
    t.observe(entry_id="a", delta_confidence=0.1)  # → 0.8, count=2
    t.observe(entry_id="a", delta_confidence=0.1)  # → 0.9, count=3
    promos = t.candidates_for_promotion()
    assert any(p.entry_id == "a" for p in promos)


def test_no_promotion_below_threshold(tmp_path):
    t = ConfidenceTracker(root=tmp_path)
    t.record_pattern(entry_id="a", confidence=0.5)
    t.observe(entry_id="a")
    t.observe(entry_id="a")
    # confidence 0.5 + 2*0.05 = 0.6 < 0.85
    assert t.candidates_for_promotion() == ()


def test_demotion_candidate_after_age(tmp_path):
    t = ConfidenceTracker(root=tmp_path)
    t.record_pattern(entry_id="a", confidence=0.2)
    # Age the record by mutating created_ts to 8 days ago.
    rec = t.get("a")
    rec.created_ts = time.time() - 8 * 86400
    demos = t.candidates_for_demotion()
    assert any(p.entry_id == "a" for p in demos)


def test_no_demotion_when_too_young(tmp_path):
    t = ConfidenceTracker(root=tmp_path)
    t.record_pattern(entry_id="a", confidence=0.1)
    # Created just now → age_days ≈ 0
    assert t.candidates_for_demotion() == ()


def test_mark_promoted_excludes_from_candidates(tmp_path):
    t = ConfidenceTracker(root=tmp_path)
    t.record_pattern(entry_id="a", confidence=0.9)
    t.observe(entry_id="a", delta_confidence=0.1)
    t.observe(entry_id="a", delta_confidence=0.1)
    assert any(c.entry_id == "a" for c in t.candidates_for_promotion())
    t.mark_promoted("a")
    assert all(c.entry_id != "a" for c in t.candidates_for_promotion())


# ---- event listener ---------------------------------------------------


def test_promotion_event_fires_on_threshold_crossing(tmp_path):
    received: list = []
    t = ConfidenceTracker(root=tmp_path, listener=received.append)
    t.record_pattern(entry_id="a", confidence=0.8)
    t.observe(entry_id="a", delta_confidence=0.1)  # crosses to seen_count=2
    t.observe(entry_id="a", delta_confidence=0.1)  # crosses to seen_count=3
    promotions = [e for e in received if isinstance(e, PromotionEvent)]
    assert len(promotions) >= 1
    assert promotions[0].record.entry_id == "a"


def test_demotion_event_fires_when_old_and_low(tmp_path):
    received: list = []
    t = ConfidenceTracker(root=tmp_path, listener=received.append)
    rec = t.record_pattern(entry_id="a", confidence=0.2)
    rec.created_ts = time.time() - 10 * 86400  # 10 days
    # Now nudge the record so the tracker's _maybe_emit re-evaluates.
    t.observe(entry_id="a", delta_confidence=-0.05)
    demotions = [e for e in received if isinstance(e, DemotionEvent)]
    assert len(demotions) >= 1
    assert demotions[0].record.entry_id == "a"


def test_listener_errors_swallowed(tmp_path):
    def boom(event):
        raise RuntimeError("listener exploded")

    t = ConfidenceTracker(root=tmp_path, listener=boom)
    # Should not raise even though the listener throws.
    t.record_pattern(entry_id="a", confidence=0.95)
    t.observe(entry_id="a", delta_confidence=0.1)
    t.observe(entry_id="a", delta_confidence=0.1)
    assert t.get("a") is not None


# ---- persistence ------------------------------------------------------


def test_tracker_round_trip_through_disk(tmp_path):
    t1 = ConfidenceTracker(root=tmp_path)
    t1.record_pattern(entry_id="a", confidence=0.7)
    t1.observe(entry_id="a")
    # Re-open tracker — sidecar must restore.
    t2 = ConfidenceTracker(root=tmp_path)
    rec = t2.get("a")
    assert rec is not None
    assert rec.seen_count == 2
    assert abs(rec.confidence - 0.75) < 1e-9


def test_tracker_corrupt_sidecar_recovers(tmp_path):
    sidecar = tmp_path / "confidence.json"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text("not json", encoding="utf-8")
    # Tracker opens cleanly even on garbage sidecar.
    t = ConfidenceTracker(root=tmp_path)
    assert t.all() == ()


# ---- HIR event integration -------------------------------------------


def test_tracker_emits_hir_promote_event(tmp_path, monkeypatch):
    captured: list = []

    def fake_emit(name: str, /, **attrs):
        captured.append((name, attrs))

    from lyra_core.hir import events

    monkeypatch.setattr(events, "emit", fake_emit)

    t = ConfidenceTracker(root=tmp_path)
    t.record_pattern(entry_id="a", confidence=0.85)
    t.observe(entry_id="a", delta_confidence=0.05)
    t.observe(entry_id="a", delta_confidence=0.05)
    names = [n for n, _ in captured]
    assert "confidence.promote" in names
