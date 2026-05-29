"""Tests for lyra-sla package."""

from __future__ import annotations

import asyncio
import time

import pytest
from lyra_sla import (
    SLA,
    SLO,
    AutoScaler,
    BudgetExceededError,
    BudgetType,
    ComplianceReport,
    ComplianceReporter,
    DashboardGenerator,
    InvalidMetricError,
    # Metrics
    MetricsCollector,
    PredictiveScaler,
    ReactiveScaler,
    ReportExporter,
    # Reporting
    ReportFormat,
    ResourceConfig,
    ScalingDirection,
    SLAError,
    SLAManager,
    SLANotFoundError,
    SLIMetric,
    TrendAnalyzer,
)

# ── SLAManager ──────────────────────────────────────────────────────────


class TestSLAManager:
    def test_define_sla(self):
        mgr = SLAManager()
        slo = SLO(metric=SLIMetric.LATENCY_P95, target=5000.0, comparator="lt")
        sla = SLA(agent_id="agent_1", name="test_sla", slos=[slo])
        mgr.define_sla(sla)
        assert mgr.get_sla("agent_1") is not None

    def test_record_and_check_compliance(self):
        mgr = SLAManager()
        slo = SLO(metric=SLIMetric.LATENCY_P95, target=5000.0, comparator="lt")
        sla = SLA(agent_id="agent_1", slos=[slo])
        mgr.define_sla(sla)
        for _ in range(100):
            mgr.record_metric("agent_1", "latency_p95", 100.0)
        result = asyncio.run(mgr.check_compliance("agent_1"))
        assert "compliant" in result
        assert result["compliant"]

    def test_no_sla_no_violation(self):
        mgr = SLAManager()
        result = asyncio.run(mgr.check_compliance("unknown"))
        assert result["compliant"]

    def test_violation_detected(self):
        mgr = SLAManager()
        slo = SLO(metric=SLIMetric.LATENCY_P95, target=100.0, comparator="lt")
        sla = SLA(agent_id="agent_1", slos=[slo])
        mgr.define_sla(sla)
        for _ in range(100):
            mgr.record_metric("agent_1", "latency_p95", 5000.0)
        result = asyncio.run(mgr.check_compliance("agent_1"))
        assert not result["compliant"] or result["violated_slos"] > 0

    def test_summary(self):
        mgr = SLAManager()
        s = mgr.summary
        assert "agents_with_sla" in s

    def test_budget_management(self):
        mgr = SLAManager()
        budget = mgr.set_budget("agent_1", BudgetType.TOKEN, 10000.0)
        assert budget.limit == 10000.0
        remaining = mgr.consume_budget("agent_1", BudgetType.TOKEN, 500.0)
        assert remaining == 9500.0
        b = mgr.get_budget("agent_1", BudgetType.TOKEN)
        assert b is not None
        assert b.consumed == 500.0

    def test_budget_exceeded(self):
        mgr = SLAManager()
        mgr.set_budget("agent_1", BudgetType.COST, 10.0)
        with pytest.raises(BudgetExceededError):
            mgr.consume_budget("agent_1", BudgetType.COST, 15.0)

    def test_invalid_metric(self):
        mgr = SLAManager()
        with pytest.raises(InvalidMetricError):
            mgr.record_metric("agent_1", "invalid_metric", 1.0)

    def test_list_slas(self):
        mgr = SLAManager()
        mgr.define_sla(SLA(agent_id="a1"))
        mgr.define_sla(SLA(agent_id="a2"))
        assert len(mgr.list_slas()) == 2

    def test_remove_sla(self):
        mgr = SLAManager()
        mgr.define_sla(SLA(agent_id="a1"))
        assert mgr.remove_sla("a1")
        assert mgr.get_sla("a1") is None


# ── MetricsCollector ────────────────────────────────────────────────────


