"""Tests for user-facing observability CLI commands."""

from __future__ import annotations

import pytest

from lyra_cli.observability.dashboard_command import (
    DashboardCommand,
    DashboardConfig,
    DashboardPanel,
    PanelType,
)
from lyra_cli.observability.health_command import (
    ComponentHealth,
    DependencyStatus,
    HealthCommand,
    HealthScore,
)
from lyra_cli.observability.metrics_command import (
    MetricsCommand,
    MetricsFilter,
    MetricsFormat,
    MetricsQuery,
    MetricType,
)
from lyra_cli.observability.trace_command import (
    SpanDetail,
    TraceCommand,
    TraceFilter,
    TraceTimeline,
)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def metrics_cmd():
    return MetricsCommand()


@pytest.fixture
def health_cmd():
    return HealthCommand()


@pytest.fixture
def trace_cmd():
    return TraceCommand()


@pytest.fixture
def dashboard_cmd():
    return DashboardCommand()


# ── TestMetricsCommand ────────────────────────────────────────


class TestMetricsQuery:
    def test_query_creation(self):
        q = MetricsQuery(
            metric_name="api_latency_ms",
            metric_type=MetricType.HISTOGRAM,
        )
        assert q.metric_name == "api_latency_ms"
        assert q.metric_type == MetricType.HISTOGRAM

    def test_query_immutability(self):
        q = MetricsQuery(metric_name="cpu_usage", metric_type=MetricType.GAUGE)
        with pytest.raises(Exception):
            q.metric_name = "other"


class TestMetricsFilter:
    def test_filter_creation(self):
        f = MetricsFilter(
            time_range_seconds=300,
            labels={"service": "lyra-router"},
            min_value=0.0,
            max_value=1000.0,
        )
        assert f.time_range_seconds == 300
        assert f.labels["service"] == "lyra-router"

    def test_filter_defaults(self):
        f = MetricsFilter()
        assert f.time_range_seconds is None
        assert f.labels == {}
        assert f.min_value is None


class TestMetricsCommandBasic:
    def test_empty_metrics(self, metrics_cmd):
        assert metrics_cmd.metric_count == 0

    def test_record_counter(self, metrics_cmd):
        metrics_cmd.record("task_completed", 1.0, MetricType.COUNTER)
        assert metrics_cmd.metric_count == 1

    def test_record_gauge(self, metrics_cmd):
        metrics_cmd.record("memory_usage_mb", 512.0, MetricType.GAUGE)
        assert metrics_cmd.metric_count == 1

    def test_record_histogram(self, metrics_cmd):
        metrics_cmd.record("api_latency_ms", 42.5, MetricType.HISTOGRAM)
        assert metrics_cmd.metric_count == 1

    def test_record_multiple_values(self, metrics_cmd):
        for i in range(5):
            metrics_cmd.record("api_latency_ms", float(i * 10), MetricType.HISTOGRAM)
        assert metrics_cmd.metric_count == 1
        data = metrics_cmd.get_metric("api_latency_ms")
        assert data is not None
        assert data["count"] == 5

    def test_get_metric_missing(self, metrics_cmd):
        assert metrics_cmd.get_metric("nonexistent") is None

    def test_query_with_filter(self, metrics_cmd):
        for i in range(10):
            metrics_cmd.record("api_latency_ms", float(i * 10), MetricType.HISTOGRAM,
                               labels={"service": "lyra-router"})
        f = MetricsFilter(time_range_seconds=60)
        results = metrics_cmd.query("api_latency_ms", f)
        assert results is not None
        assert results["count"] == 10

    def test_query_nonexistent_metric(self, metrics_cmd):
        f = MetricsFilter()
        results = metrics_cmd.query("nonexistent", f)
        assert results is None

    def test_format_output_json(self, metrics_cmd):
        metrics_cmd.record("cpu_usage", 75.0, MetricType.GAUGE)
        output = metrics_cmd.format_output(format=MetricsFormat.JSON)
        assert "cpu_usage" in output

    def test_format_output_text(self, metrics_cmd):
        metrics_cmd.record("cpu_usage", 75.0, MetricType.GAUGE)
        output = metrics_cmd.format_output(format=MetricsFormat.TEXT)
        assert "cpu_usage" in output.lower()

    def test_list_metric_names(self, metrics_cmd):
        metrics_cmd.record("cpu", 50.0, MetricType.GAUGE)
        metrics_cmd.record("memory", 1024.0, MetricType.GAUGE)
        names = metrics_cmd.list_metric_names()
        assert "cpu" in names
        assert "memory" in names
        assert len(names) == 2

    def test_get_summary(self, metrics_cmd):
        for i in range(5):
            metrics_cmd.record("latency", float(i * 10), MetricType.HISTOGRAM)
        summary = metrics_cmd.get_summary("latency")
        assert summary is not None
        assert "p50" in summary
        assert "p95" in summary
        assert "p99" in summary

    def test_get_summary_missing(self, metrics_cmd):
        assert metrics_cmd.get_summary("nonexistent") is None

    def test_reset(self, metrics_cmd):
        metrics_cmd.record("cpu", 50.0, MetricType.GAUGE)
        metrics_cmd.reset()
        assert metrics_cmd.metric_count == 0


