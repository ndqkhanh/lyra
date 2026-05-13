"""Tests for context_evaluator.py (Phase 7)."""
from __future__ import annotations

import pytest

from lyra_core.context.context_evaluator import (
    ContextMetrics,
    ContextOptEvaluator,
    OptimisationTrendTracker,
    RegressionAlert,
    SectionCost,
    SessionCostTracker,
)


# ---------------------------------------------------------------------------
# ContextOptEvaluator
# ---------------------------------------------------------------------------


def test_evaluator_basic():
    ev = ContextOptEvaluator()
    m = ev.evaluate(
        cache_hit_ratio=0.8,
        tokens_saved=500,
        total_decisions=10,
        recalled_decisions=9,
        compaction_count=2,
        input_tokens=4000,
        output_tokens=600,
        cached_tokens=3200,
    )
    assert isinstance(m, ContextMetrics)
    assert m.cache_hit_ratio == pytest.approx(0.8)
    assert m.tokens_saved_by_compression == 500
    assert m.decisions_preserved == pytest.approx(0.9)
    assert m.compaction_count == 2
    assert m.estimated_cost_usd > 0


def test_evaluator_no_decisions():
    ev = ContextOptEvaluator()
    m = ev.evaluate(total_decisions=0, recalled_decisions=0)
    assert m.decisions_preserved == pytest.approx(1.0)


def test_evaluator_clamps_hit_ratio():
    ev = ContextOptEvaluator()
    m = ev.evaluate(cache_hit_ratio=1.5)
    assert m.cache_hit_ratio == pytest.approx(1.0)

    m2 = ev.evaluate(cache_hit_ratio=-0.3)
    assert m2.cache_hit_ratio == pytest.approx(0.0)


def test_evaluator_clamps_decisions_preserved():
    ev = ContextOptEvaluator()
    m = ev.evaluate(total_decisions=5, recalled_decisions=10)
    assert m.decisions_preserved == pytest.approx(1.0)


def test_evaluator_cost_lower_with_caching():
    ev = ContextOptEvaluator()
    m_cached = ev.evaluate(input_tokens=1000, cached_tokens=1000, output_tokens=0)
    m_uncached = ev.evaluate(input_tokens=1000, cached_tokens=0, output_tokens=0)
    assert m_cached.estimated_cost_usd < m_uncached.estimated_cost_usd


def test_evaluator_zero_tokens():
    ev = ContextOptEvaluator()
    m = ev.evaluate()
    assert m.estimated_cost_usd == pytest.approx(0.0)


def test_evaluator_timestamp_present():
    ev = ContextOptEvaluator()
    m = ev.evaluate()
    assert "T" in m.timestamp  # ISO format


# ---------------------------------------------------------------------------
# ContextMetrics serialisation
# ---------------------------------------------------------------------------


def test_metrics_roundtrip():
    ev = ContextOptEvaluator()
    m = ev.evaluate(cache_hit_ratio=0.75, tokens_saved=200, compaction_count=1)
    d = m.to_dict()
    m2 = ContextMetrics.from_dict(d)
    assert m2.cache_hit_ratio == pytest.approx(m.cache_hit_ratio)
    assert m2.tokens_saved_by_compression == m.tokens_saved_by_compression
    assert m2.compaction_count == m.compaction_count


# ---------------------------------------------------------------------------
# SessionCostTracker
# ---------------------------------------------------------------------------


def test_tracker_record_section():
    t = SessionCostTracker()
    t.record_section("stable_prefix", tokens=1000, is_cached=True)
    snap = t.snapshot()
    assert snap.total_tokens == 1000
    assert snap.total_cost_usd > 0


def test_tracker_cached_cheaper_than_uncached():
    t1 = SessionCostTracker()
    t1.record_section("recent_turns", tokens=500, is_cached=True)
    s1 = t1.snapshot()

    t2 = SessionCostTracker()
    t2.record_section("recent_turns", tokens=500, is_cached=False)
    s2 = t2.snapshot()

    assert s1.total_cost_usd < s2.total_cost_usd


def test_tracker_all_sections():
    t = SessionCostTracker()
    sections = ["stable_prefix", "recall_memory", "repo_map", "recent_turns", "tool_outputs"]
    for s in sections:
        t.record_section(s, tokens=100)
    snap = t.snapshot()
    assert snap.total_tokens == 500
    assert len(snap.sections) == 5


def test_tracker_unknown_section_ignored():
    t = SessionCostTracker()
    t.record_section("unknown_section", tokens=999)
    snap = t.snapshot()
    assert snap.total_tokens == 0


