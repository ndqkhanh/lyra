"""Tests for the ReportGenerator module."""

from __future__ import annotations

import json

import pytest
from lyra_cli.performance.report_generator import (
    ReportConfig,
    ReportFormat,
    ReportGenerator,
)


@pytest.fixture
def sample_results() -> list[dict]:
    """Fixture providing sample benchmark results."""
    return [
        {
            "name": "latency_llm_call",
            "category": "latency",
            "status": "complete",
            "regressed": False,
            "metrics": {"latency_llm_call_mean_ms": 120.0},
        },
        {
            "name": "latency_tool_call",
            "category": "latency",
            "status": "complete",
            "regressed": True,
            "metrics": {"latency_tool_call_mean_ms": 75.0},
        },
        {
            "name": "memory_context_load",
            "category": "memory",
            "status": "failed",
            "regressed": False,
            "metrics": {},
        },
    ]


@pytest.fixture
def sample_comparisons() -> list[dict]:
    """Fixture providing sample competitor comparison data."""
    return [
        {
            "dimension": "task_completion_time",
            "best_competitor": "Lyra",
            "results": [
                {"competitor": "Lyra", "value": 10.0, "unit": "s"},
                {"competitor": "Claude Code", "value": 15.0, "unit": "s"},
                {"competitor": "Hermes Agent", "value": 20.0, "unit": "s"},
            ],
        },
    ]


def test_json_format(sample_results: list[dict]) -> None:
    """JSON output should be valid parseable JSON with expected keys."""
    generator = ReportGenerator(config=ReportConfig(format=ReportFormat.JSON))
    report = generator.generate(sample_results)
    data = json.loads(report)
    assert "report" in data
    assert "benchmarks" in data
    assert "summary" in data
    assert data["report"]["title"] == "Lyra Performance Benchmark Report"


def test_json_with_comparisons(sample_results: list[dict], sample_comparisons: list[dict]) -> None:
    """JSON output should include competitor comparisons when provided."""
    generator = ReportGenerator(config=ReportConfig(format=ReportFormat.JSON))
    report = generator.generate(sample_results, sample_comparisons)
    data = json.loads(report)
    assert "competitor_comparisons" in data
    assert len(data["competitor_comparisons"]) == 1


def test_markdown_format(sample_results: list[dict]) -> None:
    """Markdown output should contain headers, table, and chart."""
    generator = ReportGenerator(
        config=ReportConfig(format=ReportFormat.MARKDOWN, include_trend_charts=True)
    )
    report = generator.generate(sample_results)
    assert "# Lyra Performance Benchmark Report" in report
    assert "## Summary" in report
    assert "## Benchmark Results" in report
    assert "| Name | Category | Status | Latency (ms) | Regressed |" in report


def test_markdown_with_comparisons(
    sample_results: list[dict], sample_comparisons: list[dict]
) -> None:
    """Markdown output should include comparison table when provided."""
    generator = ReportGenerator(config=ReportConfig(format=ReportFormat.MARKDOWN))
    report = generator.generate(sample_results, sample_comparisons)
    assert "## Competitor Comparison" in report
    assert "| Dimension | Lyra | Claude Code | Hermes Agent | Best |" in report


def test_text_format(sample_results: list[dict]) -> None:
    """Text output should contain summary and results table."""
    generator = ReportGenerator(config=ReportConfig(format=ReportFormat.TEXT))
    report = generator.generate(sample_results)
    assert "Performance Benchmark Report" in report
    assert "Summary:" in report
    assert "Benchmark Results:" in report
    assert "Latency(ms)" in report


def test_text_with_comparisons(sample_results: list[dict], sample_comparisons: list[dict]) -> None:
    """Text output should include competitor comparison when provided."""
    generator = ReportGenerator(config=ReportConfig(format=ReportFormat.TEXT))
    report = generator.generate(sample_results, sample_comparisons)
    assert "Competitor Comparison:" in report
    assert "Best:" in report


def test_ascii_chart_in_markdown(sample_results: list[dict]) -> None:
    """ASCII bar chart should be included when trend charts enabled."""
    generator = ReportGenerator(
        config=ReportConfig(format=ReportFormat.MARKDOWN, include_trend_charts=True)
    )
    report = generator.generate(sample_results)
    assert "## Latency Comparison (ASCII Chart)" in report
    assert "```" in report
    assert "ms" in report


def test_empty_results() -> None:
    """Generator should handle empty results gracefully."""
    generator = ReportGenerator(config=ReportConfig(format=ReportFormat.JSON))
    report = generator.generate([])
    data = json.loads(report)
    assert data["summary"]["total"] == 0


def test_config_defaults() -> None:
    """ReportConfig should use sensible defaults."""
    config = ReportConfig()
    assert config.title == "Lyra Performance Benchmark Report"
    assert config.format == ReportFormat.MARKDOWN
    assert config.include_trend_charts
    assert config.include_comparison_tables
    assert config.max_rows == 20
