"""Tests for lyra_otel_tracer.prometheus_export."""

from __future__ import annotations

import pytest

from lyra_otel_tracer.prometheus_export import (
    ExportConfig,
    GrafanaDashboard,
    PromMetric,
    PrometheusExporter,
)


class TestPromMetric:
    def test_prom_metric_creation(self) -> None:
        metric = PromMetric(name="test_metric", value=42.0)
        assert metric.name == "test_metric"
        assert metric.value == 42.0
        assert metric.labels == ()
        assert metric.metric_type == "gauge"

    def test_prom_metric_with_labels(self) -> None:
        labels = (("agent", "a1"), ("model", "sonnet"))
        metric = PromMetric(
            name="token_usage",
            labels=labels,
            value=1500.0,
            metric_type="counter",
            help_text="Total token usage",
        )
        assert metric.name == "token_usage"
        assert len(metric.labels) == 2
        assert metric.help_text == "Total token usage"

    def test_prom_metric_frozen(self) -> None:
        metric = PromMetric(name="m", value=1.0)
        with pytest.raises(AttributeError):
            metric.name = "changed"  # type: ignore[misc]


class TestExportConfig:
    def test_export_config_defaults(self) -> None:
        config = ExportConfig()
        assert config.port == 9090
        assert config.endpoint == "/metrics"
        assert config.push_gateway == ""
        assert config.export_interval_s == 15.0

    def test_export_config_custom(self) -> None:
        config = ExportConfig(
            port=8080,
            endpoint="/custom",
            push_gateway="http://push:9091",
            export_interval_s=30.0,
        )
        assert config.port == 8080
        assert config.push_gateway == "http://push:9091"


class TestGrafanaDashboard:
    def test_grafana_dashboard_creation(self) -> None:
        dashboard = GrafanaDashboard(
            title="Lyra OTEL Dashboard",
            panels=("Latency", "Token Usage"),
            datasource="prometheus",
        )
        assert dashboard.title == "Lyra OTEL Dashboard"
        assert len(dashboard.panels) == 2

    def test_grafana_dashboard_defaults(self) -> None:
        dashboard = GrafanaDashboard(title="Default")
        assert dashboard.panels == ()
        assert dashboard.datasource == "prometheus"


class TestPrometheusExporter:
    @pytest.mark.asyncio
    async def test_export_metrics_empty(self) -> None:
        exporter = PrometheusExporter()
        output = await exporter.export_metrics(())
        assert output == "\n"

    @pytest.mark.asyncio
    async def test_export_single_metric(self) -> None:
        exporter = PrometheusExporter()
        metrics = (PromMetric(name="test_metric", value=42.0),)
        output = await exporter.export_metrics(metrics)
        assert "# TYPE test_metric gauge" in output
        assert "test_metric 42.0" in output

    @pytest.mark.asyncio
    async def test_export_metric_with_help(self) -> None:
        exporter = PrometheusExporter()
        metrics = (
            PromMetric(
                name="token_usage",
                value=1500.0,
                help_text="Total token usage count",
            ),
        )
        output = await exporter.export_metrics(metrics)
        assert "# HELP token_usage Total token usage count" in output

    @pytest.mark.asyncio
    async def test_export_metric_with_labels(self) -> None:
        exporter = PrometheusExporter()
        labels = (("agent", "a1"), ("model", "sonnet"))
        metrics = (
            PromMetric(
                name="token_usage",
                labels=labels,
                value=1500.0,
                metric_type="counter",
            ),
        )
        output = await exporter.export_metrics(metrics)
        assert 'agent="a1"' in output
        assert 'model="sonnet"' in output
        assert '# TYPE token_usage counter' in output

    @pytest.mark.asyncio
    async def test_export_multiple_metrics(self) -> None:
        exporter = PrometheusExporter()
        metrics = (
            PromMetric(name="latency_p50", value=100.0),
            PromMetric(name="latency_p95", value=500.0),
            PromMetric(name="latency_p99", value=1000.0),
        )
        output = await exporter.export_metrics(metrics)
        assert output.count("# TYPE") == 3
        assert "latency_p50 100.0" in output

    @pytest.mark.asyncio
    async def test_export_metric_counter_type(self) -> None:
        exporter = PrometheusExporter()
        metrics = (
            PromMetric(name="requests_total", value=10.0, metric_type="counter"),
        )
        output = await exporter.export_metrics(metrics)
        assert "# TYPE requests_total counter" in output

    @pytest.mark.asyncio
    async def test_export_metric_histogram_type(self) -> None:
        exporter = PrometheusExporter()
        metrics = (
            PromMetric(name="request_duration_ms", value=200.0, metric_type="histogram"),
        )
        output = await exporter.export_metrics(metrics)
        assert "# TYPE request_duration_ms histogram" in output

    @pytest.mark.asyncio
    async def test_start_export_server(self) -> None:
        exporter = PrometheusExporter()
        config = ExportConfig()
        await exporter.start_export_server(config)
        assert exporter._export_server_running

    @pytest.mark.asyncio
    async def test_start_export_server_idempotent(self) -> None:
        exporter = PrometheusExporter()
        config = ExportConfig()
        await exporter.start_export_server(config)
        await exporter.start_export_server(config)
        assert exporter._export_server_running

    @pytest.mark.asyncio
    async def test_push_to_gateway(self) -> None:
        exporter = PrometheusExporter()
        metrics = (PromMetric(name="test_metric", value=1.0),)
        result = await exporter.push_to_gateway(metrics, "http://pushgateway:9091")
        assert result

    @pytest.mark.asyncio
    async def test_push_to_gateway_empty(self) -> None:
        exporter = PrometheusExporter()
        result = await exporter.push_to_gateway((), "http://pushgateway:9091")
        assert result  # newline is still length 1 -> True

    @pytest.mark.asyncio
    async def test_generate_grafana_dashboard(self) -> None:
        exporter = PrometheusExporter()
        dashboard = await exporter.generate_grafana_dashboard("Lyra OTEL Dashboard")
        assert dashboard.title == "Lyra OTEL Dashboard"
        assert len(dashboard.panels) > 0

    @pytest.mark.asyncio
    async def test_generate_grafana_dashboard_with_custom_title(self) -> None:
        exporter = PrometheusExporter()
        dashboard = await exporter.generate_grafana_dashboard("Custom Dashboard")
        assert dashboard.title == "Custom Dashboard"

    @pytest.mark.asyncio
    async def test_export_format_newline_terminated(self) -> None:
        exporter = PrometheusExporter()
        metrics = (PromMetric(name="m", value=1.0),)
        output = await exporter.export_metrics(metrics)
        assert output.endswith("\n")

    @pytest.mark.asyncio
    async def test_export_labels_escaping(self) -> None:
        exporter = PrometheusExporter()
        labels = (("agent", 'agent "a1"'),)  # label value with quote
        metrics = (PromMetric(name="m", labels=labels, value=1.0),)
        output = await exporter.export_metrics(metrics)
        assert 'agent="agent \\"a1\\""' in output or 'agent="agent "a1""' in output

    @pytest.mark.asyncio
    async def test_export_metric_zero_value(self) -> None:
        exporter = PrometheusExporter()
        metrics = (PromMetric(name="zero_metric", value=0.0),)
        output = await exporter.export_metrics(metrics)
        assert "zero_metric 0.0" in output

    @pytest.mark.asyncio
    async def test_export_metric_negative_value(self) -> None:
        exporter = PrometheusExporter()
        metrics = (PromMetric(name="negative_metric", value=-1.5),)
        output = await exporter.export_metrics(metrics)
        assert "negative_metric -1.5" in output