def test_tracker_output_tokens():
    t = SessionCostTracker()
    t.record_output(200)
    snap = t.snapshot()
    assert snap.total_tokens == 200
    assert snap.total_cost_usd > 0


def test_tracker_reset():
    t = SessionCostTracker()
    t.record_section("repo_map", tokens=400)
    t.reset()
    snap = t.snapshot()
    assert snap.total_tokens == 0
    assert snap.total_cost_usd == pytest.approx(0.0)


def test_tracker_snapshot_includes_metrics():
    ev = ContextOptEvaluator()
    metrics = ev.evaluate(cache_hit_ratio=0.9)
    t = SessionCostTracker()
    snap = t.snapshot(metrics=metrics)
    assert snap.metrics is not None
    assert snap.metrics.cache_hit_ratio == pytest.approx(0.9)


def test_tracker_section_cost_dtype():
    t = SessionCostTracker()
    t.record_section("tool_outputs", tokens=300)
    snap = t.snapshot()
    sc = next(s for s in snap.sections if s.section == "tool_outputs")
    assert isinstance(sc, SectionCost)
    assert sc.tokens == 300


# ---------------------------------------------------------------------------
# OptimisationTrendTracker
# ---------------------------------------------------------------------------


def _make_metrics(**kwargs) -> ContextMetrics:
    ev = ContextOptEvaluator()
    return ev.evaluate(**kwargs)


def test_trend_record_and_latest():
    tracker = OptimisationTrendTracker()
    m = _make_metrics(cache_hit_ratio=0.85)
    tracker.record(m)
    assert tracker.latest() is not None
    assert tracker.latest().cache_hit_ratio == pytest.approx(0.85)  # type: ignore[union-attr]


def test_trend_previous():
    tracker = OptimisationTrendTracker()
    tracker.record(_make_metrics(cache_hit_ratio=0.8))
    tracker.record(_make_metrics(cache_hit_ratio=0.9))
    assert tracker.previous().cache_hit_ratio == pytest.approx(0.8)  # type: ignore[union-attr]


def test_trend_no_regression_on_first():
    tracker = OptimisationTrendTracker()
    m = _make_metrics(cache_hit_ratio=0.6)
    alerts = tracker.check_regression(m)
    assert alerts == []


def test_trend_detects_cache_regression():
    tracker = OptimisationTrendTracker()
    tracker.record(_make_metrics(cache_hit_ratio=0.9))
    current = _make_metrics(cache_hit_ratio=0.5)  # drop > 5 pp
    alerts = tracker.check_regression(current)
    axes = [a.axis for a in alerts]
    assert "cache_hit_ratio" in axes


def test_trend_detects_compression_regression():
    tracker = OptimisationTrendTracker()
    tracker.record(_make_metrics(tokens_saved=500))
    current = _make_metrics(tokens_saved=0)   # 500 fewer → regression
    alerts = tracker.check_regression(current)
    axes = [a.axis for a in alerts]
    assert "tokens_saved_by_compression" in axes


def test_trend_no_false_alert_on_improvement():
    tracker = OptimisationTrendTracker()
    tracker.record(_make_metrics(cache_hit_ratio=0.5))
    current = _make_metrics(cache_hit_ratio=0.9)  # improvement
    alerts = tracker.check_regression(current)
    assert not any(a.axis == "cache_hit_ratio" for a in alerts)


def test_trend_all_records():
    tracker = OptimisationTrendTracker()
    for i in range(3):
        tracker.record(_make_metrics(compaction_count=i))
    records = tracker.all_records()
    assert len(records) == 3
    assert [r.compaction_count for r in records] == [0, 1, 2]


def test_trend_persist_and_reload(tmp_path):
    path = tmp_path / "trend.json"
    t1 = OptimisationTrendTracker(store_path=path)
    t1.record(_make_metrics(cache_hit_ratio=0.88, tokens_saved=300))

    t2 = OptimisationTrendTracker(store_path=path)
    m = t2.latest()
    assert m is not None
    assert m.cache_hit_ratio == pytest.approx(0.88)
    assert m.tokens_saved_by_compression == 300


def test_trend_load_corrupt(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json")
    tracker = OptimisationTrendTracker(store_path=path)
    assert tracker.all_records() == []


def test_trend_regression_alert_fields():
    tracker = OptimisationTrendTracker()
    tracker.record(_make_metrics(cache_hit_ratio=0.9))
    current = _make_metrics(cache_hit_ratio=0.5)
    alerts = tracker.check_regression(current)
    alert = next(a for a in alerts if a.axis == "cache_hit_ratio")
    assert isinstance(alert, RegressionAlert)
    assert alert.previous == pytest.approx(0.9)
    assert alert.current == pytest.approx(0.5)
    assert alert.delta < 0