class TestMetricsCollector:
    def test_observe_and_query(self):
        mc = MetricsCollector()
        mc.observe("agent_1", "latency_p95", 100.0)
        values = mc.query("agent_1", "latency_p95")
        assert len(values) == 1
        assert values[0] == 100.0

    def test_observe_batch(self):
        mc = MetricsCollector()
        mc.observe_batch("agent_1", {"latency_p95": 50.0, "error_rate": 0.01})
        assert mc.agent_count == 1

    def test_compute_stats(self):
        mc = MetricsCollector()
        for v in [10.0, 20.0, 30.0, 40.0, 50.0]:
            mc.observe("agent_1", "latency_p95", v)
        stats = mc.compute_stats("agent_1", "latency_p95")
        assert stats.count == 5
        assert 25 < stats.mean < 35
        assert stats.p50 > 0

    def test_percentile(self):
        mc = MetricsCollector()
        for v in range(1, 101):
            mc.observe("agent_1", "latency_p95", float(v))
        p95 = mc.percentile("agent_1", "latency_p95", 95.0)
        assert 90 < p95 < 100

    def test_export_prometheus(self):
        mc = MetricsCollector()
        mc.observe("agent_1", "latency_p95", 100.0)
        exported = mc.export_prometheus()
        assert "lyra_latency_p95" in exported
        assert "# HELP" in exported

    def test_export_json(self):
        mc = MetricsCollector()
        mc.observe("agent_1", "latency_p95", 100.0)
        data = mc.export_json("agent_1")
        assert "agents" in data
        assert "agent_1" in data["agents"]

    def test_clear_agent(self):
        mc = MetricsCollector()
        mc.observe("agent_1", "latency_p95", 100.0)
        mc.clear_agent("agent_1")
        assert mc.agent_count == 0

    def test_summary(self):
        mc = MetricsCollector()
        mc.observe("agent_1", "latency_p95", 100.0)
        s = mc.summary
        assert s["agents_tracked"] == 1


# ── AutoScaler ──────────────────────────────────────────────────────────


class TestAutoScaler:
    @pytest.fixture
    def scaler(self):
        mgr = SLAManager()
        mc = MetricsCollector(sla_manager=mgr)
        return AutoScaler(sla_manager=mgr, metrics_collector=mc)

    def test_configure(self, scaler):
        config = ResourceConfig(min_replicas=2, max_replicas=8, current_replicas=4)
        scaler.configure("agent_1", config)
        cfg = scaler.get_config("agent_1")
        assert cfg.min_replicas == 2
        assert cfg.max_replicas == 8

    @pytest.mark.asyncio
    async def test_evaluate_scaling(self, scaler):
        config = ResourceConfig(current_replicas=2, max_replicas=5)
        scaler.configure("agent_1", config)
        scaler.metrics.observe("agent_1", "latency_p95", 100.0)
        decision = await scaler.evaluate_scaling("agent_1")
        assert decision is not None

    def test_summary(self, scaler):
        s = scaler.summary
        assert "strategy" in s


class TestReactiveScaler:
    def test_evaluate_no_data(self):
        rs = ReactiveScaler()
        config = ResourceConfig(current_replicas=2)
        decision = rs.evaluate("agent_1", {}, config)
        assert decision.direction == ScalingDirection.NONE


class TestPredictiveScaler:
    def test_predict_demand(self):
        ps = PredictiveScaler()
        data = [(float(i), float(i)) for i in range(50)]
        pred = ps.predict_demand("agent_1", data, horizon_seconds=60.0)
        assert pred > 0


# ── Reporting ───────────────────────────────────────────────────────────


class TestDashboardGenerator:
    def test_generate(self):
        mgr = SLAManager()
        mc = MetricsCollector(sla_manager=mgr)
        gen = DashboardGenerator(sla_manager=mgr, metrics_collector=mc)
        data = gen.generate_dashboard_data()
        assert "panels" in data


class TestComplianceReporter:
    def test_generate_report(self):
        mgr = SLAManager()
        mc = MetricsCollector(sla_manager=mgr)
        reporter = ComplianceReporter(sla_manager=mgr, metrics_collector=mc)
        now = time.time()
        report = reporter.generate_report("agent_1", now - 3600, now)
        assert isinstance(report, ComplianceReport)


class TestTrendAnalyzer:
    def test_analyze_empty(self):
        mc = MetricsCollector()
        ta = TrendAnalyzer(metrics_collector=mc)
        trend = ta.analyze("agent_1", "latency_p95")
        assert trend.trend_direction == "stable"


class TestReportExporter:
    def test_export_formats(self):
        exporter = ReportExporter()
        report = ComplianceReport(
            report_id="rpt_1", agent_id="test", period_start=0, period_end=1
        )
        json_str = exporter.export(report, ReportFormat.JSON)
        assert "rpt_1" in json_str
        md_str = exporter.export(report, ReportFormat.MARKDOWN)
        assert "test" in md_str
        txt_str = exporter.export(report, ReportFormat.TEXT)
        assert "test" in txt_str


# ── Exceptions ────────────────────────────────────────────────────────


class TestExceptions:
    def test_sla_error(self):
        with pytest.raises(SLAError):
            raise SLAError("test")

    def test_sla_not_found(self):
        with pytest.raises(SLANotFoundError):
            raise SLANotFoundError("agent_x")

    def test_budget_exceeded(self):
        with pytest.raises(BudgetExceededError):
            raise BudgetExceededError("TOKEN", 100.0, 150.0)

    def test_invalid_metric(self):
        with pytest.raises(InvalidMetricError):
            raise InvalidMetricError("bad", ["latency_p50"])
