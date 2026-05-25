"""Dashboard — plain-text dashboard that integrates tracer and metrics.

Provides a Dashboard class that renders observability data as a
simple text layout with auto-populated panels from the tracer and
metrics collector.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DashboardPanel:
    """A single panel on the dashboard.

    Attributes:
        title: Panel heading.
        content: Plain-text content body.
        updated_at: Unix timestamp of the last update.
    """

    title: str
    content: str
    updated_at: float


class Dashboard:
    """Plain-text dashboard that auto-populates from tracer and metrics.

    Args:
        tracer: Optional Tracer instance to pull span data from.
        metrics: Optional MetricsCollector instance to pull metrics from.
    """

    def __init__(
        self,
        tracer: Any | None = None,
        metrics: Any | None = None,
    ) -> None:
        self._tracer = tracer
        self._metrics = metrics
        self._panels: dict[str, DashboardPanel] = {}

    def add_panel(self, title: str, content: str) -> None:
        """Add or update a dashboard panel.

        Args:
            title: Panel heading (used as the panel identifier).
            content: Plain-text content body.
        """
        self._panels[title] = DashboardPanel(
            title=title,
            content=content,
            updated_at=time.time(),
        )

    async def refresh(self) -> None:
        """Re-populate panels from the tracer and metrics collector."""
        self._populate_tracer_panels()
        self._populate_metrics_panels()

    def _populate_tracer_panels(self) -> None:
        """Pull data from the attached Tracer, if available."""
        if self._tracer is None:
            return

        stats = self._tracer.get_stats()
        self.add_panel(
            "Tracer Stats",
            f"Total Spans: {stats['total_spans']}\n"
            f"Errors: {stats['error_count']}\n"
            f"Avg Duration: {stats['avg_duration']:.3f}s",
        )

        recent = self._tracer.get_recent_spans(5)
        if recent:
            lines: list[str] = []
            for s in recent:
                dur = f"{s.duration:.3f}s" if s.duration else "N/A"
                err = f" [ERROR: {s.error}]" if s.error else ""
                lines.append(f"  {s.name} ({dur}){err}")
            self.add_panel("Recent Spans", "\n".join(lines))
        else:
            self.add_panel("Recent Spans", "  (no spans recorded)")

    def _populate_metrics_panels(self) -> None:
        """Pull data from the attached MetricsCollector, if available."""
        if self._metrics is None:
            return

        from lyra_observability.metrics import MetricType

        all_metrics = self._metrics.get_all_metrics()

        counter_lines: list[str] = []
        gauge_lines: list[str] = []
        histogram_lines: list[str] = []

        for name, values in all_metrics.items():
            for mv in values:
                label_str = (
                    f"{{{', '.join(f'{k}={v}' for k, v in sorted(mv.labels))}}}"
                    if mv.labels
                    else ""
                )
                if mv.type == MetricType.COUNTER:
                    total = self._metrics.get_counter(name, dict(mv.labels) if mv.labels else None)
                    counter_lines.append(f"  {name}{label_str}: {total}")
                elif mv.type == MetricType.GAUGE:
                    val = self._metrics.get_gauge(name, dict(mv.labels) if mv.labels else None)
                    gauge_lines.append(f"  {name}{label_str}: {val}")
                elif mv.type == MetricType.HISTOGRAM:
                    stats = self._metrics.get_histogram_stats(
                        name, dict(mv.labels) if mv.labels else None
                    )
                    histogram_lines.append(
                        f"  {name}{label_str}: count={stats['count']} "
                        f"avg={stats['avg']:.2f} p99={stats['p99']:.2f}"
                    )

        if counter_lines:
            self.add_panel("Counters", "\n".join(counter_lines))
        if gauge_lines:
            self.add_panel("Gauges", "\n".join(gauge_lines))
        if histogram_lines:
            self.add_panel("Histograms", "\n".join(histogram_lines))

    def render(self) -> str:
        """Render the dashboard as a plain-text string.

        Returns:
            A formatted text representation of all panels.
        """
        if not self._panels:
            return "[Dashboard: No panels]"

        lines = [
            "=" * 60,
            "  LYRA OBSERVABILITY DASHBOARD",
            "=" * 60,
            "",
        ]
        for title in sorted(self._panels):
            panel = self._panels[title]
            lines.append(f"--- {title} ---")
            lines.append(panel.content)
            lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    def get_snapshot(self) -> dict[str, dict[str, Any]]:
        """Return a snapshot of all panels with timestamps.

        Returns:
            Dict mapping panel titles to dicts with ``title``, ``content``,
            and ``updated_at`` keys.
        """
        return {
            title: {
                "title": panel.title,
                "content": panel.content,
                "updated_at": panel.updated_at,
            }
            for title, panel in self._panels.items()
        }
