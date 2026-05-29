"""Tests for Drift Detector package."""

from __future__ import annotations

import asyncio

import numpy as np
import pytest
from lyra_drift_detector import (
    # Adaptation
    AdaptationEngine,
    Alert,
    AlertManager,
    AlertRule,
    # Alerts
    AlertSeverity,
    ContextDriftDetector,
    ContextMonitor,
    DetectionMethod,
    DistributionDriftDetector,
    DistributionMonitor,
    # Exceptions
    DriftDetectorError,
    DriftOrchestrator,
    DriftSeverity,
    DriftSignal,
    # Core
    DriftType,
    EscalationPolicy,
    InsufficientDataError,
    InvalidConfigurationError,
    ModelRetrainStrategy,
    # Monitors
    MonitorConfig,
    MonitorNotInitializedError,
    MonitorRegistry,
    PerformanceDriftDetector,
    PerformanceMonitor,
    RewardDriftDetector,
    RewardMonitor,
    ThresholdRecalibrationStrategy,
)

# ── PerformanceDriftDetector ────────────────────────────────────────────


class TestPerformanceDriftDetector:
    def test_initial_no_drift(self):
        d = PerformanceDriftDetector(min_samples=5)
        signals = d.check_drift()
        assert isinstance(signals, list)
        assert len(signals) > 0

    def test_record_and_check_single_metric(self):
        d = PerformanceDriftDetector(window_size=50, min_samples=5)
        for _i in range(20):
            d.record("latency_ms", 100.0)
        signal = d.check_drift(metric="latency_ms")
        assert isinstance(signal, DriftSignal)
        assert signal.drift_type == DriftType.PERFORMANCE

    def test_record_batch(self):
        d = PerformanceDriftDetector(window_size=50, min_samples=5)
        for _ in range(30):
            d.record_batch({"latency_ms": 100.0, "error_rate": 0.01, "throughput": 50.0})
        signals = d.check_drift()
        assert len(signals) > 0


# ── ContextDriftDetector ───────────────────────────────────────────────


class TestContextDriftDetector:
    def test_no_drift_without_baseline(self):
        d = ContextDriftDetector()
        signal = d.check_drift()
        assert not signal.is_drift

    def test_drift_detected(self):
        d = ContextDriftDetector(threshold=0.1, min_samples=2)
        d.set_baseline({"python_files": 10.0, "complexity": 0.3})
        d.update({"python_files": 5.0, "complexity": 0.8})
        signal = d.check_drift()
        assert signal.drift_type == DriftType.CONTEXT


# ── DistributionDriftDetector ──────────────────────────────────────────


class TestDistributionDriftDetector:
    def test_record_and_check(self):
        d = DistributionDriftDetector(window_size=200, min_samples=5)
        d.set_reference([float(i % 10) for i in range(50)])
        for i in range(100):
            d.record(float(i % 10), task_type="code")
        signal = d.check_drift()
        assert isinstance(signal, DriftSignal)

    def test_ks_test_method(self):
        d = DistributionDriftDetector(
            window_size=200, min_samples=20,
            detection_method=DetectionMethod.KS_TEST,
        )
        d.set_reference([float(i) for i in range(50)])
        for i in range(100):
            d.record(float(50 + i), task_type="code")
        signal = d.check_drift()
        assert isinstance(signal, DriftSignal)


# ── RewardDriftDetector ────────────────────────────────────────────────


class TestRewardDriftDetector:
    def test_record_and_check(self):
        d = RewardDriftDetector(window_size=50, min_samples=5)
        for _ in range(20):
            d.record(0.8, "code")
        signal = d.check_drift()
        assert signal.drift_type == DriftType.REWARD


# ── DriftOrchestrator ──────────────────────────────────────────────────


