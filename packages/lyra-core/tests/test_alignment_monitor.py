"""Tests for the Phase 1 Alignment Drift Monitor."""
from __future__ import annotations

import pytest
from lyra_core.safety.alignment_monitor import (
    AlignmentMonitor,
    DriftReport,
    DriftStatus,
)

# ── Helpers ────────────────────────────────────────────────────────────

def _nominal_vector() -> tuple[float, ...]:
    """A perfectly aligned 8-dim vector."""
    return (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)


def _drifted_vector(severity: float = 0.5) -> tuple[float, ...]:
    """A partially misaligned 8-dim vector."""
    return tuple(1.0 - severity * (i / 8) for i in range(8))


class TestAlignmentMonitor:
    """Core alignment monitor behaviour."""

    def test_initial_state_is_nominal(self):
        monitor = AlignmentMonitor()
        report = monitor.check_drift()
        assert report.status == DriftStatus.NOMINAL
        assert report.current_drift == 0.0

    def test_recording_nominal_vector_stays_nominal(self):
        monitor = AlignmentMonitor()
        for _ in range(10):
            monitor.record_action_vector(_nominal_vector())
        report = monitor.check_drift()
        assert report.status == DriftStatus.NOMINAL

    def test_recording_drifted_vectors_detected(self):
        monitor = AlignmentMonitor(drift_threshold=0.01)
        for _ in range(30):
            monitor.record_action_vector(_drifted_vector(0.5))
        report = monitor.check_drift()
        assert report.status in (DriftStatus.ELEVATED, DriftStatus.DRIFTING, DriftStatus.CRITICAL)
        assert report.current_drift > 0
        assert report.samples_evaluated > 0

    def test_critical_drift_triggers_critical_status(self):
        monitor = AlignmentMonitor(drift_threshold=0.02, critical_threshold=0.05)
        for _ in range(30):
            monitor.record_action_vector(_drifted_vector(0.9))
        report = monitor.check_drift()
        assert report.status == DriftStatus.CRITICAL
        assert report.requires_intervention

    def test_drifting_with_positive_trend(self):
        monitor = AlignmentMonitor(drift_threshold=0.02)
        for severity in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
            monitor.record_action_vector(_drifted_vector(severity))
        report = monitor.check_drift()
        # With strong progressive drift, should be at least elevated
        assert report.status != DriftStatus.NOMINAL


class TestCalibration:
    def test_calibrate_sets_baseline(self):
        monitor = AlignmentMonitor()
        samples = [(0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9) for _ in range(10)]
        monitor.calibrate(samples)
        assert monitor.baseline == pytest.approx((0.9,) * 8)

    def test_post_calibration_nominal_has_zero_drift(self):
        monitor = AlignmentMonitor()
        vec = (0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8)
        monitor.calibrate([vec] * 20)
        monitor.record_action_vector(vec)
        report = monitor.check_drift()
        assert report.current_drift == pytest.approx(0.0, abs=1e-6)

    def test_calibrate_empty_does_nothing(self):
        monitor = AlignmentMonitor()
        original = monitor.baseline
        monitor.calibrate([])
        assert monitor.baseline == original


class TestInferVectorFromAction:
    def test_successful_action_is_helpful(self):
        vec = AlignmentMonitor.infer_vector_from_action(
            action_type="read_file",
            success=True,
            tests_passed=True,
        )
        assert vec[0] > 0.8  # helpfulness

    def test_failed_action_has_low_helpfulness(self):
        vec = AlignmentMonitor.infer_vector_from_action(
            action_type="read_file",
            success=False,
            tests_passed=False,
        )
        assert vec[0] < 0.6

    def test_bypass_actions_have_low_compliance(self):
        vec = AlignmentMonitor.infer_vector_from_action(
            action_type="bypass_check",
            success=True,
            tests_passed=True,
        )
        assert vec[4] < 0.6  # compliance

    def test_errors_reduce_caution(self):
        vec_clean = AlignmentMonitor.infer_vector_from_action(errors_encountered=0)
        vec_errs = AlignmentMonitor.infer_vector_from_action(errors_encountered=10)
        assert vec_errs[5] < vec_clean[5]  # caution

    def test_thoroughness_low_when_no_files_modified(self):
        vec = AlignmentMonitor.infer_vector_from_action(
            files_modified=0, tests_passed=False,
        )
        assert vec[6] < 0.7  # thoroughness

    def test_user_feedback_boosts_helpfulness(self):
        vec = AlignmentMonitor.infer_vector_from_action(
            success=True,
            user_feedback_score=0.95,
        )
        assert vec[0] > 0.8

    def test_returns_8_dimensions(self):
        vec = AlignmentMonitor.infer_vector_from_action()
        assert len(vec) == 8
        assert all(0.0 <= v <= 1.0 for v in vec)


class TestDriftReport:
    def test_nominal_does_not_require_intervention(self):
        report = DriftReport(
            report_id="dr-001",
            status=DriftStatus.NOMINAL,
            current_drift=0.01,
            trend_slope=0.0,
            samples_evaluated=10,
            recommendation="All good.",
            timestamp=1000.0,
        )
        assert not report.requires_intervention

    def test_critical_requires_intervention(self):
        report = DriftReport(
            report_id="dr-002",
            status=DriftStatus.CRITICAL,
            current_drift=0.45,
            trend_slope=0.01,
            samples_evaluated=10,
            recommendation="Suspend!",
            timestamp=1000.0,
        )
        assert report.requires_intervention

    def test_drifting_requires_intervention(self):
        report = DriftReport(
            report_id="dr-003",
            status=DriftStatus.DRIFTING,
            current_drift=0.25,
            trend_slope=0.005,
            samples_evaluated=10,
            recommendation="Review needed.",
            timestamp=1000.0,
        )
        assert report.requires_intervention


class TestWindowManagement:
    def test_window_prunes_old_samples(self):
        monitor = AlignmentMonitor(window_size=10)
        for i in range(15):
            monitor.record_action_vector(_nominal_vector())
        assert len(monitor.samples) == 10

    def test_reset_clears_all(self):
        monitor = AlignmentMonitor()
        for _ in range(5):
            monitor.record_action_vector(_nominal_vector())
        monitor.reset()
        assert len(monitor.samples) == 0
