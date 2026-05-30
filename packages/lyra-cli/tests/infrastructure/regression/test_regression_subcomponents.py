"""Tests for regression sub-components — comparator, history store, and alert manager."""

from __future__ import annotations

import tempfile

import pytest

from lyra_cli.infrastructure.regression.alert_manager import (
    AlertManager,
    AlertRule,
    AlertSeverity,
)
from lyra_cli.infrastructure.regression.comparator import (
    BenchmarkComparator,
    ComparisonVerdict,
    MetricComparison,
)
from lyra_cli.infrastructure.regression.history_store import (
    BenchmarkRun,
    HistoryQuery,
    HistoryStore,
)


# ── BenchmarkComparator Tests ──


class TestBenchmarkComparator:
    @pytest.fixture
    def comparator(self):
        return BenchmarkComparator(
            regression_threshold_pct=5.0,
            lower_is_better={"latency_ms", "error_rate", "memory_mb"},
        )

    def test_regression_detected(self, comparator):
        baseline = {"latency_ms": 100.0}
        current = {"latency_ms": 115.0}  # +15%, above 5% threshold
        result = comparator.compare("v1", "v2", baseline, current)
        assert result.regression_count == 1
        assert result.overall_verdict == ComparisonVerdict.REGRESSED

    def test_improvement_detected(self, comparator):
        baseline = {"latency_ms": 100.0}
        current = {"latency_ms": 90.0}
        result = comparator.compare("v1", "v2", baseline, current)
        assert result.improvement_count == 1

    def test_stable_metric(self, comparator):
        baseline = {"latency_ms": 100.0}
        current = {"latency_ms": 101.0}  # +1%, within threshold
        result = comparator.compare("v1", "v2", baseline, current)
        assert result.stable_count == 1

    def test_new_metric(self, comparator):
        baseline = {"latency_ms": 100.0}
        current = {"latency_ms": 100.0, "new_metric": 50.0}
        result = comparator.compare("v1", "v2", baseline, current)
        assert any(c.verdict == ComparisonVerdict.NEW for c in result.comparisons)

    def test_removed_metric(self, comparator):
        baseline = {"latency_ms": 100.0, "old_metric": 50.0}
        current = {"latency_ms": 100.0}
        result = comparator.compare("v1", "v2", baseline, current)
        assert any(c.verdict == ComparisonVerdict.REMOVED for c in result.comparisons)

    def test_critical_regression_severity(self, comparator):
        baseline = {"latency_ms": 100.0}
        current = {"latency_ms": 125.0}  # +25%, >20% threshold for critical
        result = comparator.compare("v1", "v2", baseline, current)
        regressed = [c for c in result.comparisons if c.verdict == ComparisonVerdict.REGRESSED]
        assert len(regressed) == 1
        assert regressed[0].severity == "critical"

    def test_warning_regression_severity(self, comparator):
        baseline = {"latency_ms": 100.0}
        current = {"latency_ms": 112.0}  # +12%, >10% threshold for warning
        result = comparator.compare("v1", "v2", baseline, current)
        regressed = [c for c in result.comparisons if c.verdict == ComparisonVerdict.REGRESSED]
        assert len(regressed) == 1
        assert regressed[0].severity == "warning"

    def test_info_regression_severity(self, comparator):
        baseline = {"latency_ms": 100.0}
        current = {"latency_ms": 107.0}  # +7%, >5% threshold
        result = comparator.compare("v1", "v2", baseline, current)
        regressed = [c for c in result.comparisons if c.verdict == ComparisonVerdict.REGRESSED]
        assert len(regressed) == 1
        assert regressed[0].severity == "info"

    def test_multiple_metrics(self, comparator):
        baseline = {"latency_ms": 100.0, "throughput": 1000.0, "memory_mb": 256.0}
        current = {"latency_ms": 110.0, "throughput": 950.0, "memory_mb": 256.0}
        result = comparator.compare("v1", "v2", baseline, current)
        assert len(result.comparisons) == 3
        assert result.summary != ""

    def test_overall_improved(self, comparator):
        baseline = {"latency_ms": 100.0, "error_rate": 10.0, "memory_mb": 256.0}
        current = {"latency_ms": 80.0, "error_rate": 5.0, "memory_mb": 200.0}
        result = comparator.compare("v1", "v2", baseline, current)
        assert result.overall_verdict == ComparisonVerdict.IMPROVED

    def test_zero_baseline_handled(self, comparator):
        baseline = {"metric": 0.0}
        current = {"metric": 10.0}
        result = comparator.compare("v1", "v2", baseline, current)
        assert result.regression_count == 0


