"""Tests for DriftDetector — PRISM prompt drift detection and auto-repair."""

import pytest

from lyra_core.evolve.drift_detector import (
    DriftDetector,
    DriftMetric,
    DriftSeverity,
    DriftSnapshot,
    RepairStatus,
)


class TestDriftSeverity:
    def test_severity_values(self):
        assert DriftSeverity.NONE.value == "none"
        assert DriftSeverity.MINOR.value == "minor"
        assert DriftSeverity.MODERATE.value == "moderate"
        assert DriftSeverity.SEVERE.value == "severe"
        assert DriftSeverity.CRITICAL.value == "critical"


class TestRepairStatus:
    def test_status_values(self):
        assert RepairStatus.IDLE.value == "idle"
        assert RepairStatus.IN_PROGRESS.value == "in_progress"
        assert RepairStatus.SUCCESS.value == "success"
        assert RepairStatus.FAILED.value == "failed"
        assert RepairStatus.ROLLED_BACK.value == "rolled_back"


class TestDriftMetric:
    def test_no_drift(self):
        metric = DriftMetric(
            name="accuracy",
            current_value=0.95,
            baseline_value=0.95,
            threshold_warning=0.02,
            threshold_critical=0.05,
            direction="higher_is_better",
        )
        assert metric.severity == DriftSeverity.NONE
        assert metric.drift_pct == 0.0

    def test_minor_drift(self):
        metric = DriftMetric(
            name="accuracy",
            current_value=0.93,
            baseline_value=0.95,
            threshold_warning=0.02,
            threshold_critical=0.05,
            direction="higher_is_better",
        )
        assert metric.severity == DriftSeverity.MINOR

    def test_severe_drift(self):
        metric = DriftMetric(
            name="accuracy",
            current_value=0.85,
            baseline_value=0.95,
            threshold_warning=0.02,
            threshold_critical=0.05,
            direction="higher_is_better",
        )
        assert metric.severity == DriftSeverity.SEVERE

    def test_critical_drift(self):
        metric = DriftMetric(
            name="latency",
            current_value=6.0,
            baseline_value=1.0,
            threshold_warning=0.5,
            threshold_critical=2.0,
            direction="lower_is_better",
        )
        assert metric.severity == DriftSeverity.CRITICAL

    def test_direction_lower_is_better_improvement(self):
        metric = DriftMetric(
            name="latency",
            current_value=0.8,
            baseline_value=1.0,
            threshold_warning=0.1,
            threshold_critical=0.3,
            direction="lower_is_better",
        )
        assert metric.severity == DriftSeverity.NONE

    def test_drift_pct(self):
        metric = DriftMetric(
            name="accuracy",
            current_value=0.8,
            baseline_value=1.0,
            threshold_warning=0.05,
            threshold_critical=0.1,
            direction="higher_is_better",
        )
        assert metric.drift_pct == pytest.approx(20.0)

    def test_metric_immutable(self):
        m = DriftMetric("accuracy", 0.9, 0.95, 0.02, 0.05)
        with pytest.raises(Exception):
            m.current_value = 0.8


class TestDriftSnapshot:
    def test_collect_no_drift(self):
        metrics = {
            "accuracy": (0.95, 0.95, 0.02, 0.05, "higher_is_better"),
            "token_efficiency": (0.85, 0.85, 0.05, 0.10, "higher_is_better"),
        }
        snapshot = DriftSnapshot.collect("system-prompt", 1, metrics)
        assert snapshot.prompt_id == "system-prompt"
        assert snapshot.overall_severity == DriftSeverity.NONE
        assert len(snapshot.metrics) == 2

    def test_collect_with_drift(self):
        metrics = {
            "accuracy": (0.80, 0.95, 0.02, 0.05, "higher_is_better"),
            "token_efficiency": (0.84, 0.85, 0.05, 0.10, "higher_is_better"),
        }
        snapshot = DriftSnapshot.collect("system-prompt", 2, metrics)
        assert snapshot.overall_severity == DriftSeverity.CRITICAL

    def test_snapshot_immutable(self):
        metrics = {"a": (1.0, 1.0, 0.1, 0.2, "higher_is_better")}
        s = DriftSnapshot.collect("p", 1, metrics)
        with pytest.raises(Exception):
            s.overall_severity = DriftSeverity.CRITICAL


