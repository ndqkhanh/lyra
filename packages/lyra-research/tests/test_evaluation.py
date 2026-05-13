"""
Tests for the Research Quality Evaluation system (evaluation.py).

All tests run offline — no network calls, no LLM calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

import pytest

from lyra_research.evaluation import (
    QualityTrendTracker,
    ResearchQualityEvaluator,
    ResearchQualityMetrics,
    SelfEvaluationAgent,
)


# ---------------------------------------------------------------------------
# Minimal stub for ResearchProgress and ResearchReport (avoids network deps)
# ---------------------------------------------------------------------------

@dataclass
class _StubReport:
    citation_fidelity: float = 1.0
    taxonomy_section: str = ""
    best_papers_section: str = ""
    gaps_section: str = ""
    next_steps_section: str = ""
    contested_claims_section: str = ""


@dataclass
class _StubProgress:
    session_id: str = field(default_factory=lambda: str(uuid4()))
    topic: str = "test topic"
    papers_analyzed: int = 0
    repos_analyzed: int = 0
    gaps_found: int = 0
    report: Optional[Any] = None


def _make_full_report() -> _StubReport:
    """Report with all sections populated, including a table."""
    return _StubReport(
        citation_fidelity=1.0,
        taxonomy_section="Taxonomy content",
        best_papers_section="| Title | Venue |\n|---|---|\n| PaperA | NeurIPS |",
        gaps_section="1. Gap one\n2. Gap two",
        next_steps_section="Next steps content",
        contested_claims_section="Contested claim A",
    )


def _make_progress(
    *,
    papers: int = 0,
    repos: int = 0,
    gaps: int = 0,
    report: Optional[Any] = None,
    topic: str = "test topic",
) -> _StubProgress:
    return _StubProgress(
        topic=topic,
        papers_analyzed=papers,
        repos_analyzed=repos,
        gaps_found=gaps,
        report=report,
    )


# ---------------------------------------------------------------------------
# ResearchQualityMetrics tests
# ---------------------------------------------------------------------------

def test_metrics_compute_overall_zero():
    m = ResearchQualityMetrics(session_id="s1", topic="t")
    # All axes default to 0.0
    assert m.compute_overall() == pytest.approx(0.0)


def test_metrics_compute_overall_weighted():
    m = ResearchQualityMetrics(session_id="s1", topic="t")
    m.coverage_score = 1.0
    m.citation_fidelity = 1.0
    m.source_breadth = 1.0
    m.insight_depth = 1.0
    m.gap_detection = 1.0
    m.contradiction_coverage = 1.0
    # All weights sum to 1.0, so overall should be 1.0
    assert m.compute_overall() == pytest.approx(1.0)


def test_metrics_compute_overall_partial():
    m = ResearchQualityMetrics(session_id="s1", topic="t")
    m.citation_fidelity = 1.0   # weight 0.30
    m.coverage_score = 1.0      # weight 0.25
    # Others remain 0.0
    expected = 0.30 + 0.25
    assert m.compute_overall() == pytest.approx(expected)


def test_metrics_to_dict_has_all_fields():
    m = ResearchQualityMetrics(session_id="abc", topic="test")
    d = m.to_dict()
    required_keys = [
        "session_id", "topic",
        "coverage_score", "coverage_detail",
        "citation_fidelity", "citation_detail",
        "source_breadth", "breadth_detail",
        "insight_depth", "depth_detail",
        "gap_detection", "gap_detail",
        "contradiction_coverage", "contradiction_detail",
        "overall_score", "passed", "issues", "measured_at",
    ]
    for key in required_keys:
        assert key in d, f"Missing key: {key}"


def test_metrics_to_dict_values():
    m = ResearchQualityMetrics(session_id="abc", topic="my topic")
    m.coverage_score = 0.9
    m.passed = True
    m.issues = ["issue1"]
    d = m.to_dict()
    assert d["session_id"] == "abc"
    assert d["topic"] == "my topic"
    assert d["coverage_score"] == pytest.approx(0.9)
    assert d["passed"] is True
    assert d["issues"] == ["issue1"]


def test_metrics_measured_at_is_utc():
    m = ResearchQualityMetrics(session_id="s", topic="t")
    assert m.measured_at.tzinfo is not None


# ---------------------------------------------------------------------------
# ResearchQualityEvaluator tests
# ---------------------------------------------------------------------------

def test_evaluator_evaluate_empty_progress():
    evaluator = ResearchQualityEvaluator()
    progress = _make_progress()
    metrics = evaluator.evaluate(progress, checklist_total=10, checklist_answered=0)
    assert metrics.coverage_score == pytest.approx(0.0)
    assert metrics.citation_fidelity == pytest.approx(0.0)
    assert metrics.session_id == progress.session_id
    assert metrics.topic == "test topic"


def test_evaluator_coverage_score():
    evaluator = ResearchQualityEvaluator()
    progress = _make_progress()
    metrics = evaluator.evaluate(progress, checklist_total=10, checklist_answered=8)
    assert metrics.coverage_score == pytest.approx(0.8)
    assert "8/10" in metrics.coverage_detail


def test_evaluator_coverage_score_full():
    evaluator = ResearchQualityEvaluator()
    progress = _make_progress()
    metrics = evaluator.evaluate(progress, checklist_total=5, checklist_answered=5)
    assert metrics.coverage_score == pytest.approx(1.0)


def test_evaluator_coverage_score_zero_total():
    """checklist_total=0 should not divide by zero."""
    evaluator = ResearchQualityEvaluator()
    progress = _make_progress()
    metrics = evaluator.evaluate(progress, checklist_total=0, checklist_answered=0)
    assert metrics.coverage_score == pytest.approx(0.0)


def test_evaluator_source_breadth():
    evaluator = ResearchQualityEvaluator()
    progress = _make_progress(papers=6, repos=4)
    metrics = evaluator.evaluate(progress, sources_found=20)
    # used=10, found=20 -> 0.5
    assert metrics.source_breadth == pytest.approx(0.5)
    assert "10 of 20" in metrics.breadth_detail


def test_evaluator_source_breadth_capped_at_one():
    evaluator = ResearchQualityEvaluator()
    progress = _make_progress(papers=30, repos=20)
    metrics = evaluator.evaluate(progress, sources_found=10)
    assert metrics.source_breadth == pytest.approx(1.0)


def test_evaluator_source_breadth_zero_sources_found():
    evaluator = ResearchQualityEvaluator()
    progress = _make_progress(papers=5)
    metrics = evaluator.evaluate(progress, sources_found=0)
    # used/max(0,1) = 5/1 capped at 1.0
    assert metrics.source_breadth == pytest.approx(1.0)


def test_evaluator_gap_detection():
    evaluator = ResearchQualityEvaluator()
    progress = _make_progress(gaps=2)
    metrics = evaluator.evaluate(progress, gaps_expected=4)
    assert metrics.gap_detection == pytest.approx(0.5)
    assert "2 gaps found" in metrics.gap_detail


def test_evaluator_gap_detection_exceeds_expected():
    evaluator = ResearchQualityEvaluator()
    progress = _make_progress(gaps=10)
    metrics = evaluator.evaluate(progress, gaps_expected=3)
    assert metrics.gap_detection == pytest.approx(1.0)


def test_evaluator_insight_depth_no_report():
    evaluator = ResearchQualityEvaluator()
    assert evaluator._score_insight_depth(None) == pytest.approx(0.0)


def test_evaluator_insight_depth_empty_report():
    evaluator = ResearchQualityEvaluator()
    report = _StubReport()
    assert evaluator._score_insight_depth(report) == pytest.approx(0.0)


def test_evaluator_insight_depth_partial_report():
    evaluator = ResearchQualityEvaluator()
    report = _StubReport(taxonomy_section="has content", gaps_section="gap")
    score = evaluator._score_insight_depth(report)
    assert score == pytest.approx(0.50)


def test_evaluator_insight_depth_full_report():
    evaluator = ResearchQualityEvaluator()
    report = _make_full_report()
    score = evaluator._score_insight_depth(report)
    assert score == pytest.approx(1.0)


def test_evaluator_insight_depth_needs_pipe_for_table():
    """best_papers_section without | should not count as table."""
    evaluator = ResearchQualityEvaluator()
    report = _StubReport(best_papers_section="Paper A, Paper B")
    score = evaluator._score_insight_depth(report)
    assert score == pytest.approx(0.0)


def test_evaluator_citation_fidelity_from_report():
    evaluator = ResearchQualityEvaluator()
    report = _StubReport(citation_fidelity=0.75)
    progress = _make_progress(report=report)
    metrics = evaluator.evaluate(progress)
    assert metrics.citation_fidelity == pytest.approx(0.75)
    assert "75%" in metrics.citation_detail


def test_evaluator_contradiction_coverage_present():
    evaluator = ResearchQualityEvaluator()
    report = _StubReport(contested_claims_section="Contested claim here")
    progress = _make_progress(report=report)
    metrics = evaluator.evaluate(progress)
    assert metrics.contradiction_coverage == pytest.approx(0.8)
    assert "present" in metrics.contradiction_detail


def test_evaluator_contradiction_coverage_absent():
    evaluator = ResearchQualityEvaluator()
    report = _StubReport(contested_claims_section="")
    progress = _make_progress(report=report)
    metrics = evaluator.evaluate(progress)
    assert metrics.contradiction_coverage == pytest.approx(0.0)


def test_evaluator_passed_when_all_gates_met():
    evaluator = ResearchQualityEvaluator()
    report = _make_full_report()
    progress = _make_progress(report=report, gaps=3)
    metrics = evaluator.evaluate(
        progress,
        checklist_total=10,
        checklist_answered=8,  # 80% >= MIN_COVERAGE
        sources_found=5,
        gaps_expected=3,
    )
    # citation_fidelity=1.0 (>= 1.0) and coverage=0.8 (>= 0.75)
    assert metrics.passed is True
    required_issues = [i for i in metrics.issues if "required" in i]
    assert len(required_issues) == 0


def test_evaluator_fails_low_citation_fidelity():
    evaluator = ResearchQualityEvaluator()
    report = _StubReport(citation_fidelity=0.5)
    progress = _make_progress(report=report, gaps=3)
    metrics = evaluator.evaluate(
        progress,
        checklist_total=10,
        checklist_answered=9,
        gaps_expected=3,
    )
    assert metrics.passed is False
    assert any("Citation fidelity" in i for i in metrics.issues)


def test_evaluator_fails_low_coverage():
    evaluator = ResearchQualityEvaluator()
    report = _StubReport(citation_fidelity=1.0)
    progress = _make_progress(report=report)
    metrics = evaluator.evaluate(
        progress,
        checklist_total=10,
        checklist_answered=5,  # 50% < 75%
    )
    assert metrics.passed is False
    assert any("Coverage" in i for i in metrics.issues)


def test_evaluator_gap_issue_below_target():
    evaluator = ResearchQualityEvaluator()
    report = _StubReport(citation_fidelity=1.0)
    progress = _make_progress(report=report, gaps=1)
    metrics = evaluator.evaluate(
        progress,
        checklist_total=10,
        checklist_answered=10,
        gaps_expected=5,
    )
    assert any("Gap detection" in i for i in metrics.issues)


def test_evaluator_is_deliverable_true():
    evaluator = ResearchQualityEvaluator()
    report = _make_full_report()
    progress = _make_progress(report=report, gaps=3)
    metrics = evaluator.evaluate(
        progress,
        checklist_total=10,
        checklist_answered=8,
        gaps_expected=3,
    )
    assert evaluator.is_deliverable(metrics) is True


def test_evaluator_is_deliverable_false_low_citation():
    evaluator = ResearchQualityEvaluator()
    report = _StubReport(citation_fidelity=0.5)
    progress = _make_progress(report=report, gaps=3)
    metrics = evaluator.evaluate(
        progress,
        checklist_total=10,
        checklist_answered=8,
        gaps_expected=3,
    )
    assert evaluator.is_deliverable(metrics) is False


def test_evaluator_is_deliverable_false_low_coverage():
    evaluator = ResearchQualityEvaluator()
    report = _StubReport(citation_fidelity=1.0)
    progress = _make_progress(report=report)
    metrics = evaluator.evaluate(
        progress,
        checklist_total=10,
        checklist_answered=3,  # 30% < 75%
    )
    assert evaluator.is_deliverable(metrics) is False


def test_evaluator_overall_score_is_set():
    evaluator = ResearchQualityEvaluator()
    report = _make_full_report()
    progress = _make_progress(report=report, gaps=3, papers=5)
    metrics = evaluator.evaluate(
        progress,
        checklist_total=10,
        checklist_answered=8,
        sources_found=10,
        gaps_expected=3,
    )
    assert metrics.overall_score > 0.0


# ---------------------------------------------------------------------------
# QualityTrendTracker tests
# ---------------------------------------------------------------------------

def _make_metrics(overall: float = 0.5, coverage: float = 0.8) -> ResearchQualityMetrics:
    m = ResearchQualityMetrics(session_id=str(uuid4()), topic="t")
    m.overall_score = overall
    m.coverage_score = coverage
    m.citation_fidelity = 1.0
    return m


def test_trend_tracker_record_and_get_trend(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    tracker.record(_make_metrics(overall=0.5))
    tracker.record(_make_metrics(overall=0.7))
    trend = tracker.get_trend("overall_score")
    assert trend == pytest.approx([0.5, 0.7])


def test_trend_tracker_get_trend_last_n(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    for v in [0.1, 0.2, 0.3, 0.4, 0.5]:
        tracker.record(_make_metrics(overall=v))
    trend = tracker.get_trend("overall_score", last_n=3)
    assert trend == pytest.approx([0.3, 0.4, 0.5])


def test_trend_tracker_is_improving_true(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    tracker.record(_make_metrics(overall=0.4))
    tracker.record(_make_metrics(overall=0.5))
    tracker.record(_make_metrics(overall=0.7))
    assert tracker.is_improving("overall_score", window=3) is True


def test_trend_tracker_is_improving_false(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    tracker.record(_make_metrics(overall=0.9))
    tracker.record(_make_metrics(overall=0.7))
    tracker.record(_make_metrics(overall=0.5))
    assert tracker.is_improving("overall_score", window=3) is False


def test_trend_tracker_is_improving_single_record(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    tracker.record(_make_metrics(overall=0.8))
    assert tracker.is_improving("overall_score") is False


def test_trend_tracker_average(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    tracker.record(_make_metrics(overall=0.4))
    tracker.record(_make_metrics(overall=0.6))
    assert tracker.average("overall_score") == pytest.approx(0.5)


def test_trend_tracker_average_empty(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    assert tracker.average("overall_score") == pytest.approx(0.0)


def test_trend_tracker_summary(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    tracker.record(_make_metrics(overall=0.6))
    tracker.record(_make_metrics(overall=0.8))
    summary = tracker.summary()
    assert summary["total_sessions"] == 2
    assert "averages" in summary
    assert "improving" in summary
    assert "overall_score" in summary["averages"]
    assert summary["averages"]["overall_score"] == pytest.approx(0.7)


def test_trend_tracker_summary_empty(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    summary = tracker.summary()
    assert summary["total_sessions"] == 0
    assert summary["averages"]["overall_score"] == pytest.approx(0.0)


def test_trend_tracker_persistence(tmp_path):
    path = tmp_path / "trends.json"
    tracker1 = QualityTrendTracker(store_path=path)
    tracker1.record(_make_metrics(overall=0.55))
    tracker1.record(_make_metrics(overall=0.77))

    # Reload from disk
    tracker2 = QualityTrendTracker(store_path=path)
    assert len(tracker2._records) == 2
    trend = tracker2.get_trend("overall_score")
    assert trend == pytest.approx([0.55, 0.77])


def test_trend_tracker_empty_trend(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    trend = tracker.get_trend("overall_score")
    assert trend == []


def test_trend_tracker_corrupted_file(tmp_path):
    path = tmp_path / "trends.json"
    path.write_text("NOT_VALID_JSON")
    tracker = QualityTrendTracker(store_path=path)
    # Should recover gracefully
    assert tracker._records == []


def test_trend_tracker_unknown_axis(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    tracker.record(_make_metrics())
    trend = tracker.get_trend("nonexistent_axis")
    assert trend == [0.0]


# ---------------------------------------------------------------------------
# SelfEvaluationAgent tests
# ---------------------------------------------------------------------------

def test_self_eval_agent_evaluate_and_track(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    agent = SelfEvaluationAgent(trend_tracker=tracker)
    report = _make_full_report()
    progress = _make_progress(report=report, gaps=3, papers=5)

    metrics = agent.evaluate_and_track(
        progress,
        checklist_total=10,
        checklist_answered=8,
        sources_found=10,
    )
    assert isinstance(metrics, ResearchQualityMetrics)
    assert len(tracker._records) == 1


def test_self_eval_agent_multiple_tracks(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    agent = SelfEvaluationAgent(trend_tracker=tracker)

    for _ in range(3):
        progress = _make_progress(report=_make_full_report(), gaps=3)
        agent.evaluate_and_track(progress, checklist_total=10, checklist_answered=8)

    assert len(tracker._records) == 3


def test_self_eval_agent_format_report_pass(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    agent = SelfEvaluationAgent(trend_tracker=tracker)

    m = ResearchQualityMetrics(session_id="s", topic="t")
    m.coverage_score = 0.9
    m.citation_fidelity = 1.0
    m.source_breadth = 0.8
    m.insight_depth = 1.0
    m.gap_detection = 0.7
    m.contradiction_coverage = 0.8
    m.overall_score = m.compute_overall()
    m.passed = True

    report_str = agent.format_report(m)
    assert "PASS" in report_str
    assert "Coverage" in report_str
    assert "Citation Fidelity" in report_str
    assert "Overall" in report_str


def test_self_eval_agent_format_report_fail(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    agent = SelfEvaluationAgent(trend_tracker=tracker)

    m = ResearchQualityMetrics(session_id="s", topic="t")
    m.coverage_score = 0.4
    m.citation_fidelity = 0.5
    m.passed = False
    m.issues = ["Citation fidelity 50% below required 100%"]
    m.overall_score = m.compute_overall()

    report_str = agent.format_report(m)
    assert "FAIL" in report_str
    assert "Issues" in report_str
    assert "Citation fidelity" in report_str


def test_self_eval_agent_format_report_no_issues(tmp_path):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    agent = SelfEvaluationAgent(trend_tracker=tracker)

    m = ResearchQualityMetrics(session_id="s", topic="t")
    m.passed = True
    m.overall_score = 0.9

    report_str = agent.format_report(m)
    assert "Issues" not in report_str


def test_self_eval_agent_default_tracker(tmp_path, monkeypatch):
    """SelfEvaluationAgent creates its own tracker if none provided."""
    monkeypatch.setattr(
        "lyra_research.evaluation.QualityTrendTracker.__init__",
        lambda self, store_path=None: setattr(self, "_records", [])
        or setattr(self, "store_path", tmp_path / "t.json"),
    )
    # Just verify it can be constructed without error
    agent = SelfEvaluationAgent()
    assert agent.tracker is not None
    assert agent.evaluator is not None