class TestComparisonVerdict:
    def test_values(self):
        assert ComparisonVerdict.IMPROVED == "improved"
        assert ComparisonVerdict.REGRESSED == "regressed"
        assert ComparisonVerdict.STABLE == "stable"


class TestMetricComparison:
    def test_immutability(self):
        mc = MetricComparison(
            metric_name="test", baseline_value=1.0, current_value=2.0,
            delta_pct=100.0, verdict=ComparisonVerdict.IMPROVED,
        )
        with pytest.raises(Exception):
            mc.metric_name = "other"


# ── HistoryStore Tests ──


class TestHistoryStore:
    @pytest.fixture
    def store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield HistoryStore(storage_dir=tmpdir)

    def test_save_and_get(self, store):
        run = BenchmarkRun(
            run_id="run-001", timestamp=1000.0,
            metrics={"latency": 45.0}, metadata={}, tag="release",
        )
        store.save(run)
        retrieved = store.get("run-001")
        assert retrieved is not None
        assert retrieved.metrics["latency"] == 45.0

    def test_query_by_metric(self, store):
        store.save(BenchmarkRun("r1", 1000.0, {"latency": 45.0}, {}, "v1"))
        store.save(BenchmarkRun("r2", 2000.0, {"throughput": 500.0}, {}, "v1"))
        results = store.query(HistoryQuery(metric_name="latency"))
        assert len(results) == 1
        assert results[0].run_id == "r1"

    def test_query_by_tag(self, store):
        store.save(BenchmarkRun("r1", 1000.0, {"x": 1.0}, {}, "release"))
        store.save(BenchmarkRun("r2", 2000.0, {"x": 2.0}, {}, "dev"))
        results = store.query(HistoryQuery(tag="release"))
        assert len(results) == 1

    def test_query_since(self, store):
        store.save(BenchmarkRun("r1", 1000.0, {"x": 1.0}, {}, ""))
        store.save(BenchmarkRun("r2", 2000.0, {"x": 2.0}, {}, ""))
        store.save(BenchmarkRun("r3", 3000.0, {"x": 3.0}, {}, ""))
        results = store.query(HistoryQuery(since=2000.0))
        assert len(results) == 2

    def test_query_limit(self, store):
        for i in range(10):
            store.save(BenchmarkRun(f"r{i}", float(i), {"x": float(i)}, {}, ""))
        results = store.query(HistoryQuery(limit=3))
        assert len(results) == 3

    def test_get_trend(self, store):
        for i in range(5):
            store.save(BenchmarkRun(f"r{i}", float(i), {"latency": float(i * 10)}, {}, ""))
        trend = store.get_trend("latency", window=5)
        assert len(trend) == 5
        assert trend == [0.0, 10.0, 20.0, 30.0, 40.0]

    def test_get_latest(self, store):
        store.save(BenchmarkRun("r1", 1000.0, {"x": 1.0}, {}, ""))
        store.save(BenchmarkRun("r2", 2000.0, {"x": 2.0}, {}, ""))
        latest = store.get_latest()
        assert latest is not None
        assert latest.run_id == "r2"

    def test_get_latest_empty(self, store):
        assert store.get_latest() is None

    def test_delete(self, store):
        store.save(BenchmarkRun("r1", 1000.0, {"x": 1.0}, {}, ""))
        store.delete("r1")
        assert store.get("r1") is None

    def test_list_runs(self, store):
        store.save(BenchmarkRun("a", 1000.0, {}, {}, ""))
        store.save(BenchmarkRun("b", 2000.0, {}, {}, ""))
        runs = store.list_runs()
        assert len(runs) == 2

    def test_clear(self, store):
        store.save(BenchmarkRun("r1", 1000.0, {"x": 1.0}, {}, ""))
        store.clear()
        assert store.run_count == 0

    def test_run_count(self, store):
        assert store.run_count == 0
        store.save(BenchmarkRun("r1", 1000.0, {}, {}, ""))
        assert store.run_count == 1


class TestBenchmarkRun:
    def test_immutability(self):
        run = BenchmarkRun(run_id="r1", timestamp=1.0, metrics={}, metadata={})
        with pytest.raises(Exception):
            run.run_id = "r2"


# ── AlertManager Tests ──


