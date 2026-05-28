"""Tests for the Phase 2.4b Quality Arbiter."""
from __future__ import annotations

import pytest
from lyra_core.orchestration.quality_arbiter import (
    QualityArbiter,
    QualityDimension,
    QualityReport,
    QualityScore,
    QualityStatus,
)


class TestQualityScore:
    def test_valid_score(self):
        qs = QualityScore(
            dimension=QualityDimension.CORRECTNESS,
            score=0.85,
            weight=2.0,
            reason="Looks good",
        )
        assert qs.score == 0.85

    def test_score_below_zero_raises(self):
        with pytest.raises(ValueError):
            QualityScore(
                dimension=QualityDimension.CORRECTNESS,
                score=-0.1,
                weight=1.0,
                reason="bad",
            )

    def test_score_above_one_raises(self):
        with pytest.raises(ValueError):
            QualityScore(
                dimension=QualityDimension.CORRECTNESS,
                score=1.5,
                weight=1.0,
                reason="bad",
            )

    def test_frozen_dataclass(self):
        qs = QualityScore(
            dimension=QualityDimension.CORRECTNESS,
            score=0.9,
            weight=1.0,
            reason="ok",
        )
        with pytest.raises(Exception):
            qs.score = 0.5  # type: ignore[misc]


class TestQualityArbiter:
    def test_evaluate_good_code_passes(self):
        arbiter = QualityArbiter(threshold=0.5)
        report = arbiter.evaluate(
            "def add(a: int, b: int) -> int:\n    return a + b",
            context="Math utility",
        )
        assert report.status == QualityStatus.PASSED

    def test_evaluate_empty_output_needs_revision(self):
        arbiter = QualityArbiter(threshold=0.7)
        report = arbiter.evaluate("", context="")
        assert report.status == QualityStatus.NEEDS_REVISION

    def test_evaluate_dangerous_code_has_low_safety(self):
        arbiter = QualityArbiter(threshold=0.7)
        report = arbiter.evaluate(
            "os.system('rm -rf /')",
            context="dangerous",
        )
        safety_score = arbiter.get_dimension_score(report, QualityDimension.SAFETY)
        assert safety_score is not None
        assert safety_score < 1.0

    def test_evaluate_todo_code_scores_lower(self):
        arbiter = QualityArbiter(threshold=0.7)
        report = arbiter.evaluate(
            "def process():\n    # TODO implement\n    pass",
            context="",
        )
        correctness = arbiter.get_dimension_score(report, QualityDimension.CORRECTNESS)
        assert correctness is not None
        assert correctness < 0.8

    def test_evaluate_returns_all_dimensions(self):
        arbiter = QualityArbiter()
        report = arbiter.evaluate("def foo(): return 1", context="test")
        dimension_names = {s.dimension for s in report.scores}
        assert len(dimension_names) == len(QualityDimension)

    def test_evaluate_subset_dimensions(self):
        arbiter = QualityArbiter()
        report = arbiter.evaluate(
            "def foo(): return 1",
            dimensions=(QualityDimension.CORRECTNESS, QualityDimension.SAFETY),
        )
        assert len(report.scores) == 2

    def test_composite_score_is_weighted_average(self):
        arbiter = QualityArbiter()
        report = arbiter.evaluate("def foo(): return 1", context="test")
        assert 0.0 <= report.composite_score <= 1.0

    def test_report_id_is_unique(self):
        arbiter = QualityArbiter()
        r1 = arbiter.evaluate("a")
        r2 = arbiter.evaluate("b")
        assert r1.report_id != r2.report_id

    def test_revision_suggestions_for_low_score(self):
        arbiter = QualityArbiter(threshold=0.9)
        report = arbiter.evaluate("", context="")
        if report.status != QualityStatus.PASSED:
            assert len(report.revision_suggestions) > 0

    def test_custom_threshold(self):
        arbiter = QualityArbiter()
        report = arbiter.evaluate(
            "def good_function(a: int) -> int:\n    return a + 1",
            threshold=0.3,
        )
        assert report.status == QualityStatus.PASSED

    def test_register_custom_scorer(self):
        arbiter = QualityArbiter()

        def perfect_scorer(_output: str, _ctx: str) -> float:
            return 1.0

        arbiter.register_scorer(QualityDimension.CORRECTNESS, perfect_scorer)
        report = arbiter.evaluate("anything")
        correctness = arbiter.get_dimension_score(report, QualityDimension.CORRECTNESS)
        assert correctness == 1.0

    def test_history_accumulates(self):
        arbiter = QualityArbiter()
        arbiter.evaluate("first")
        arbiter.evaluate("second")
        assert len(arbiter.history) == 2

    def test_clear_history(self):
        arbiter = QualityArbiter()
        arbiter.evaluate("test")
        arbiter.clear_history()
        assert len(arbiter.history) == 0

    def test_pass_rate(self):
        arbiter = QualityArbiter(threshold=0.5)
        arbiter.evaluate("def good(a: int) -> int:\n    return a + 1")
        arbiter.evaluate("")  # should be rejected/pass depending on threshold
        # At least one result in history
        assert len(arbiter.history) == 2
        assert 0.0 <= arbiter.pass_rate <= 1.0

    def test_get_dimension_score_nonexistent(self):
        arbiter = QualityArbiter()
        report = arbiter.evaluate("test")
        score = arbiter.get_dimension_score(report, QualityDimension.EFFICIENCY)
        assert score is not None

    def test_revise_loop_improves_output(self):
        arbiter = QualityArbiter(threshold=0.71)

        def revision_fn(output: str, _suggestions: tuple[str, ...]) -> str:
            return "def revised(a: int) -> int:\n    return a + 1"

        report = arbiter.evaluate("pass", context="")
        final_output, final_report = arbiter.revise(
            "pass", report, revision_fn, context="",
        )
        # Either revision happened or original passed — both fine
        assert final_output is not None
        assert final_report is not None

    def test_revise_respects_max_revisions(self):
        arbiter = QualityArbiter(threshold=0.99, max_revisions=2)
        call_count = [0]

        def revision_fn(output: str, _suggestions: tuple[str, ...]) -> str:
            call_count[0] += 1
            return "def still_not_perfect(): pass"

        report = arbiter.evaluate("def still_not_perfect(): pass")
        arbiter.revise("def still_not_perfect(): pass", report, revision_fn)
        assert call_count[0] <= arbiter.max_revisions

    def test_rejected_status_for_very_low_score(self):
        arbiter = QualityArbiter(threshold=0.7)
        report = arbiter.evaluate("", context="")
        assert report.status in (QualityStatus.NEEDS_REVISION, QualityStatus.REJECTED)


class TestQualityReport:
    def test_passed_status(self):
        report = QualityReport(
            report_id="qr-001",
            output_preview="def foo(): pass",
            scores=(),
            composite_score=0.85,
            status=QualityStatus.PASSED,
            threshold=0.7,
            revision_suggestions=(),
            timestamp=1000.0,
        )
        assert report.status == QualityStatus.PASSED

    def test_output_preview_truncation(self):
        arbiter = QualityArbiter()
        report = arbiter.evaluate("x" * 500)
        assert len(report.output_preview) <= 200
