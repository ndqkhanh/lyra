"""Tests for lyra-regression."""
from lyra_regression import RegressionDetector


class TestRegressionDetector:
    def test_no_regression_initially(self):
        d = RegressionDetector(threshold=0.1)
        d.record_snapshot("task_1", 0.9)
        d.record_snapshot("task_1", 0.91)
        assert len(d.events) == 0
        assert d.stats["regression_events"] == 0

    def test_regression_detected(self):
        d = RegressionDetector(threshold=0.1)
        d.record_snapshot("task_1", 0.9)
        d.record_snapshot("task_1", 0.5)
        assert len(d.events) == 1
        assert d.events[0].drop > 0.1

    def test_rollback(self):
        d = RegressionDetector(threshold=0.1)
        d.record_snapshot("task_1", 0.9)
        d.record_snapshot("task_1", 0.3)
        assert d.rollback("task_1")
