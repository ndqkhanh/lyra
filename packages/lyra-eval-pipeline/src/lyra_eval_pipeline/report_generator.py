"""Evaluation report generation and export."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from .domain_evaluator import DomainEvalReport
from .exceptions import ReportError
from .leaderboard import Leaderboard


@dataclass(frozen=True)
class ReportConfig:
    """Configuration for report generation."""

    format: str = "markdown"
    include_plots: bool = True
    include_recommendations: bool = True
    output_path: str = ""


@dataclass(frozen=True)
class EvalReport:
    """An evaluation report with leaderboard and domain breakdown."""

    title: str
    generated_at: float
    summary: str
    leaderboard: Leaderboard
    domain_breakdown: tuple[DomainEvalReport, ...]
    recommendations: tuple[str, ...]


@dataclass(frozen=True)
class ReportArtifact:
    """Generated report artifacts."""

    report: EvalReport
    markdown: str
    json_data: str
    file_paths: tuple[str, ...]


class ReportGenerator:
    """Generates evaluation reports and exports them."""

    async def generate_report(
        self,
        results: list[DomainEvalReport],
        leaderboard: Leaderboard,
        config: ReportConfig | None = None,
    ) -> EvalReport:
        """Generate a comprehensive evaluation report."""
        cfg = config or ReportConfig()

        if not results:
            raise ReportError("No domain results provided for report generation")

        # Compute summary
        total_samples = sum(len(r.results) for r in results)
        avg_pass_rate = sum(r.pass_rate for r in results) / len(results)
        avg_score = sum(r.avg_score for r in results) / len(results)

        summary = (
            f"Evaluated {total_samples} samples across {len(results)} domains. "
            f"Average pass rate: {avg_pass_rate:.1%}. "
            f"Average score: {avg_score:.3f}."
        )

        recommendations: tuple[str, ...] = ()
        if cfg.include_recommendations:
            recommendations = await self.generate_recommendations(
                EvalReport(
                    title=cfg.format,
                    generated_at=time.time(),
                    summary=summary,
                    leaderboard=leaderboard,
                    domain_breakdown=tuple(results),
                    recommendations=(),
                )
            )

        return EvalReport(
            title="Evaluation Report",
            generated_at=time.time(),
            summary=summary,
            leaderboard=leaderboard,
            domain_breakdown=tuple(results),
            recommendations=recommendations,
        )

    async def export_markdown(self, report: EvalReport, path: str = "") -> str:
        """Export a report as markdown."""
        lines: list[str] = []
        lines.append(f"# {report.title}")
        lines.append("")
        lines.append(f"*Generated at: {time.ctime(report.generated_at)}*")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append(report.summary)
        lines.append("")

        # Leaderboard
        lines.append("## Leaderboard")
        lines.append("")
        lines.append(f"Category: {report.leaderboard.category}")
        lines.append("")
        lines.append("| Rank | Name | Score | Domain | Evals |")
        lines.append("|------|------|-------|--------|-------|")
        for entry in report.leaderboard.entries:
            lines.append(
                f"| {entry.rank} | {entry.name} | {entry.score:.4f} | "
                f"{entry.domain} | {entry.num_evals} |"
            )
        lines.append("")

        # Domain breakdown
        lines.append("## Domain Breakdown")
        lines.append("")
        for dr in report.domain_breakdown:
            lines.append(f"### {dr.domain}")
            lines.append("")
            lines.append(f"- Pass Rate: {dr.pass_rate:.1%}")
            lines.append(f"- Avg Score: {dr.avg_score:.4f}")
            lines.append(f"- Avg Latency: {dr.avg_latency_ms:.2f}ms")
            lines.append(f"- Samples: {len(dr.results)}")
            lines.append("")

        # Recommendations
        if report.recommendations:
            lines.append("## Recommendations")
            lines.append("")
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        markdown = "\n".join(lines)

        if path:
            try:
                with open(path, "w") as f:
                    f.write(markdown)
            except OSError as exc:
                raise ReportError(f"Failed to write markdown to {path}: {exc}") from exc

        return markdown

    async def export_json(self, report: EvalReport, path: str = "") -> str:
        """Export a report as JSON."""
        data: dict[str, Any] = {
            "title": report.title,
            "generated_at": report.generated_at,
            "summary": report.summary,
            "leaderboard": {
                "category": report.leaderboard.category,
                "updated_at": report.leaderboard.updated_at,
                "total_entries": report.leaderboard.total_entries,
                "entries": [
                    {
                        "rank": e.rank,
                        "name": e.name,
                        "score": e.score,
                        "change": e.change,
                        "domain": e.domain,
                        "num_evals": e.num_evals,
                    }
                    for e in report.leaderboard.entries
                ],
            },
            "domain_breakdown": [
                {
                    "domain": dr.domain,
                    "pass_rate": dr.pass_rate,
                    "avg_score": dr.avg_score,
                    "avg_latency_ms": dr.avg_latency_ms,
                    "results": [
                        {
                            "sample_id": r.sample_id,
                            "domain": r.domain,
                            "metric_scores": list(r.metric_scores),
                            "overall_score": r.overall_score,
                            "passed": r.passed,
                            "latency_ms": r.latency_ms,
                        }
                        for r in dr.results
                    ],
                }
                for dr in report.domain_breakdown
            ],
            "recommendations": list(report.recommendations),
        }

        json_str = json.dumps(data, indent=2)

        if path:
            try:
                with open(path, "w") as f:
                    f.write(json_str)
            except OSError as exc:
                raise ReportError(f"Failed to write JSON to {path}: {exc}") from exc

        return json_str

    async def generate_recommendations(
        self, report: EvalReport
    ) -> tuple[str, ...]:
        """Generate recommendations based on evaluation results."""
        recommendations: list[str] = []

        for dr in report.domain_breakdown:
            if dr.pass_rate < 0.5:
                recommendations.append(
                    f"Critical: Domain '{dr.domain}' has very low pass rate "
                    f"({dr.pass_rate:.1%}). Immediate improvement needed."
                )
            elif dr.pass_rate < 0.75:
                recommendations.append(
                    f"Warning: Domain '{dr.domain}' pass rate is below target "
                    f"({dr.pass_rate:.1%}). Consider focused training."
                )

            if dr.avg_latency_ms > 500:
                recommendations.append(
                    f"Performance: Domain '{dr.domain}' has high latency "
                    f"({dr.avg_latency_ms:.0f}ms). Optimize evaluation pipeline."
                )

        # Leaderboard-based recommendations
        if report.leaderboard.entries:
            best = report.leaderboard.entries[0]
            recommendations.append(
                f"Model '{best.name}' leads with score {best.score:.4f}. "
                f"Consider it as reference for further evaluations."
            )

            if len(report.leaderboard.entries) >= 2:
                worst = report.leaderboard.entries[-1]
                if worst.score < 0.5:
                    recommendations.append(
                        f"Model '{worst.name}' scores low ({worst.score:.4f}). "
                        f"Review and retrain."
                    )

        if not recommendations:
            recommendations.append("All domains performing adequately. Continue monitoring.")

        return tuple(recommendations)