# ── TestHealthCommand ─────────────────────────────────────────


class TestComponentHealth:
    def test_healthy_component(self):
        c = ComponentHealth(
            name="lyra-router",
            status=DependencyStatus.HEALTHY,
        )
        assert c.is_healthy
        assert not c.is_degraded

    def test_degraded_component(self):
        c = ComponentHealth(
            name="lyra-router",
            status=DependencyStatus.DEGRADED,
            message="High latency detected",
        )
        assert c.is_degraded
        assert c.message == "High latency detected"

    def test_component_immutability(self):
        c = ComponentHealth(name="db", status=DependencyStatus.HEALTHY)
        with pytest.raises(Exception):
            c.status = DependencyStatus.UNHEALTHY


class TestHealthScore:
    def test_health_score_creation(self):
        s = HealthScore(overall=0.95, component_scores={"router": 0.98, "db": 0.92})
        assert s.overall == 0.95
        assert s.is_healthy

    def test_health_score_unhealthy(self):
        s = HealthScore(overall=0.55, component_scores={})
        assert not s.is_healthy

    def test_health_score_immutability(self):
        s = HealthScore(overall=0.8, component_scores={})
        with pytest.raises(Exception):
            s.overall = 0.9


class TestHealthCommandBasic:
    def test_empty_health(self, health_cmd):
        assert health_cmd.component_count == 0

    def test_register_component(self, health_cmd):
        health_cmd.register_component("router", status=DependencyStatus.HEALTHY)
        assert health_cmd.component_count == 1

    def test_get_component(self, health_cmd):
        health_cmd.register_component("router", status=DependencyStatus.HEALTHY)
        c = health_cmd.get_component("router")
        assert c is not None
        assert c.is_healthy

    def test_get_component_missing(self, health_cmd):
        assert health_cmd.get_component("nonexistent") is None

    def test_update_component_status(self, health_cmd):
        health_cmd.register_component("router", status=DependencyStatus.HEALTHY)
        health_cmd.update_component("router", status=DependencyStatus.DEGRADED,
                                     message="High latency")
        c = health_cmd.get_component("router")
        assert c.is_degraded

    def test_check_all_healthy(self, health_cmd):
        health_cmd.register_component("router", status=DependencyStatus.HEALTHY)
        health_cmd.register_component("db", status=DependencyStatus.HEALTHY)
        score = health_cmd.check_all()
        assert score.overall == 1.0
        assert score.is_healthy

    def test_check_all_with_degraded(self, health_cmd):
        health_cmd.register_component("router", status=DependencyStatus.HEALTHY)
        health_cmd.register_component("db", status=DependencyStatus.DEGRADED)
        score = health_cmd.check_all()
        assert score.overall < 1.0

    def test_check_all_with_unhealthy(self, health_cmd):
        health_cmd.register_component("router", status=DependencyStatus.UNHEALTHY)
        score = health_cmd.check_all()
        assert not score.is_healthy

    def test_get_recommendations(self, health_cmd):
        health_cmd.register_component("router", status=DependencyStatus.DEGRADED,
                                       message="High latency")
        recs = health_cmd.get_recommendations()
        assert len(recs) > 0

    def test_get_recommendations_all_healthy(self, health_cmd):
        health_cmd.register_component("router", status=DependencyStatus.HEALTHY)
        recs = health_cmd.get_recommendations()
        assert len(recs) == 0

    def test_reset(self, health_cmd):
        health_cmd.register_component("router", status=DependencyStatus.HEALTHY)
        health_cmd.reset()
        assert health_cmd.component_count == 0