class TestAlertManager:
    @pytest.fixture
    def mgr(self):
        return AlertManager()

    def test_no_alert_without_rules(self, mgr):
        alert = mgr.check_metric("latency", 100.0, 50.0)
        assert alert is None

    def test_alert_fires_on_threshold(self, mgr):
        mgr.add_rule("latency_*", threshold_pct=10.0, severity=AlertSeverity.WARNING)
        alert = mgr.check_metric("latency_p95", 120.0, 100.0)
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.deviation_pct == 20.0

    def test_no_alert_below_threshold(self, mgr):
        mgr.add_rule("latency_*", threshold_pct=10.0)
        alert = mgr.check_metric("latency_p95", 105.0, 100.0)
        assert alert is None

    def test_critical_alert(self, mgr):
        mgr.add_rule("*", threshold_pct=20.0, severity=AlertSeverity.CRITICAL)
        alert = mgr.check_metric("error_rate", 50.0, 10.0)  # 400% deviation
        assert alert is not None
        assert alert.severity == AlertSeverity.CRITICAL

    def test_cooldown_respected(self, mgr):
        mgr.add_rule("*", threshold_pct=5.0, cooldown_seconds=999.0)
        first = mgr.check_metric("latency", 120.0, 100.0)
        second = mgr.check_metric("latency", 120.0, 100.0)
        assert first is not None
        assert second is None  # cooldown prevents second alert

    def test_pattern_matching(self, mgr):
        mgr.add_rule("latency_*", threshold_pct=5.0)
        assert mgr.check_metric("latency_p50", 110.0, 100.0) is not None
        assert mgr.check_metric("throughput", 110.0, 100.0) is None  # doesn't match

    def test_disabled_rule(self, mgr):
        rule = mgr.add_rule("*", threshold_pct=5.0)
        rule.enabled = False
        assert mgr.check_metric("latency", 110.0, 100.0) is None

    def test_acknowledge_alert(self, mgr):
        mgr.add_rule("*", threshold_pct=5.0)
        alert = mgr.check_metric("latency", 110.0, 100.0)
        assert alert is not None
        assert mgr.acknowledge(alert.alert_id)
        assert not mgr.acknowledge("nonexistent-id")

    def test_get_alerts_by_severity(self, mgr):
        mgr.add_rule("a_*", threshold_pct=5.0, severity=AlertSeverity.WARNING)
        mgr.add_rule("b_*", threshold_pct=5.0, severity=AlertSeverity.CRITICAL)
        mgr.check_metric("a_metric", 120.0, 100.0)
        mgr.check_metric("b_metric", 120.0, 100.0)
        assert len(mgr.get_alerts_by_severity(AlertSeverity.WARNING)) == 1
        assert len(mgr.get_alerts_by_severity(AlertSeverity.CRITICAL)) == 1

    def test_get_alerts_by_metric(self, mgr):
        mgr.add_rule("*", threshold_pct=5.0)
        mgr.check_metric("latency", 120.0, 100.0)
        mgr.check_metric("throughput", 120.0, 100.0)
        assert len(mgr.get_alerts_by_metric("latency")) == 1

    def test_callback_invoked(self, mgr):
        received: list = []
        mgr.on_callback = lambda a: received.append(a)
        mgr.add_rule("*", threshold_pct=5.0)
        mgr.check_metric("latency", 120.0, 100.0)
        assert len(received) == 1

    def test_clear(self, mgr):
        mgr.add_rule("*", threshold_pct=5.0)
        mgr.check_metric("latency", 120.0, 100.0)
        mgr.clear()
        assert mgr.alert_count == 0

    def test_zero_baseline_no_alert(self, mgr):
        mgr.add_rule("*", threshold_pct=5.0)
        assert mgr.check_metric("latency", 10.0, 0.0) is None

    def test_alert_count(self, mgr):
        assert mgr.alert_count == 0
        mgr.add_rule("*", threshold_pct=5.0)
        mgr.check_metric("latency", 120.0, 100.0)
        assert mgr.alert_count == 1


class TestAlertRule:
    def test_rule_creation(self):
        rule = AlertRule(metric_pattern="*", threshold_pct=10.0, severity=AlertSeverity.WARNING)
        assert rule.enabled is True
        assert rule.cooldown_seconds == 300.0


class TestAlertSeverity:
    def test_values(self):
        assert AlertSeverity.CRITICAL == "critical"
        assert AlertSeverity.WARNING == "warning"
        assert AlertSeverity.INFO == "info"
