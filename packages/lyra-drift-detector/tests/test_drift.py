"""Tests for Drift Detector package."""

import pytest
from lyra_drift_detector import (
    PerformanceDriftDetector, ContextDriftDetector,
    DistributionDriftDetector, RewardDriftDetector, DriftOrchestrator, DriftType
)


class TestPerformanceDriftDetector:
    def test_initial_no_drift(self):
        d = PerformanceDriftDetector()
        signal = d.check_drift()
        assert not signal.is_drift

    def test_record_attempts(self):
        d = PerformanceDriftDetector(window_size=10)
        for _ in range(20):
            d.record_attempt(True)
        d.record_attempt(False)
        signal = d.check_drift()
        assert signal.drift_type == DriftType.PERFORMANCE


class TestContextDriftDetector:
    def test_no_drift_without_baseline(self):
        d = ContextDriftDetector()
        signal = d.check_drift()
        assert not signal.is_drift

    def test_drift_detected(self):
        d = ContextDriftDetector(threshold=0.1)
        d.set_baseline({"python_files": 10.0, "complexity": 0.3})
        d.update_current({"python_files": 5.0, "complexity": 0.8})
        signal = d.check_drift()
        assert signal.drift_type == DriftType.CONTEXT


class TestRewardDriftDetector:
    def test_record_rewards(self):
        d = RewardDriftDetector(window_size=10)
        for _ in range(20):
            d.record_reward(0.8, "code")
        signal = d.check_drift()
        assert signal.drift_type == DriftType.REWARD


class TestDriftOrchestrator:
    def test_summary(self):
        o = DriftOrchestrator()
        s = o.summary
        assert "signals" in s