# ── TestTraceCommand ──────────────────────────────────────────


class TestSpanDetail:
    def test_span_creation(self):
        s = SpanDetail(
            span_id="span-001",
            trace_id="trace-abc",
            operation="agent.execute",
            duration_ms=150.0,
        )
        assert s.span_id == "span-001"
        assert s.trace_id == "trace-abc"
        assert s.duration_ms == 150.0

    def test_span_immutability(self):
        s = SpanDetail(span_id="s1", trace_id="t1", operation="op", duration_ms=100.0)
        with pytest.raises(Exception):
            s.span_id = "s2"


class TestTraceFilter:
    def test_filter_defaults(self):
        f = TraceFilter()
        assert f.min_duration_ms is None
        assert f.has_error is None
        assert f.operation_prefix is None

    def test_filter_by_duration(self):
        f = TraceFilter(min_duration_ms=100.0)
        assert f.min_duration_ms == 100.0


class TestTraceCommandBasic:
    def test_empty_tracer(self, trace_cmd):
        assert trace_cmd.trace_count == 0

    def test_start_trace(self, trace_cmd):
        trace_id = trace_cmd.start_trace(operation="agent.execute")
        assert trace_cmd.trace_count == 1
        assert trace_id is not None

    def test_add_span(self, trace_cmd):
        trace_id = trace_cmd.start_trace(operation="workflow.run")
        span_id = trace_cmd.add_span(
            trace_id=trace_id,
            operation="agent.execute",
            duration_ms=100.0,
        )
        assert span_id is not None
        span = trace_cmd.get_span(span_id)
        assert span is not None
        assert span.operation == "agent.execute"

    def test_add_span_with_error(self, trace_cmd):
        trace_id = trace_cmd.start_trace(operation="workflow.run")
        span_id = trace_cmd.add_span(
            trace_id=trace_id,
            operation="tool.call",
            duration_ms=50.0,
            error="Connection refused",
        )
        span = trace_cmd.get_span(span_id)
        assert span is not None
        assert span.has_error

    def test_get_span_missing(self, trace_cmd):
        assert trace_cmd.get_span("nonexistent") is None

    def test_get_trace_timeline(self, trace_cmd):
        trace_id = trace_cmd.start_trace(operation="workflow.run")
        trace_cmd.add_span(trace_id=trace_id, operation="agent.execute", duration_ms=100.0)
        trace_cmd.add_span(trace_id=trace_id, operation="tool.call", duration_ms=50.0)
        timeline = trace_cmd.get_trace_timeline(trace_id)
        assert timeline is not None
        assert len(timeline.spans) == 2

    def test_get_trace_timeline_missing(self, trace_cmd):
        assert trace_cmd.get_trace_timeline("nonexistent") is None

    def test_filter_spans(self, trace_cmd):
        trace_id = trace_cmd.start_trace(operation="workflow.run")
        trace_cmd.add_span(trace_id=trace_id, operation="agent.execute", duration_ms=100.0)
        trace_cmd.add_span(trace_id=trace_id, operation="tool.call", duration_ms=50.0,
                           error="timeout")
        f = TraceFilter(has_error=True)
        errors = trace_cmd.filter_spans(f)
        assert len(errors) == 1

    def test_get_span_breakdown(self, trace_cmd):
        trace_id = trace_cmd.start_trace(operation="workflow.run")
        trace_cmd.add_span(trace_id=trace_id, operation="agent.execute", duration_ms=100.0)
        trace_cmd.add_span(trace_id=trace_id, operation="tool.call", duration_ms=50.0)
        breakdown = trace_cmd.get_span_breakdown(trace_id)
        assert breakdown["total_duration_ms"] > 0
        assert breakdown["span_count"] == 2

    def test_list_traces(self, trace_cmd):
        trace_cmd.start_trace(operation="workflow.run")
        trace_cmd.start_trace(operation="agent.execute")
        traces = trace_cmd.list_traces()
        assert len(traces) == 2

    def test_reset(self, trace_cmd):
        trace_cmd.start_trace(operation="workflow.run")
        trace_cmd.reset()
        assert trace_cmd.trace_count == 0


