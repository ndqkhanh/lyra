"""Tests for the Alignment Drift Monitor."""

from __future__ import annotations

import pytest

from lyra_core.safety.alignment_monitor import (
    DEFAULT_DIMENSIONS,
    AlignmentMonitor,
    AlignmentSample,
    DriftReport,
    DriftStatus,
    _cosine_distance,
    _ema,
    _linear_trend,
)


class TestCosineDistance:
    def test_identical_vectors_zero_distance(self) -> None:
        a = (1.0, 0.5, 0.8)
        b = (1.0, 0.5, 0.8)
        assert _cosine_distance(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_orthogonal_vectors_max_distance(self) -> None:
        a = (1.0, 0.0)
        b = (0.0, 1.0)
        assert _cosine_distance(a, b) == pytest.approx(1.0, abs=1e-6)

    def test_zero_vector_returns_one(self) -> None:
        assert _cosine_distance((0.0, 0.0), (1.0, 1.0)) == 1.0

    def test_clamped_to_zero_one(self) -> None:
        d = _cosine_distance((1.0, 1.0), (-1.0, -1.0))
        assert 0.0 <= d <= 1.0


class TestEMA:
    def test_single_value(self) -> None:
        assert _ema([5.0], alpha=0.3) == 5.0

    def test_empty_returns_zero(self) -> None:
        assert _ema([]) == 0.0

    def test_converges_to_mean(self) -> None:
        values = [1.0] * 20
        assert _ema(values, alpha=0.3) == pytest.approx(1.0, abs=0.01)


class TestLinearTrend:
    def test_positive_trend(self) -> None:
        x = [0, 1, 2, 3, 4]
        y = [0.0, 0.1, 0.2, 0.3, 0.4]
        assert _linear_trend(x, y) == pytest.approx(0.1, abs=0.01)

    def test_flat_trend(self) -> None:
        x = [0, 1, 2]
        y = [0.5, 0.5, 0.5]
        assert _linear_trend(x, y) == pytest.approx(0.0, abs=1e-6)

    def test_single_point_zero_slope(self) -> None:
        assert _linear_trend([0], [1.0]) == 0.0

    def test_empty_returns_zero(self) -> None:
        assert _linear_trend([], []) == 0.0


class TestAlignmentSample:
    def test_sample_is_immutable(self) -> None:
        sample = AlignmentSample(
            sample_id="test",
            timestamp=100.0,
            value_vector=(1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
            action_signature="test_action",
            drift_score=0.0,
        )
        with pytest.raises(Exception):
            sample.drift_score = 0.5  # type: ignore[misc]


class TestAlignmentMonitorBasics:
    def test_initializes_with_default_baseline(self) -> None:
        monitor = AlignmentMonitor()
        assert monitor.baseline is not None
        assert len(monitor.baseline) == DEFAULT_DIMENSIONS

    def test_calibrate_sets_baseline(self) -> None:
        monitor = AlignmentMonitor()
        samples = [
            (0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9),
            (0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7),
        ]
        monitor.calibrate(samples)
        expected = tuple(0.8 for _ in range(DEFAULT_DIMENSIONS))
        for a, b in zip(monitor.baseline, expected):
            assert a == pytest.approx(b, abs=0.01)

    def test_calibrate_empty_does_nothing(self) -> None:
        monitor = AlignmentMonitor()
        original = monitor.baseline
        monitor.calibrate([])
        assert monitor.baseline == original

    def test_record_action_vector_returns_sample(self) -> None:
        monitor = AlignmentMonitor()
        vec = (0.95, 0.88, 0.92, 0.9, 0.85, 0.8, 0.9, 0.95)
        sample = monitor.record_action_vector(vec, "read_file:test.py")
        assert isinstance(sample, AlignmentSample)
        assert sample.action_signature == "read_file:test.py"
        assert sample.drift_score >= 0.0

    def test_perfect_alignment_gives_low_drift(self) -> None:
        monitor = AlignmentMonitor()
        monitor.baseline = (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
        sample = monitor.record_action_vector(
            (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
        )
        assert sample.drift_score == pytest.approx(0.0, abs=1e-6)

    def test_diverged_action_gives_high_drift(self) -> None:
        monitor = AlignmentMonitor()
        monitor.baseline = (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
        sample = monitor.record_action_vector(
            (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        )
        assert sample.drift_score > 0.5


class TestAlignmentMonitorDriftDetection:
    def test_no_samples_nominal(self) -> None:
        monitor = AlignmentMonitor()
        report = monitor.check_drift()
        assert report.status == DriftStatus.NOMINAL
        assert report.samples_evaluated == 0

    def test_nominal_when_below_threshold(self) -> None:
        monitor = AlignmentMonitor()
        monitor.baseline = (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
        for _ in range(10):
            monitor.record_action_vector(
                (0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99, 0.99)
            )
        report = monitor.check_drift()
        assert report.status == DriftStatus.NOMINAL

    def test_critical_when_above_threshold(self) -> None:
        monitor = AlignmentMonitor()
        monitor.baseline = (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
        monitor.critical_threshold = 0.01
        for _ in range(10):
            monitor.record_action_vector(
                (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            )
        report = monitor.check_drift()
        assert report.status == DriftStatus.CRITICAL
        assert report.requires_intervention

    def test_drifting_when_trend_positive(self) -> None:
        monitor = AlignmentMonitor()
        monitor.baseline = (0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
        monitor.drift_threshold = 0.01
        for i in range(15):
            divergence = 0.3 + i * 0.05
            vec = tuple(max(0.0, min(1.0, 0.5 - divergence)) for _ in range(8))
            monitor.record_action_vector(vec)
        report = monitor.check_drift()
        assert report.requires_intervention or report.status != DriftStatus.NOMINAL

    def test_window_size_respected(self) -> None:
        monitor = AlignmentMonitor()
        monitor.window_size = 5
        for _ in range(10):
            monitor.record_action_vector(
                (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
            )
        assert len(monitor.samples) == 5

    def test_report_recommendation_provided(self) -> None:
        monitor = AlignmentMonitor()
        report = monitor.check_drift()
        assert len(report.recommendation) > 0


class TestInferVectorFromAction:
    def test_successful_action_high_helpfulness(self) -> None:
        vec = AlignmentMonitor.infer_vector_from_action(
            action_type="read_file",
            success=True,
            tests_passed=True,
        )
        assert vec[0] >= 0.8  # helpfulness

    def test_failed_action_low_helpfulness(self) -> None:
        vec = AlignmentMonitor.infer_vector_from_action(
            action_type="write_file",
            success=False,
        )
        assert vec[0] <= 0.5

    def test_bypass_keyword_reduces_compliance(self) -> None:
        vec = AlignmentMonitor.infer_vector_from_action(
            action_type="bypass security check",
        )
        assert vec[4] <= 0.5  # compliance

    def test_errors_reduce_caution(self) -> None:
        vec_no_errors = AlignmentMonitor.infer_vector_from_action(errors_encountered=0)
        vec_with_errors = AlignmentMonitor.infer_vector_from_action(errors_encountered=5)
        assert vec_with_errors[5] < vec_no_errors[5]  # caution

    def test_user_feedback_influences_scores(self) -> None:
        vec_bad = AlignmentMonitor.infer_vector_from_action(user_feedback_score=0.1)
        vec_good = AlignmentMonitor.infer_vector_from_action(user_feedback_score=0.9)
        assert vec_good[0] > vec_bad[0]

    def test_returns_8_dimension_vector(self) -> None:
        vec = AlignmentMonitor.infer_vector_from_action()
        assert len(vec) == 8
        assert all(0.0 <= v <= 1.0 for v in vec)

    def test_files_modified_affects_thoroughness(self) -> None:
        vec_with_files = AlignmentMonitor.infer_vector_from_action(
            files_modified=1, tests_passed=False
        )
        vec_no_files = AlignmentMonitor.infer_vector_from_action(
            files_modified=0, tests_passed=False
        )
        assert vec_with_files[6] > vec_no_files[6]  # thoroughness


class TestDriftReport:
    def test_requires_intervention_on_drifting(self) -> None:
        report = DriftReport(
            report_id="test",
            status=DriftStatus.DRIFTING,
            current_drift=0.08,
            trend_slope=0.003,
            samples_evaluated=10,
            recommendation="Review needed.",
            timestamp=100.0,
        )
        assert report.requires_intervention

    def test_requires_intervention_on_critical(self) -> None:
        report = DriftReport(
            report_id="test",
            status=DriftStatus.CRITICAL,
            current_drift=0.2,
            trend_slope=0.01,
            samples_evaluated=10,
            recommendation="Suspend!",
            timestamp=100.0,
        )
        assert report.requires_intervention

    def test_no_intervention_on_nominal(self) -> None:
        report = DriftReport(
            report_id="test",
            status=DriftStatus.NOMINAL,
            current_drift=0.01,
            trend_slope=0.0,
            samples_evaluated=10,
            recommendation="All good.",
            timestamp=100.0,
        )
        assert not report.requires_intervention


class TestAlignmentMonitorReset:
    def test_reset_clears_samples(self) -> None:
        monitor = AlignmentMonitor()
        monitor.record_action_vector(
            (0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
        )
        monitor.reset()
        assert len(monitor.samples) == 0

    def test_reset_restores_baseline(self) -> None:
        monitor = AlignmentMonitor()
        monitor.calibrate([(0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5)])
        monitor.reset()
        assert monitor.baseline == tuple(1.0 for _ in range(DEFAULT_DIMENSIONS))
