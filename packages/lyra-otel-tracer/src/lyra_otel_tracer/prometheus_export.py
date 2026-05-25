"""Export metrics in Prometheus-compatible format."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class PromMetric:
    """A single Prometheus metric."""

    name: str
    labels: Tuple[Tuple[str, str], ...] = ()
    value: float = 0.0
    metric_type: str = "gauge"
    help_text: str = ""


@dataclass(frozen=True)
class ExportConfig:
    """Configuration for Prometheus export."""

    port: int = 9090
    endpoint: str = "/metrics"
    push_gateway: str = ""
    export_interval_s: float = 15.0


@dataclass(frozen=True)
class GrafanaDashboard:
    """A generated Grafana dashboard definition."""

    title: str
    panels: Tuple[str, ...] = ()
    datasource: str = "prometheus"


class PrometheusExporter:
    """Exports metrics in Prometheus text format and generates Grafana dashboards."""

    def __init__(self) -> None:
        self._export_server_running: bool = False

    async def export_metrics(self, metrics: Tuple[PromMetric, ...]) -> str:
        """Format metrics as Prometheus exposition format text."""
        lines: List[str] = []

        for metric in metrics:
            # HELP line
            if metric.help_text:
                lines.append(f"# HELP {metric.name} {metric.help_text}")

            # TYPE line
            lines.append(f"# TYPE {metric.name} {metric.metric_type}")

            # Metric line with labels
            if metric.labels:
                label_str = ",".join(
                    f'{k}="{v}"' for k, v in metric.labels
                )
                lines.append(f'{metric.name}{{{label_str}}} {metric.value}')
            else:
                lines.append(f"{metric.name} {metric.value}")

        return "\n".join(lines) + "\n"

    async def start_export_server(self, _config: ExportConfig) -> None:
        """Register export configuration (actual HTTP server would require aiohttp)."""
        if self._export_server_running:
            return
        self._export_server_running = True

    async def push_to_gateway(
        self,
        metrics: Tuple[PromMetric, ...],
        _gateway_url: str,
    ) -> bool:
        """Push metrics to a Prometheus Pushgateway (simulated)."""
        formatted = await self.export_metrics(metrics)
        # In a real implementation this would POST to the gateway URL
        return len(formatted) > 0

    async def generate_grafana_dashboard(
        self,
        title: str,
    ) -> GrafanaDashboard:
        """Generate a Grafana dashboard configuration based on available metrics."""
        panels = (
            "Latency (p50/p95/p99)",
            "Token Usage by Agent",
            "Token Usage by Model",
            "Cost Breakdown by Agent",
            "Cost Breakdown by Model",
            "Hallucination Risk Score",
            "Drift Score by Metric",
            "Active Spans",
        )

        return GrafanaDashboard(
            title=title,
            panels=panels,
            datasource="prometheus",
        )