class TestDriftDetector:
    def test_establish_baseline(self):
        detector = DriftDetector()
        metrics = {
            "accuracy": (0.95, 0.95, 0.02, 0.05, "higher_is_better"),
        }
        snapshot = detector.establish_baseline("system-prompt", metrics)
        assert snapshot.prompt_id == "system-prompt"
        assert snapshot.prompt_version == 1
        assert detector.tracked_prompts == 1

    def test_check_no_drift(self):
        detector = DriftDetector()
        baseline_metrics = {
            "accuracy": (0.95, 0.95, 0.02, 0.05, "higher_is_better"),
        }
        detector.establish_baseline("prompt-1", baseline_metrics)
        snapshot = detector.check("prompt-1", baseline_metrics)
        assert snapshot.overall_severity == DriftSeverity.NONE

    def test_check_drift_detected(self):
        detector = DriftDetector()
        detector.establish_baseline("prompt-1", {
            "accuracy": (0.95, 0.95, 0.02, 0.05, "higher_is_better"),
        })
        drifted = {
            "accuracy": (0.82, 0.95, 0.02, 0.05, "higher_is_better"),
        }
        snapshot = detector.check("prompt-1", drifted)
        assert snapshot.overall_severity != DriftSeverity.NONE

    def test_check_auto_establishes_baseline(self):
        detector = DriftDetector()
        metrics = {"accuracy": (0.9, 0.9, 0.05, 0.1, "higher_is_better")}
        snapshot = detector.check("new-prompt", metrics)
        assert detector.tracked_prompts == 1
        assert snapshot.overall_severity == DriftSeverity.NONE

    def test_repair_success(self):
        detector = DriftDetector()
        detector.establish_baseline("prompt-1", {
            "accuracy": (0.95, 0.95, 0.02, 0.05, "higher_is_better"),
        })
        detector.check("prompt-1", {
            "accuracy": (0.80, 0.95, 0.02, 0.05, "higher_is_better"),
        })
        result = detector.initiate_repair("prompt-1")
        assert result.status == RepairStatus.SUCCESS
        assert result.from_version != result.to_version
        assert detector.total_repairs == 1

    def test_repair_no_baseline(self):
        detector = DriftDetector()
        result = detector.initiate_repair("unknown-prompt")
        assert result.status == RepairStatus.FAILED

    def test_repair_with_custom_fn(self):
        detector = DriftDetector()
        detector.establish_baseline("p1", {
            "accuracy": (0.95, 0.95, 0.02, 0.05, "higher_is_better"),
        })
        detector.check("p1", {
            "accuracy": (0.80, 0.95, 0.02, 0.05, "higher_is_better"),
        })

        def repair_fn(_snapshot):
            return {"accuracy": (0.96, 0.96, 0.02, 0.05, "higher_is_better")}

        result = detector.initiate_repair("p1", repair_fn=repair_fn)
        assert result.status == RepairStatus.SUCCESS

    def test_repair_fn_exception(self):
        detector = DriftDetector()

        def failing_repair(_):
            raise RuntimeError("repair failed")

        detector.establish_baseline("p1", {
            "accuracy": (0.95, 0.95, 0.02, 0.05, "higher_is_better"),
        })
        result = detector.initiate_repair("p1", repair_fn=failing_repair)
        assert result.status == RepairStatus.FAILED
        assert "repair failed" in result.error_message

    def test_rollback(self):
        detector = DriftDetector()
        detector.establish_baseline("p1", {
            "accuracy": (0.95, 0.95, 0.02, 0.05, "higher_is_better"),
        })
        result = detector.rollback("p1", 1)
        assert result.status == RepairStatus.ROLLED_BACK

    def test_rollback_nonexistent(self):
        detector = DriftDetector()
        result = detector.rollback("unknown", 1)
        assert result.status == RepairStatus.FAILED

    def test_rollback_bad_version(self):
        detector = DriftDetector()
        detector.establish_baseline("p1", {
            "accuracy": (0.95, 0.95, 0.02, 0.05, "higher_is_better"),
        })
        result = detector.rollback("p1", 99)
        assert result.status == RepairStatus.FAILED

    def test_snapshot_history(self):
        detector = DriftDetector()
        detector.establish_baseline("p1", {
            "accuracy": (0.95, 0.95, 0.02, 0.05, "higher_is_better"),
        })
        detector.check("p1", {
            "accuracy": (0.93, 0.95, 0.02, 0.05, "higher_is_better"),
        })
        history = detector.get_snapshot_history("p1")
        assert len(history) == 2

    def test_latest_snapshot(self):
        detector = DriftDetector()
        detector.establish_baseline("p1", {
            "accuracy": (0.9, 0.9, 0.05, 0.1, "higher_is_better"),
        })
        latest = detector.get_latest_snapshot("p1")
        assert latest is not None
        assert latest.prompt_version == 1

    def test_stats(self):
        detector = DriftDetector()
        detector.establish_baseline("p1", {
            "accuracy": (0.95, 0.95, 0.02, 0.05, "higher_is_better"),
        })
        stats = detector.stats()
        assert stats["tracked_prompts"] == 1
        assert stats["total_snapshots"] == 1

    def test_stats_empty(self):
        detector = DriftDetector()
        stats = detector.stats()
        assert stats["tracked_prompts"] == 0

    def test_multiple_prompts(self):
        detector = DriftDetector()
        detector.establish_baseline("p1", {
            "accuracy": (0.95, 0.95, 0.02, 0.05, "higher_is_better"),
        })
        detector.establish_baseline("p2", {
            "latency": (1.0, 1.0, 0.1, 0.5, "lower_is_better"),
        })
        assert detector.tracked_prompts == 2

    def test_repair_history(self):
        detector = DriftDetector()
        detector.establish_baseline("p1", {
            "accuracy": (0.95, 0.95, 0.02, 0.05, "higher_is_better"),
        })
        detector.initiate_repair("p1")
        assert detector.total_repairs == 1
