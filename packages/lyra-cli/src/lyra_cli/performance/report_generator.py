"""Report generator for Lyra performance benchmarking.

Provides ReportGenerator that produces performance reports in text,
JSON, and markdown formats, with comparison tables and ASCII charts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class ReportFormat(Enum):
    """Output format for performance reports."""

    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    title: str = "Lyra Performance Benchmark Report"
    format: ReportFormat = ReportFormat.MARKDOWN
    include_trend_charts: bool = True
    include_comparison_tables: bool = True
    detailed: bool = False
    max_rows: int = 20


class ReportGenerator:
    """Generates performance reports in multiple formats.

    Supports text, JSON, and markdown output with comparison tables
    and ASCII trend charts.
    """

    def __init__(self, config: ReportConfig | None = None) -> None:
        """Initialize generator with report configuration.

        Args:
            config: Report configuration. Uses defaults if None.
        """
        self.config = config or ReportConfig()

    def generate(
        self,
        benchmark_results: list[dict[str, Any]],
        competitor_comparisons: list[dict[str, Any]] | None = None,
    ) -> str:
        """Generate a report in the configured format.

        Args:
            benchmark_results: List of benchmark result dicts.
            competitor_comparisons: Optional competitor comparison data.

        Returns:
            Report string in the configured format.
        """
        if self.config.format == ReportFormat.JSON:
            return self._generate_json(benchmark_results, competitor_comparisons)
        if self.config.format == ReportFormat.MARKDOWN:
            return self._generate_markdown(benchmark_results, competitor_comparisons)
        return self._generate_text(benchmark_results, competitor_comparisons)

    def _generate_json(
        self,
        benchmark_results: list[dict[str, Any]],
        competitor_comparisons: list[dict[str, Any]] | None,
    ) -> str:
        """Generate a JSON report.

        Args:
            benchmark_results: Benchmark result data.
            competitor_comparisons: Optional competitor data.

        Returns:
            JSON string.
        """
        data: dict[str, Any] = {
            "report": {
                "title": self.config.title,
                "generated_at": datetime.now().isoformat(),
            },
            "benchmarks": benchmark_results,
        }
        if competitor_comparisons:
            data["competitor_comparisons"] = competitor_comparisons

        data["summary"] = self._compute_summary(benchmark_results)

        return json.dumps(data, indent=2)

    def _compute_summary(
        self, results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Compute summary statistics from results.

        Args:
            results: Benchmark result dicts.

        Returns:
            Summary statistics dict.
        """
        if not results:
            return {"total": 0, "passed": 0, "failed": 0}

        total = len(results)
        passed = sum(
            1 for r in results if r.get("status") == "complete" and not r.get("regressed", False)
        )
        failed = sum(1 for r in results if r.get("status") == "failed")

        latencies = [
            r.get("metrics", {}).get(f"{r.get('name', '')}_mean_ms", 0)
            for r in results
            if r.get("metrics")
        ]

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "timestamp": datetime.now().isoformat(),
        }

    def _generate_markdown(
        self,
        benchmark_results: list[dict[str, Any]],
        competitor_comparisons: list[dict[str, Any]] | None,
    ) -> str:
        """Generate a markdown report.

        Args:
            benchmark_results: Benchmark result data.
            competitor_comparisons: Optional competitor data.

        Returns:
            Markdown string.
        """
        lines: list[str] = [
            f"# {self.config.title}",
            "",
            f"_Generated: {datetime.now().isoformat()}_",
            "",
            "## Summary",
            "",
        ]

        summary = self._compute_summary(benchmark_results)
        lines.append(f"- **Total Benchmarks**: {summary['total']}")
        lines.append(f"- **Passed**: {summary['passed']}")
        lines.append(f"- **Failed**: {summary['failed']}")
        lines.append(f"- **Avg Latency**: {summary['avg_latency_ms']:.2f} ms")
        lines.append("")

        if self.config.include_comparison_tables and benchmark_results:
            lines.extend(self._markdown_results_table(benchmark_results))

        if competitor_comparisons and self.config.include_comparison_tables:
            lines.extend(self._markdown_comparison_table(competitor_comparisons))

        if self.config.include_trend_charts and benchmark_results:
            lines.extend(self._ascii_trend_chart(benchmark_results))

        return "\n".join(lines)

    def _markdown_results_table(
        self, results: list[dict[str, Any]]
    ) -> list[str]:
        """Generate a markdown table for benchmark results.

        Args:
            results: Benchmark result dicts.

        Returns:
            Markdown table lines.
        """
        lines: list[str] = [
            "## Benchmark Results",
            "",
            "| Name | Category | Status | Latency (ms) | Regressed |",
            "|------|----------|--------|-------------|-----------|",
        ]

        for r in results[: self.config.max_rows]:
            name = r.get("name", "unknown")
            category = r.get("category", "unknown")
            status = r.get("status", "unknown")
            metrics = r.get("metrics", {})
            latency = metrics.get(f"{name}_mean_ms", metrics.get("value", 0))
            regressed = "Yes" if r.get("regressed") else "No"

            lines.append(
                f"| {name} | {category} | {status} | {latency:.2f} | {regressed} |"
            )

        lines.append("")
        return lines

    def _markdown_comparison_table(
        self, comparisons: list[dict[str, Any]]
    ) -> list[str]:
        """Generate a markdown table for competitor comparisons.

        Args:
            comparisons: Competitor comparison data.

        Returns:
            Markdown table lines.
        """
        lines: list[str] = [
            "## Competitor Comparison",
            "",
            "| Dimension | Lyra | Claude Code | Hermes Agent | Best |",
            "|-----------|------|-------------|--------------|------|",
        ]

        for comp in comparisons:
            dim = comp.get("dimension", "unknown")
            results = comp.get("results", [])
            lyra = _find_value(results, "Lyra")
            claude = _find_value(results, "Claude Code")
            hermes = _find_value(results, "Hermes Agent")
            best_name = comp.get("best_competitor", "-")

            def _fmt(v: float | None) -> str:
                return f"{v:.2f}" if v is not None else "N/A"

            lines.append(
                f"| {dim} | {_fmt(lyra)} | {_fmt(claude)} | "
                f"{_fmt(hermes)} | {best_name} |"
            )

        lines.append("")
        return lines

    def _ascii_trend_chart(
        self, results: list[dict[str, Any]]
    ) -> list[str]:
        """Generate an ASCII bar chart for benchmark latencies.

        Args:
            results: Benchmark result dicts.

        Returns:
            ASCII chart lines.
        """
        lines: list[str] = [
            "## Latency Comparison (ASCII Chart)",
            "",
            "```",
        ]

        entries: list[tuple[str, float]] = []
        for r in results:
            name = r.get("name", "unknown")
            metrics = r.get("metrics", {})
            latency = metrics.get(f"{name}_mean_ms", metrics.get("value", 0))
            if latency > 0:
                entries.append((name, latency))

        if not entries:
            lines.append("(no latency data)")
            lines.append("```")
            lines.append("")
            return lines

        max_val = max(v for _, v in entries)
        if max_val == 0:
            max_val = 1

        bar_max = 40
        for name, value in entries:
            bar_len = max(1, int((value / max_val) * bar_max))
            bar = "█" * bar_len
            lines.append(f"  {name:30s} {bar} {value:.1f}ms")

        lines.append("```")
        lines.append("")
        return lines

    def _generate_text(
        self, benchmark_results: list[dict[str, Any]],
        competitor_comparisons: list[dict[str, Any]] | None,
    ) -> str:
        """Generate a plain text report."""
        lines: list[str] = [
            "=" * 70,
            f"  {self.config.title}",
            "=" * 70,
            f"  Generated: {datetime.now().isoformat()}",
            "",
        ]
        summary = self._compute_summary(benchmark_results)
        lines.extend([
            "  Summary:",
            f"    Total: {summary['total']}",
            f"    Passed: {summary['passed']}",
            f"    Failed: {summary['failed']}",
            f"    Avg Latency: {summary['avg_latency_ms']:.2f} ms",
            "",
        ])
        if benchmark_results:
            lines.append("  Benchmark Results:")
            lines.append(f"    {'Name':30s} {'Category':20s} {'Status':12s} {'Latency(ms)':12s}")
            lines.append(f"    {'-'*30} {'-'*20} {'-'*12} {'-'*12}")
            for r in benchmark_results[: self.config.max_rows]:
                n = r.get("name", "unknown")
                m = r.get("metrics", {})
                lat = m.get(f"{n}_mean_ms", m.get("value", 0))
                lines.append(f"    {n:30s} {r.get('category', ''):20s} {r.get('status', ''):12s} {lat:<12.2f}")
            lines.append("")
        if competitor_comparisons:
            lines.append("  Competitor Comparison:\n")
            for comp in competitor_comparisons:
                dim = comp.get("dimension", "unknown")
                lines.append(f"    {dim}:")
                for r in comp.get("results", []):
                    lines.append(f"      {r.get('competitor', ''):20s} {r.get('value', 0):.2f} {r.get('unit', '')}")
                lines.append(f"      {'Best:':20s} {comp.get('best_competitor', '-')}\n")
        lines.append("=" * 70)
        return "\n".join(lines)


def _find_value(
    results: list[dict[str, Any]], competitor_name: str
) -> float | None:
    """Find a competitor's result value by name.

    Args:
        results: List of competitor result dicts.
        competitor_name: Name to search for.

    Returns:
        Value if found, else None.
    """
    for r in results:
        if r.get("competitor") == competitor_name:
            return r.get("value")
    return None