class TestTraceTimeline:
    def test_timeline_creation(self):
        t = TraceTimeline(
            trace_id="trace-abc",
            spans=(),
            total_duration_ms=250.0,
        )
        assert t.trace_id == "trace-abc"
        assert t.total_duration_ms == 250.0

    def test_timeline_immutability(self):
        t = TraceTimeline(trace_id="t1", spans=(), total_duration_ms=100.0)
        with pytest.raises(Exception):
            t.total_duration_ms = 200.0


# ── TestDashboardCommand ──────────────────────────────────────


class TestDashboardPanel:
    def test_panel_creation(self):
        p = DashboardPanel(
            title="System Overview",
            panel_type=PanelType.STATUS,
            content="All systems operational",
        )
        assert p.title == "System Overview"
        assert p.panel_type == PanelType.STATUS

    def test_panel_immutability(self):
        p = DashboardPanel(title="Metrics", panel_type=PanelType.METRICS, content="...")
        with pytest.raises(Exception):
            p.title = "Other"


class TestDashboardConfig:
    def test_default_config(self):
        cfg = DashboardConfig()
        assert cfg.refresh_interval_seconds == 2.0
        assert cfg.max_panels == 10
        assert cfg.show_alerts is True

    def test_custom_config(self):
        cfg = DashboardConfig(refresh_interval_seconds=5.0, max_panels=6)
        assert cfg.refresh_interval_seconds == 5.0


class TestDashboardCommandBasic:
    def test_empty_dashboard(self, dashboard_cmd):
        assert dashboard_cmd.panel_count == 0

    def test_add_panel(self, dashboard_cmd):
        dashboard_cmd.add_panel(
            title="System Health",
            panel_type=PanelType.STATUS,
            content="All systems operational",
        )
        assert dashboard_cmd.panel_count == 1

    def test_add_multiple_panels(self, dashboard_cmd):
        dashboard_cmd.add_panel("CPU", PanelType.METRICS, "75%")
        dashboard_cmd.add_panel("Memory", PanelType.METRICS, "4.2GB")
        dashboard_cmd.add_panel("Alerts", PanelType.ALERTS, "0 active")
        assert dashboard_cmd.panel_count == 3

    def test_remove_panel(self, dashboard_cmd):
        dashboard_cmd.add_panel("CPU", PanelType.METRICS, "75%")
        assert dashboard_cmd.remove_panel("CPU") is True
        assert dashboard_cmd.panel_count == 0

    def test_remove_panel_missing(self, dashboard_cmd):
        assert dashboard_cmd.remove_panel("nonexistent") is False

    def test_update_panel(self, dashboard_cmd):
        dashboard_cmd.add_panel("CPU", PanelType.METRICS, "75%")
        dashboard_cmd.update_panel("CPU", content="82%")
        panel = dashboard_cmd.get_panel("CPU")
        assert panel is not None
        assert panel.content == "82%"

    def test_get_panel_missing(self, dashboard_cmd):
        assert dashboard_cmd.get_panel("nonexistent") is None

    def test_render_dashboard(self, dashboard_cmd):
        dashboard_cmd.add_panel("System", PanelType.STATUS, "Healthy")
        dashboard_cmd.add_panel("Metrics", PanelType.METRICS, "CPU: 50%")
        output = dashboard_cmd.render()
        assert "System" in output
        assert "Metrics" in output

    def test_render_empty_dashboard(self, dashboard_cmd):
        output = dashboard_cmd.render()
        assert isinstance(output, str)

    def test_list_panels(self, dashboard_cmd):
        dashboard_cmd.add_panel("CPU", PanelType.METRICS, "75%")
        dashboard_cmd.add_panel("Alerts", PanelType.ALERTS, "2 active")
        panels = dashboard_cmd.list_panels()
        assert len(panels) == 2

    def test_reset(self, dashboard_cmd):
        dashboard_cmd.add_panel("CPU", PanelType.METRICS, "75%")
        dashboard_cmd.reset()
        assert dashboard_cmd.panel_count == 0


class TestPanelType:
    def test_panel_types(self):
        assert PanelType.STATUS is not None
        assert PanelType.METRICS is not None
        assert PanelType.ALERTS is not None
        assert PanelType.TRACES is not None
        assert PanelType.CUSTOM is not None
