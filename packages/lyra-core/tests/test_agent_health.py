"""Tests for Phase 11: Agent Health & Self-Diagnosis."""

from __future__ import annotations

import time

import pytest
from lyra_core.agent.health.anomaly import (
    AnomalyDetector,
    AnomalyRecord,
    AnomalyType,
)
from lyra_core.agent.health.monitor import (
    AgentHealthMonitor,
    HealthStatus,
    HealthTrend,
    MonitorConfig,
)
from lyra_core.agent.health.recovery import (
    PlaybookRegistry,
    PlaybookStatus,
    PlaybookStep,
    RecoveryPlaybook,
    RecoveryResult,
)
from lyra_core.agent.health.signals import (
    HealthSignal,
    SignalSeverity,
    SignalSource,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Signals
# ═══════════════════════════════════════════════════════════════════════════════


class TestSignalSeverity:
    def test_values(self):
        assert SignalSeverity.OK.value == "ok"
        assert SignalSeverity.WARN.value == "warn"
        assert SignalSeverity.DEGRADED.value == "degraded"
        assert SignalSeverity.CRITICAL.value == "critical"


class TestSignalSource:
    def test_values(self):
        assert SignalSource.MEMORY.value == "memory"
        assert SignalSource.LATENCY.value == "latency"
        assert SignalSource.ERROR_RATE.value == "error_rate"
        assert SignalSource.TOKEN_USAGE.value == "token_usage"
        assert SignalSource.TOOL_SUCCESS.value == "tool_success"
        assert SignalSource.SAFETY_TRIP.value == "safety_trip"
        assert SignalSource.CRASH_LOOP.value == "crash_loop"
        assert SignalSource.RECOVERY.value == "recovery"


class TestHealthSignal:
    def test_create_minimal(self):
        sig = HealthSignal(
            source=SignalSource.ERROR_RATE,
            severity=SignalSeverity.WARN,
            value=0.25,
        )
        assert sig.source == SignalSource.ERROR_RATE
        assert sig.severity == SignalSeverity.WARN
        assert sig.value == 0.25
        assert sig.metric == "default"
        assert sig.timestamp > 0

    def test_create_full(self):
        ts = time.time()
        sig = HealthSignal(
            source=SignalSource.LATENCY,
            severity=SignalSeverity.OK,
            value=1.5,
            metric="round_trip",
            message="All good",
            timestamp=ts,
            agent_id="agent-1",
            session_id="s1",
        )
        assert sig.metric == "round_trip"
        assert sig.message == "All good"
        assert sig.agent_id == "agent-1"
        assert sig.session_id == "s1"

    def test_to_dict(self):
        sig = HealthSignal(
            source=SignalSource.SAFETY_TRIP,
            severity=SignalSeverity.CRITICAL,
            value=1.0,
            metric="policy_deny",
            agent_id="a1",
        )
        d = sig.to_dict()
        assert d["source"] == "safety_trip"
        assert d["severity"] == "critical"
        assert d["value"] == 1.0
        assert d["metric"] == "policy_deny"
        assert d["agent_id"] == "a1"

    def test_from_dict(self):
        original = HealthSignal(
            source=SignalSource.MEMORY,
            severity=SignalSeverity.DEGRADED,
            value=0.85,
            metric="heap_usage",
            message="Near limit",
            agent_id="a2",
        )
        restored = HealthSignal.from_dict(original.to_dict())
        assert restored.source == original.source
        assert restored.severity == original.severity
        assert restored.value == original.value
        assert restored.metric == original.metric
        assert restored.message == original.message
        assert restored.agent_id == original.agent_id

    def test_from_dict_partial(self):
        d: dict[str, object] = {"source": "latency", "severity": "ok", "value": 0.0}
        sig = HealthSignal.from_dict(d)
        assert sig.metric == "default"
        assert sig.message == ""

    def test_is_frozen(self):
        sig = HealthSignal(
            source=SignalSource.ERROR_RATE,
            severity=SignalSeverity.OK,
            value=0.0,
        )
        with pytest.raises(Exception):  # noqa: B017
            sig.value = 1.0  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# Monitor
# ═══════════════════════════════════════════════════════════════════════════════


class TestMonitorConfig:
    def test_defaults(self):
        cfg = MonitorConfig()
        assert cfg.window_seconds == 300.0
        assert cfg.max_signals_per_source == 1000
        assert cfg.degrade_threshold == 0.3
        assert cfg.critical_threshold == 0.6
        assert cfg.trend_window_count == 3
        assert cfg.min_signals_for_trend == 5

    def test_custom(self):
        cfg = MonitorConfig(window_seconds=60.0, degrade_threshold=0.2)
        assert cfg.window_seconds == 60.0
        assert cfg.degrade_threshold == 0.2

    def test_is_frozen(self):
        cfg = MonitorConfig()
        with pytest.raises(Exception):  # noqa: B017
            cfg.window_seconds = 10.0  # type: ignore[misc]


class TestHealthTrend:
    def test_values(self):
        assert HealthTrend.IMPROVING.value == "improving"
        assert HealthTrend.STABLE.value == "stable"
        assert HealthTrend.DECLINING.value == "declining"


class TestHealthStatus:
    def test_create(self):
        status = HealthStatus(
            overall="ok",
            per_source=(("error_rate", "ok", 0.05, HealthTrend.STABLE),),
            anomaly_count=0,
            active_playbook="",
        )
        assert status.overall == "ok"
        assert status.anomaly_count == 0
        assert status.active_playbook == ""

    def test_is_frozen(self):
        status = HealthStatus(
            overall="ok",
            per_source=(),
            anomaly_count=0,
            active_playbook="",
        )
        with pytest.raises(Exception):  # noqa: B017
            status.overall = "critical"  # type: ignore[misc]


class TestAgentHealthMonitor:
    @pytest.fixture
    def monitor(self):
        return AgentHealthMonitor()

    def test_initial_state(self, monitor):
        assert monitor.signal_count == 0
        assert monitor.active_playbook == ""
        snap = monitor.snapshot()
        assert snap.overall == "ok"
        assert snap.anomaly_count == 0

    def test_ingest_signal(self, monitor):
        monitor.ingest(HealthSignal(
            source=SignalSource.ERROR_RATE,
            severity=SignalSeverity.WARN,
            value=0.25,
        ))
        assert monitor.signal_count == 1

    def test_get_signals_by_source(self, monitor):
        monitor.ingest(HealthSignal(
            source=SignalSource.ERROR_RATE,
            severity=SignalSeverity.WARN,
            value=0.25,
        ))
        monitor.ingest(HealthSignal(
            source=SignalSource.LATENCY,
            severity=SignalSeverity.OK,
            value=0.1,
        ))
        err_signals = monitor.get_signals(SignalSource.ERROR_RATE)
        assert len(err_signals) == 1
        assert err_signals[0].source == SignalSource.ERROR_RATE

    def test_get_all_signals(self, monitor):
        monitor.ingest(HealthSignal(
            source=SignalSource.ERROR_RATE,
            severity=SignalSeverity.WARN,
            value=0.25,
        ))
        monitor.ingest(HealthSignal(
            source=SignalSource.LATENCY,
            severity=SignalSeverity.OK,
            value=0.1,
        ))
        all_sigs = monitor.get_signals()
        assert len(all_sigs) == 2

    def test_source_summary_empty(self, monitor):
        summary = monitor.get_source_summary(SignalSource.MEMORY)
        assert summary["count"] == 0
        assert summary["trend"] == "stable"

    def test_source_summary(self, monitor):
        for v in [0.1, 0.15, 0.12, 0.18, 0.14, 0.2]:
            monitor.ingest(HealthSignal(
                source=SignalSource.ERROR_RATE,
                severity=SignalSeverity.WARN,
                value=v,
            ))
        summary = monitor.get_source_summary(SignalSource.ERROR_RATE)
        assert summary["count"] == 6
        assert "mean_value" in summary
        assert "trend" in summary

    def test_snapshot_reflects_signals(self, monitor):
        monitor.ingest(HealthSignal(
            source=SignalSource.ERROR_RATE,
            severity=SignalSeverity.CRITICAL,
            value=0.95,
        ))
        snap = monitor.snapshot()
        per_source = {s[0]: s for s in snap.per_source}
        assert "error_rate" in per_source
        assert per_source["error_rate"][1] == "critical"

    def test_register_anomaly(self, monitor):
        monitor.register_anomaly(AnomalyRecord(
            anomaly_type=AnomalyType.SPIKE,
            source="error_rate",
            metric="default",
            detected_value=0.9,
            expected_range=(0.0, 0.3),
            z_score=3.5,
            confidence=0.95,
        ))
        snap = monitor.snapshot()
        assert snap.anomaly_count == 1

    def test_set_active_playbook(self, monitor):
        monitor.set_active_playbook("pb-error-spike")
        assert monitor.active_playbook == "pb-error-spike"

    def test_clear(self, monitor):
        monitor.ingest(HealthSignal(
            source=SignalSource.ERROR_RATE,
            severity=SignalSeverity.WARN,
            value=0.5,
        ))
        monitor.register_anomaly(AnomalyRecord(
            anomaly_type=AnomalyType.SPIKE,
            source="error_rate",
            metric="default",
            detected_value=0.9,
            expected_range=(0.0, 0.3),
            z_score=3.5,
            confidence=0.95,
        ))
        monitor.clear()
        assert monitor.signal_count == 0

    def test_prune_old_signals(self, monitor):
        old_ts = time.time() - 1000
        monitor.ingest(HealthSignal(
            source=SignalSource.ERROR_RATE,
            severity=SignalSeverity.WARN,
            value=0.5,
            timestamp=old_ts,
        ))
        monitor.ingest(HealthSignal(
            source=SignalSource.ERROR_RATE,
            severity=SignalSeverity.OK,
            value=0.1,
        ))
        assert monitor.signal_count == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Anomaly Detection
# ═══════════════════════════════════════════════════════════════════════════════


class TestAnomalyType:
    def test_values(self):
        assert AnomalyType.SPIKE.value == "spike"
        assert AnomalyType.DIP.value == "dip"
        assert AnomalyType.DRIFT.value == "drift"
        assert AnomalyType.PATTERN_BREAK.value == "pattern_break"


class TestAnomalyRecord:
    def test_create(self):
        rec = AnomalyRecord(
            anomaly_type=AnomalyType.SPIKE,
            source="error_rate",
            metric="default",
            detected_value=0.95,
            expected_range=(0.1, 0.3),
            z_score=3.5,
            confidence=0.95,
            description="Spike detected",
        )
        assert rec.anomaly_type == AnomalyType.SPIKE
        assert rec.source == "error_rate"
        assert rec.z_score == 3.5
        assert rec.is_significant is True

    def test_not_significant(self):
        rec = AnomalyRecord(
            anomaly_type=AnomalyType.DIP,
            source="latency",
            metric="default",
            detected_value=0.01,
            expected_range=(0.1, 0.3),
            z_score=1.5,
            confidence=0.4,
        )
        assert rec.is_significant is False

    def test_is_frozen(self):
        rec = AnomalyRecord(
            anomaly_type=AnomalyType.SPIKE,
            source="error_rate",
            metric="default",
            detected_value=0.9,
            expected_range=(0.0, 0.3),
            z_score=3.5,
            confidence=0.95,
        )
        with pytest.raises(Exception):  # noqa: B017
            rec.z_score = 4.0  # type: ignore[misc]


class TestAnomalyDetector:
    @pytest.fixture
    def detector(self):
        return AnomalyDetector()

    def test_initial_state(self, detector):
        assert detector.z_threshold == 2.0
        assert detector.drift_window == 20
        assert detector.min_samples == 5

    def test_detect_spike(self, detector):
        values = [0.1, 0.12, 0.11, 0.13, 0.1, 0.9]
        result = detector.detect(values, source="error_rate")
        assert result is not None
        assert result.anomaly_type == AnomalyType.SPIKE
        assert result.z_score > 2.0
        assert result.is_significant is True

    def test_detect_dip(self, detector):
        values = [0.5, 0.52, 0.51, 0.53, 0.5, 0.05]
        result = detector.detect(values, source="error_rate")
        assert result is not None
        assert result.anomaly_type == AnomalyType.DIP

    def test_no_anomaly_stable(self, detector):
        values = [0.1, 0.12, 0.11, 0.13, 0.1, 0.12]
        result = detector.detect(values, source="error_rate")
        assert result is None

    def test_not_enough_samples(self, detector):
        result = detector.detect([0.1, 0.2], source="error_rate")
        assert result is None

    def test_zero_std_different_values(self, detector):
        result = detector.detect([5.0, 5.0, 5.0, 5.0, 5.0, 10.0], source="latency")
        assert result is not None
        assert result.anomaly_type == AnomalyType.SPIKE

    def test_detect_drift(self, detector):
        detector.detect_drift([0.1] * 25, source="error_rate")
        drifted = [0.1] * 20 + [0.5] * 10
        result = detector.detect_drift(drifted, source="error_rate")
        assert result is not None
        assert result.anomaly_type == AnomalyType.DRIFT

    def test_detect_drift_not_enough(self, detector):
        result = detector.detect_drift([0.1] * 5, source="error_rate")
        assert result is None

    def test_detect_drift_first_call_sets_baseline(self, detector):
        baseline = [0.1] * 25
        result = detector.detect_drift(baseline, source="error_rate")
        assert result is None

    def test_reset_baseline(self, detector):
        baseline = [0.1] * 25
        detector.detect_drift(baseline, source="error_rate")
        detector.reset_baseline("error_rate")
        result = detector.detect_drift(baseline, source="error_rate")
        assert result is None

    def test_clear_baselines(self, detector):
        detector.detect_drift([0.1] * 25, source="error_rate")
        detector.detect_drift([0.2] * 25, source="latency")
        detector.clear_baselines()
        result = detector.detect_drift([0.1] * 25, source="error_rate")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# Recovery Playbooks
# ═══════════════════════════════════════════════════════════════════════════════


class TestPlaybookStatus:
    def test_values(self):
        assert PlaybookStatus.PENDING.value == "pending"
        assert PlaybookStatus.RUNNING.value == "running"
        assert PlaybookStatus.COMPLETED.value == "completed"
        assert PlaybookStatus.FAILED.value == "failed"
        assert PlaybookStatus.ROLLED_BACK.value == "rolled_back"


class TestPlaybookStep:
    def test_create(self):
        step = PlaybookStep(
            order=1,
            action="throttle_requests",
            description="Reduce incoming request rate",
        )
        assert step.order == 1
        assert step.action == "throttle_requests"
        assert step.verify_after is True
        assert step.timeout_seconds == 30.0
        assert step.rollback_action == ""

    def test_is_frozen(self):
        step = PlaybookStep(order=1, action="restart")
        with pytest.raises(Exception):  # noqa: B017
            step.order = 2  # type: ignore[misc]


class TestRecoveryResult:
    def test_success(self):
        result = RecoveryResult(
            playbook_id="pb1",
            status=PlaybookStatus.COMPLETED,
            steps_completed=3,
            total_steps=3,
        )
        assert result.is_success is True
        assert result.progress_pct == 100.0

    def test_failed(self):
        result = RecoveryResult(
            playbook_id="pb1",
            status=PlaybookStatus.FAILED,
            steps_completed=1,
            total_steps=3,
            error_message="Step 2 timed out",
        )
        assert result.is_success is False
        assert result.progress_pct == pytest.approx(33.3333, abs=0.01)

    def test_zero_steps_progress(self):
        result = RecoveryResult(
            playbook_id="pb1",
            status=PlaybookStatus.COMPLETED,
            steps_completed=0,
            total_steps=0,
        )
        assert result.progress_pct == 100.0

    def test_is_frozen(self):
        result = RecoveryResult(
            playbook_id="pb1",
            status=PlaybookStatus.COMPLETED,
            steps_completed=1,
            total_steps=1,
        )
        with pytest.raises(Exception):  # noqa: B017
            result.status = PlaybookStatus.FAILED  # type: ignore[misc]


class TestRecoveryPlaybook:
    def test_create(self):
        steps = (
            PlaybookStep(order=1, action="throttle"),
            PlaybookStep(order=2, action="restart", verify_after=False),
        )
        pb = RecoveryPlaybook(
            id="pb-err-spike",
            name="Error Spike Recovery",
            anomaly_type="spike",
            signal_source="error_rate",
            steps=steps,
            description="Handles error rate spikes",
            max_retries=3,
            cooldown_seconds=120.0,
        )
        assert pb.id == "pb-err-spike"
        assert pb.step_count == 2
        assert pb.max_retries == 3
        assert pb.cooldown_seconds == 120.0

    def test_is_frozen(self):
        pb = RecoveryPlaybook(
            id="pb1",
            name="Test",
            anomaly_type="spike",
            signal_source="error_rate",
            steps=(),
        )
        with pytest.raises(Exception):  # noqa: B017
            pb.name = "Changed"  # type: ignore[misc]


class TestPlaybookRegistry:
    @pytest.fixture
    def registry(self):
        return PlaybookRegistry()

    def test_initial_state(self, registry):
        assert registry.playbook_count == 0
        assert registry.history_count == 0

    def test_register_and_find(self, registry):
        pb = RecoveryPlaybook(
            id="pb1",
            name="Error Spike Recovery",
            anomaly_type="spike",
            signal_source="error_rate",
            steps=(PlaybookStep(order=1, action="throttle"),),
        )
        registry.register(pb)
        assert registry.playbook_count == 1
        found = registry.find("spike", "error_rate")
        assert found is not None
        assert found.id == "pb1"

    def test_register_merges(self, registry):
        pb1 = RecoveryPlaybook(
            id="pb1",
            name="V1",
            anomaly_type="spike",
            signal_source="error_rate",
            steps=(PlaybookStep(order=1, action="throttle"),),
        )
        pb2 = RecoveryPlaybook(
            id="pb2",
            name="V2",
            anomaly_type="spike",
            signal_source="error_rate",
            steps=(PlaybookStep(order=2, action="restart"),),
        )
        registry.register(pb1)
        registry.register(pb2)
        merged = registry.find("spike", "error_rate")
        assert merged is not None
        assert merged.step_count == 2

    def test_find_missing(self, registry):
        assert registry.find("nonexistent", "error_rate") is None

    def test_can_run_first_time(self, registry):
        pb = RecoveryPlaybook(
            id="pb1",
            name="Test",
            anomaly_type="spike",
            signal_source="error_rate",
            steps=(),
        )
        registry.register(pb)
        assert registry.can_run("pb1") is True

    def test_can_run_cooldown(self, registry):
        pb = RecoveryPlaybook(
            id="pb1",
            name="Test",
            anomaly_type="spike",
            signal_source="error_rate",
            steps=(),
            cooldown_seconds=3600,
        )
        registry.register(pb)
        registry.record_result(RecoveryResult(
            playbook_id="pb1",
            status=PlaybookStatus.COMPLETED,
            steps_completed=1,
            total_steps=1,
        ))
        assert registry.can_run("pb1") is False

    def test_can_run_missing_id(self, registry):
        assert registry.can_run("nonexistent") is True

    def test_record_and_get_history(self, registry):
        r1 = RecoveryResult(
            playbook_id="pb1",
            status=PlaybookStatus.COMPLETED,
            steps_completed=1,
            total_steps=1,
        )
        r2 = RecoveryResult(
            playbook_id="pb1",
            status=PlaybookStatus.FAILED,
            steps_completed=0,
            total_steps=2,
        )
        registry.record_result(r1)
        registry.record_result(r2)
        assert registry.history_count == 2
        assert len(registry.get_history("pb1")) == 2
        assert len(registry.get_history("unknown")) == 0

    def test_list_playbooks(self, registry):
        registry.register(RecoveryPlaybook(
            id="pb1", name="PB1",
            anomaly_type="spike", signal_source="error_rate",
            steps=(),
        ))
        registry.register(RecoveryPlaybook(
            id="pb2", name="PB2",
            anomaly_type="drift", signal_source="latency",
            steps=(),
        ))
        assert len(registry.list_playbooks()) == 2

    def test_clear(self, registry):
        registry.register(RecoveryPlaybook(
            id="pb1", name="PB1",
            anomaly_type="spike", signal_source="error_rate",
            steps=(),
        ))
        registry.record_result(RecoveryResult(
            playbook_id="pb1",
            status=PlaybookStatus.COMPLETED,
            steps_completed=1,
            total_steps=1,
        ))
        registry.clear()
        assert registry.playbook_count == 0
        assert registry.history_count == 0