class TestDriftOrchestrator:
    def test_summary(self):
        o = DriftOrchestrator()
        s = o.summary
        assert "adaptation_needed" in s
        assert "drift_count" in s
        assert "by_type" in s

    def test_check_all_sync(self):
        o = DriftOrchestrator()
        signals = o.check_all_sync()
        assert isinstance(signals, list)

    def test_disable_adaptation(self):
        o = DriftOrchestrator()
        o.disable_adaptation()
        assert not o._adaptation_enabled
        o.enable_adaptation()
        assert o._adaptation_enabled

    def test_reset(self):
        o = DriftOrchestrator()
        o.reset()
        assert o.performance.window_size == 500


# ── Monitors ───────────────────────────────────────────────────────────


class TestPerformanceMonitor:
    def test_observe_and_check(self):
        config = MonitorConfig(name="perf_test", window_size=100, min_samples=5, threshold=0.15)
        m = PerformanceMonitor(config=config, metric="latency_ms")
        m.set_baseline([100.0] * 20)
        for _ in range(20):
            m.observe(100.0)
        signal = asyncio.run(m.check())
        assert signal.drift_type == DriftType.PERFORMANCE


class TestContextMonitor:
    def test_profile_drift(self):
        config = MonitorConfig(name="ctx_test", threshold=0.1, min_samples=2)
        m = ContextMonitor(config=config)
        m.set_baseline([1.0, 2.0, 3.0])
        for _ in range(10):
            m.observe_profile({"a": 1.0, "b": 2.0})
        for _ in range(10):
            m.observe_profile({"a": 10.0, "b": 0.1})
        score = m.compute_drift_score()
        assert score > 0


class TestDistributionMonitor:
    def test_task_drift(self):
        config = MonitorConfig(name="dist_test", threshold=0.1, min_samples=2)
        m = DistributionMonitor(config=config)
        m.set_baseline([1.0, 1.0, 1.0])
        for _ in range(20):
            m.observe_task("task_a")
        for _ in range(5):
            m.observe_task("task_b")
        score = m.compute_drift_score()
        assert score is not None


class TestRewardMonitor:
    def test_context_rewards(self):
        config = MonitorConfig(name="rew_test", threshold=0.1, min_samples=2)
        m = RewardMonitor(config=config, track_per_context=True)
        m.set_baseline([0.5, 0.5, 0.5])
        for _ in range(10):
            m.observe_with_context(0.9, "good_context")
        for _ in range(10):
            m.observe_with_context(0.1, "bad_context")
        stats = m.reward_stats
        assert "per_context" in stats


class TestMonitorRegistry:
    def test_register_and_list(self):
        registry = MonitorRegistry()
        config = MonitorConfig(name="m1", min_samples=2)
        m = PerformanceMonitor(config=config, metric="test")
        m.set_baseline([1.0] * 20)
        registry.register(m)
        assert "m1" in registry.monitor_names

    def test_duplicate_register(self):
        registry = MonitorRegistry()
        config = MonitorConfig(name="m1", min_samples=2)
        m = PerformanceMonitor(config=config, metric="test")
        m.set_baseline([1.0] * 20)
        registry.register(m)
        with pytest.raises(ValueError):
            registry.register(m)

    def test_get_by_type(self):
        registry = MonitorRegistry()
        config = MonitorConfig(name="pm", min_samples=2)
        pm = PerformanceMonitor(config=config, metric="lat")
        pm.set_baseline([1.0] * 20)
        registry.register(pm)
        monitors = registry.get_by_type(DriftType.PERFORMANCE)
        assert len(monitors) == 1

    def test_summary(self):
        registry = MonitorRegistry()
        config = MonitorConfig(name="pm", min_samples=2)
        pm = PerformanceMonitor(config=config, metric="lat")
        pm.set_baseline([1.0] * 20)
        registry.register(pm)
        summary = registry.summary
        assert summary["total_monitors"] == 1


# ── Alerts ─────────────────────────────────────────────────────────────


