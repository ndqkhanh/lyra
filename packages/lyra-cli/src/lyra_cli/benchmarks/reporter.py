"""Benchmark report generation — text, JSON, and markdown formats."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import StrEnum


class ReportFormat(StrEnum):
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


@dataclass(frozen=True)
class BenchmarkRunSummary:
    run_id: str
    timestamp: float
    scenario_count: int
    passed_count: int
    failed_count: int
    total_duration_sec: float
    overall_grade: str = ""


@dataclass(frozen=True)
class GradeThresholds:
    a_plus_p95_ratio: float = 0.5   # p95 < 50% of target
    a_p95_ratio: float = 0.75       # p95 < 75% of target
    b_p95_ratio: float = 1.0        # p95 < target
    c_p95_ratio: float = 1.5        # p95 < 150% of target


class BenchmarkReporter:
    """Generates formatted benchmark reports in multiple formats.

    Usage::

        reporter = BenchmarkReporter()
        report = reporter.generate(summary, results, ReportFormat.MARKDOWN)
        print(report)
    """

    def __init__(self, grade_thresholds: GradeThresholds | None = None) -> None:
        self._thresholds = grade_thresholds or GradeThresholds()

    def generate(
        self,
        summary: BenchmarkRunSummary,
        results: list[dict],
        fmt: ReportFormat = ReportFormat.TEXT,
    ) -> str:
        if fmt == ReportFormat.JSON:
            return self._generate_json(summary, results)
        if fmt == ReportFormat.MARKDOWN:
            return self._generate_markdown(summary, results)
        return self._generate_text(summary, results)

    def compute_grade(self, p95_ms: float, target_p95_ms: float) -> str:
        if target_p95_ms <= 0:
            return "N/A"
        ratio = p95_ms / target_p95_ms
        if ratio <= self._thresholds.a_plus_p95_ratio:
            return "A+"
        if ratio <= self._thresholds.a_p95_ratio:
            return "A"
        if ratio <= self._thresholds.b_p95_ratio:
            return "B"
        if ratio <= self._thresholds.c_p95_ratio:
            return "C"
        return "D"

    def compute_overall_grade(self, results: list[dict]) -> str:
        grades = []
        for r in results:
            g = self.compute_grade(
                r.get("p95_ms", float("inf")),
                r.get("target_p95_ms", 1.0),
            )
            grades.append(g)

        if not grades:
            return "N/A"

        grade_scores = {"A+": 5, "A": 4, "B": 3, "C": 2, "D": 1, "N/A": 0}
        avg_score = sum(grade_scores.get(g, 0) for g in grades) / len(grades)

        if avg_score >= 4.5:
            return "A+"
        if avg_score >= 3.75:
            return "A"
        if avg_score >= 2.75:
            return "B"
        if avg_score >= 1.75:
            return "C"
        return "D"

    def _generate_text(self, summary: BenchmarkRunSummary, results: list[dict]) -> str:
        lines = [
            "=" * 60,
            f"BENCHMARK REPORT: {summary.run_id}",
            f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(summary.timestamp))}",
            "-" * 60,
            f"Scenarios: {summary.scenario_count} total, "
            f"{summary.passed_count} passed, {summary.failed_count} failed",
            f"Duration: {summary.total_duration_sec:.1f}s",
            f"Overall Grade: {summary.overall_grade}",
            "-" * 60,
        ]
        for r in results:
            status = "PASS" if r.get("passed", True) else "FAIL"
            grade = r.get("grade", self.compute_grade(
                r.get("p95_ms", 0), r.get("target_p95_ms", 1.0),
            ))
            lines.append(
                f"  [{status}] {r['name']:<40s} "
                f"p95={r.get('p95_ms', 0):7.2f}ms  "
                f"target={r.get('target_p95_ms', 0):7.2f}ms  "
                f"grade={grade}"
            )
        lines.extend(["-" * 60, f"Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}"])
        return "\n".join(lines)

    def _generate_json(self, summary: BenchmarkRunSummary, results: list[dict]) -> str:
        return json.dumps(
            {
                "run_id": summary.run_id,
                "timestamp": summary.timestamp,
                "scenario_count": summary.scenario_count,
                "passed_count": summary.passed_count,
                "failed_count": summary.failed_count,
                "total_duration_sec": summary.total_duration_sec,
                "overall_grade": summary.overall_grade,
                "results": results,
            },
            indent=2,
        )

    def _generate_markdown(self, summary: BenchmarkRunSummary, results: list[dict]) -> str:
        lines = [
            f"# Benchmark Report: {summary.run_id}",
            "",
            f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(summary.timestamp))}",
            f"**Overall Grade:** {summary.overall_grade}",
            "",
            "| Scenario | Status | p95 (ms) | Target (ms) | Grade |",
            "|----------|--------|----------|-------------|-------|",
        ]
        for r in results:
            status = "PASS" if r.get("passed", True) else "FAIL"
            grade = r.get("grade", self.compute_grade(
                r.get("p95_ms", 0), r.get("target_p95_ms", 1.0),
            ))
            lines.append(
                f"| {r['name']} | {status} | {r.get('p95_ms', 0):.2f} | "
                f"{r.get('target_p95_ms', 0):.2f} | {grade} |"
            )
        lines.extend(["", f"*Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}*"])
        return "\n".join(lines)