class TestAlertManager:
    @pytest.fixture
    def manager(self):
        return AlertManager()

    def test_add_rule(self, manager):
        rule = AlertRule(name="test_rule")
        manager.add_rule(rule)
        assert len(manager.list_rules()) == 1

    @pytest.mark.asyncio
    async def test_process_signal_no_drift(self, manager):
        rule = AlertRule(name="test")
        manager.add_rule(rule)
        signal = DriftSignal(
            drift_type=DriftType.PERFORMANCE,
            metric="latency", score=0.01, threshold=0.15,
            is_drift=False,
        )
        alert = await manager.process_signal(signal)
        assert alert is None

    @pytest.mark.asyncio
    async def test_process_signal_drift(self, manager):
        rule = AlertRule(name="test", min_severity=DriftSeverity.LOW)
        manager.add_rule(rule)
        signal = DriftSignal(
            drift_type=DriftType.PERFORMANCE,
            metric="latency", score=0.5, threshold=0.15,
            is_drift=True, severity=DriftSeverity.HIGH,
        )
        alert = await manager.process_signal(signal)
        assert alert is not None
        assert alert.severity == AlertSeverity.WARN

    def test_alert_stats(self, manager):
        for _ in range(3):
            manager._alerts.append(Alert())
        stats = manager.alert_stats
        assert stats["total_alerts"] == 3


class TestEscalationPolicy:
    @pytest.fixture
    def policy(self):
        return EscalationPolicy(AlertManager())

    def test_set_delay(self, policy):
        policy.set_delay(AlertSeverity.CRITICAL, 120.0)

    @pytest.mark.asyncio
    async def test_check_and_escalate(self, policy):
        escalated = await policy.check_and_escalate()
        assert isinstance(escalated, list)


# ── Adaptation ─────────────────────────────────────────────────────────


class TestAdaptationEngine:
    @pytest.fixture
    def engine(self):
        eng = AdaptationEngine()
        eng.register_strategy(ThresholdRecalibrationStrategy())
        eng.register_strategy(ModelRetrainStrategy())
        return eng

    def test_register_strategy(self, engine):
        assert len(engine.list_strategies()) == 2

    def test_create_checkpoint(self, engine):
        cp = engine.create_checkpoint("test_component", {"key": "value"})
        assert cp.component == "test_component"
        assert engine.get_checkpoint(cp.checkpoint_id) is not None

    def test_latest_checkpoint(self, engine):
        engine.create_checkpoint("comp_a", {"v": 1})
        engine.create_checkpoint("comp_a", {"v": 2})
        latest = engine.get_latest_checkpoint("comp_a")
        assert latest.state_snapshot["v"] == 2

    def test_stats(self, engine):
        stats = engine.stats
        assert "strategies" in stats
        assert stats["strategies"] == 2


# ── Statistical functions ──────────────────────────────────────────────


class TestStatisticalFunctions:
    def test_ks_test_same_distribution(self):
        from lyra_drift_detector.drift_detector import _ks_test
        rng = np.random.default_rng(42)
        a = rng.normal(0, 1, 500)
        b = rng.normal(0, 1, 500)
        ks_stat, p_value = _ks_test(a, b)
        assert ks_stat < 0.3

    def test_kl_divergence_same(self):
        from lyra_drift_detector.drift_detector import _kl_divergence
        p = np.array([0.5, 0.3, 0.2])
        q = np.array([0.5, 0.3, 0.2])
        assert _kl_divergence(p, q) < 0.01

    def test_compute_severity(self):
        from lyra_drift_detector.drift_detector import _compute_severity
        assert _compute_severity(0.05, 0.1) == DriftSeverity.NONE
        assert _compute_severity(0.15, 0.1) == DriftSeverity.LOW


# ── Exceptions ────────────────────────────────────────────────────────


class TestExceptions:
    def test_drift_detector_error(self):
        with pytest.raises(DriftDetectorError):
            raise DriftDetectorError("test error")

    def test_monitor_not_initialized(self):
        with pytest.raises(MonitorNotInitializedError):
            raise MonitorNotInitializedError("test_monitor")

    def test_insufficient_data(self):
        with pytest.raises(InsufficientDataError):
            raise InsufficientDataError("metric", 10, 3)

    def test_invalid_config(self):
        with pytest.raises(InvalidConfigurationError):
            raise InvalidConfigurationError("comp", "bad config")
