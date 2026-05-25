"""SLA reporting: dashboard data, compliance reports, trend analysis, SLA breach post-mortems."""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

import numpy as np

from .sla_manager import SLAManager, SLAViolation, ViolationSeverity, SLIMetric
from .metrics import MetricsCollector, RollingStats

logger = logging.getLogger(__name__)


# ── Enums and data classes ──────────────────────────────────────────────


class ReportFormat(Enum):
    """Output formats for reports."""

    JSON = auto()
    HTML = auto()
    MARKDOWN = auto()
    TEXT = auto()


@dataclass
class ComplianceReport:
    """SLA compliance report for a period.

    Attributes:
        report_id: Unique identifier.
        agent_id: Agent identifier.
        period_start: Start of reporting period (Unix timestamp).
        period_end: End of reporting period.
        compliance_pct: Overall compliance percentage.
        total_checks: Total SLO evaluations.
        violations: Number of violations.
        slo_details: Per-SLO breakdown.
        recommendations: Suggested improvements.
    """

    report_id: str = ""
    agent_id: str = ""
    period_start: float = 0.0
    period_end: float = 0.0
    compliance_pct: float = 100.0
    total_checks: int = 0
    violations: int = 0
    slo_details: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class TrendAnalysis:
    """Trend analysis for SLA metrics.

    Attributes:
        agent_id: Agent identifier.
        metric: Metric name.
        trend_direction: 'improving', 'degrading', 'stable'.
        slope: Linear regression slope.
        r_squared: Goodness of fit.
        forecast_next_period: Predicted value for next period.
        confidence_interval: 95% CI for the forecast.
    """

    agent_id: str
    metric: str
    trend_direction: str = "stable"
    slope: float = 0.0
    r_squared: float = 0.0
    forecast_next_period: float = 0.0
    confidence_interval: tuple[float, float] = (0.0, 0.0)


@dataclass
class BreachPostMortem:
    """Post-mortem analysis of an SLA breach.

    Attributes:
        breach_id: Unique identifier.
        agent_id: Affected agent.
        metric: Breached metric.
        breach_time: When the breach started.
        resolution_time: When the issue was resolved.
        duration_seconds: How long the breach lasted.
        root_cause: Identified root cause.
        impact: Description of impact.
        contributing_factors: Factors that contributed.
        action_items: Recommended actions to prevent recurrence.
        severity: Worst severity during the breach.
    """

    breach_id: str = ""
    agent_id: str = ""
    metric: str = ""
    breach_time: float = 0.0
    resolution_time: float = 0.0
    duration_seconds: float = 0.0
    root_cause: str = ""
    impact: str = ""
    contributing_factors: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    severity: str = ""


# ── Dashboard data generator ───────────────────────────────────────────


class DashboardGenerator:
    """Generates structured data for SLA monitoring dashboards.

    Produces summary statistics, compliance gauges, and heatmap data
    suitable for rendering in monitoring dashboards.
    """

    def __init__(
        self,
        sla_manager: SLAManager,
        metrics_collector: MetricsCollector,
    ) -> None:
        self.sla_manager = sla_manager
        self.metrics = metrics_collector

    def generate_dashboard_data(self) -> dict[str, Any]:
        """Generate comprehensive dashboard data for all agents.

        Returns:
            Dict with panels, gauges, and alert data.
        """
        now = time.time()

        panels: list[dict[str, Any]] = []

        # Overall health panel
        health_data = self._health_panel()
        panels.append({"id": "overall_health", "type": "summary", "data": health_data})

        # Per-agent panels
        for sla in self.sla_manager.list_slas():
            agent_data = self._agent_panel(sla.agent_id)
            panels.append({"id": f"agent_{sla.agent_id}", "type": "agent_detail", "data": agent_data})

        # Budget utilization panel
        budget_data = self._budget_panel()
        panels.append({"id": "budgets", "type": "gauges", "data": budget_data})

        # Recent violations panel
        violation_data = self._violation_panel()
        panels.append({"id": "recent_violations", "type": "alerts", "data": violation_data})

        return {
            "timestamp": now,
            "panels": panels,
            "refreshed_at": now,
        }

    def _health_panel(self) -> dict[str, Any]:
        """Generate overall health summary."""
        slas = self.sla_manager.list_slas()
        total_agents = len(slas)
        if total_agents == 0:
            return {"status": "no_data", "agents": 0}

        # Count agents by health
        healthy = 0
        warning = 0
        critical = 0

        for sla in slas:
            stats = self.metrics.get_all_stats(sla.agent_id)
            error_rate = stats.get("error_rate", RollingStats()).mean
            p95_latency = stats.get("latency_p95", RollingStats()).p95

            if error_rate > 0.1 or p95_latency > 10000:
                critical += 1
            elif error_rate > 0.05 or p95_latency > 5000:
                warning += 1
            else:
                healthy += 1

        return {
            "status": "critical" if critical > 0 else ("warning" if warning > 0 else "healthy"),
            "total_agents": total_agents,
            "healthy": healthy,
            "warning": warning,
            "critical": critical,
        }

    def _agent_panel(self, agent_id: str) -> dict[str, Any]:
        """Generate dashboard data for a single agent."""
        sla = self.sla_manager.get_sla(agent_id)
        stats = self.metrics.get_all_stats(agent_id)

        return {
            "agent_id": agent_id,
            "sla_name": sla.name if sla else "",
            "metrics": {
                key: {
                    "mean": s.mean,
                    "p50": s.p50,
                    "p95": s.p95,
                    "p99": s.p99,
                }
                for key, s in stats.items()
            },
            "budgets": {
                bt.name: {
                    "limit": b.limit,
                    "consumed": b.consumed,
                    "remaining": b.remaining,
                    "utilization_pct": b.utilization_pct,
                }
                for bt, b in self.sla_manager.get_all_budgets(agent_id).items()
            },
            "violations_24h": self.sla_manager.get_violation_count(agent_id),
        }

    def _budget_panel(self) -> dict[str, Any]:
        """Generate budget utilization gauges."""
        budgets_data = {}
        for aid, budgets in self.sla_manager._budgets.items():
            budgets_data[aid] = {
                bt.name: {
                    "limit": b.limit,
                    "utilization": b.utilization_pct,
                    "status": "danger" if b.utilization_pct > 90 else ("warning" if b.utilization_pct > 70 else "ok"),
                }
                for bt, b in budgets.items()
            }
        return {"agents": budgets_data}

    def _violation_panel(self) -> dict[str, Any]:
        """Generate recent violations data."""
        recent = list(self.sla_manager._violations)[-20:]
        return {
            "recent_count": len(recent),
            "violations": [
                {
                    "agent": v.agent_id,
                    "metric": v.metric,
                    "severity": v.severity.name,
                    "actual": v.actual,
                    "target": v.slo_target,
                    "time": v.timestamp,
                }
                for v in recent
            ],
        }


# ── Compliance reporter ────────────────────────────────────────────────


class ComplianceReporter:
    """Generates compliance reports for defined periods.

    Creates detailed reports showing SLO adherence, trends,
    and actionable recommendations.
    """

    def __init__(
        self,
        sla_manager: SLAManager,
        metrics_collector: MetricsCollector,
    ) -> None:
        self.sla_manager = sla_manager
        self.metrics = metrics_collector

    def generate_report(
        self,
        agent_id: str,
        period_start: float,
        period_end: float,
    ) -> ComplianceReport:
        """Generate a compliance report for a period.

        Args:
            agent_id: Agent identifier.
            period_start: Start timestamp.
            period_end: End timestamp.

        Returns:
            Compliance report.
        """
        sla = self.sla_manager.get_sla(agent_id)
        if not sla:
            return ComplianceReport(
                report_id=f"rpt_{agent_id}_{int(period_start)}",
                agent_id=agent_id,
                period_start=period_start,
                period_end=period_end,
            )

        window = period_end - period_start
        slo_details: list[dict[str, Any]] = []
        total_checks = 0
        violations = 0
        recommendations: list[str] = []

        for slo in sla.slos:
            values = self.metrics.query(
                agent_id, slo.metric.value
            )
            # Filter to period
            timeseries = self.metrics.query_timeseries(
                agent_id, slo.metric.value
            )
            period_values = [
                v for ts, v in timeseries
                if period_start <= ts <= period_end
            ]

            if not period_values:
                continue

            total_checks += len(period_values)
            failures = sum(1 for v in period_values if not slo.evaluate(v))
            violations += failures

            slo_detail = {
                "metric": slo.metric.value,
                "target": slo.target,
                "comparator": slo.comparator,
                "checks": len(period_values),
                "failures": failures,
                "compliance_pct": (
                    (1 - failures / len(period_values)) * 100
                ),
                "avg_value": float(np.mean(period_values)),
                "p95_value": float(np.percentile(period_values, 95)),
            }
            slo_details.append(slo_detail)

            if failures > 0:
                recommendations.append(
                    f"Address {slo.metric.value} SLO: {failures}/{len(period_values)} "
                    f"checks failed (target: {slo.comparator} {slo.target})"
                )

        overall_compliance = (
            (1 - violations / total_checks) * 100 if total_checks > 0 else 100.0
        )

        return ComplianceReport(
            report_id=f"rpt_{agent_id}_{int(period_start)}",
            agent_id=agent_id,
            period_start=period_start,
            period_end=period_end,
            compliance_pct=overall_compliance,
            total_checks=total_checks,
            violations=violations,
            slo_details=slo_details,
            recommendations=recommendations,
        )

    def generate_all_reports(
        self,
        period_start: float,
        period_end: float,
    ) -> list[ComplianceReport]:
        """Generate reports for all agents."""
        return [
            self.generate_report(aid, period_start, period_end)
            for aid in self.sla_manager._slas
        ]


# ── Trend analyzer ─────────────────────────────────────────────────────


class TrendAnalyzer:
    """Analyzes trends in SLA metrics over time.

    Detects degradation patterns, seasonal effects, and provides
    forecasts with confidence intervals.
    """

    def __init__(self, metrics_collector: MetricsCollector) -> None:
        self.metrics = metrics_collector

    def analyze(
        self,
        agent_id: str,
        metric: str,
        window_seconds: float = 3600.0,
    ) -> TrendAnalysis:
        """Analyze trend for a specific metric.

        Args:
            agent_id: Agent identifier.
            metric: Metric name.
            window_seconds: Analysis window.

        Returns:
            Trend analysis with direction, slope, and forecast.
        """
        timeseries = self.metrics.query_timeseries(agent_id, metric, window_seconds)

        if len(timeseries) < 10:
            return TrendAnalysis(
                agent_id=agent_id, metric=metric,
                trend_direction="stable",
            )

        ts = np.array([t for t, _ in timeseries], dtype=np.float64)
        vals = np.array([v for _, v in timeseries], dtype=np.float64)

        # Normalize timestamps
        ts_norm = ts - ts[0]

        # Linear regression
        n = len(ts_norm)
        sum_x = np.sum(ts_norm)
        sum_y = np.sum(vals)
        sum_xy = np.sum(ts_norm * vals)
        sum_xx = np.sum(ts_norm * ts_norm)
        sum_yy = np.sum(vals * vals)

        denom = n * sum_xx - sum_x * sum_x
        if abs(denom) < 1e-10:
            slope = 0.0
            intercept = float(np.mean(vals))
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denom
            intercept = (sum_y - slope * sum_x) / n

        # R-squared
        y_mean = sum_y / n
        ss_tot = sum_yy - n * y_mean * y_mean
        ss_res = np.sum((vals - (intercept + slope * ts_norm)) ** 2)
        r_squared = 1.0 - ss_res / max(ss_tot, 1e-10)

        # Determine direction
        rel_slope = slope / max(abs(y_mean), 1e-10) * 3600  # Per-hour change
        if rel_slope > 0.05:
            direction = "degrading"  # Getting worse (higher latency, etc.)
        elif rel_slope < -0.05:
            direction = "improving"
        else:
            direction = "stable"

        # Forecast
        forecast_horizon = window_seconds * 0.2  # 20% of window
        forecast = intercept + slope * (ts_norm[-1] + forecast_horizon)

        # 95% CI
        residuals_std = np.std(vals - (intercept + slope * ts_norm))
        ci_half = 1.96 * residuals_std

        return TrendAnalysis(
            agent_id=agent_id,
            metric=metric,
            trend_direction=direction,
            slope=float(slope),
            r_squared=float(max(0, min(1, r_squared))),
            forecast_next_period=float(max(0, forecast)),
            confidence_interval=(float(max(0, forecast - ci_half)), float(forecast + ci_half)),
        )

    def analyze_all_metrics(self, agent_id: str) -> dict[str, TrendAnalysis]:
        """Analyze trends for all metrics of an agent."""
        trends = {}
        for metric_key in self.metrics._metrics.get(agent_id, {}):
            base_metric = metric_key.split("{")[0] if "{" in metric_key else metric_key
            trends[base_metric] = self.analyze(agent_id, base_metric)
        return trends


# ── Breach post-mortem generator ───────────────────────────────────────


class PostMortemGenerator:
    """Generates post-mortem analysis for SLA breaches.

    Identifies breach root causes, contributing factors, and
    recommends preventative actions.
    """

    def __init__(
        self,
        sla_manager: SLAManager,
        metrics_collector: MetricsCollector,
    ) -> None:
        self.sla_manager = sla_manager
        self.metrics = metrics_collector

    def generate_postmortem(
        self,
        violation: SLAViolation,
        preceding_seconds: float = 600.0,
    ) -> BreachPostMortem:
        """Generate a post-mortem for a specific violation.

        Args:
            violation: The violation to analyze.
            preceding_seconds: How much history before the breach to analyze.

        Returns:
            Post-mortem analysis.
        """
        breach_time = violation.timestamp

        # Get metric data before the breach
        timeseries = self.metrics.query_timeseries(
            violation.agent_id, violation.metric,
            window_seconds=preceding_seconds,
        )

        # Filter to pre-breach
        pre_breach = [(ts, v) for ts, v in timeseries if ts < breach_time]
        if pre_breach:
            pre_values = [v for _, v in pre_breach]
            pre_mean = float(np.mean(pre_values))
            pre_std = float(np.std(pre_values))
        else:
            pre_mean = 0.0
            pre_std = 0.0

        # Determine root cause heuristically
        if violation.metric.startswith("latency"):
            if pre_std > pre_mean * 0.5:
                root_cause = "High variance in latency, possible resource contention"
            else:
                root_cause = "Sustained latency increase, possible capacity issue"
        elif violation.metric == "error_rate":
            root_cause = "Elevated error rate, possible code regression or downstream failure"
        elif violation.metric == "availability":
            root_cause = "Service availability dropped, possible infrastructure issue"
        else:
            root_cause = f"Metric {violation.metric} breached SLO target"

        factors = []
        if pre_std > pre_mean * 0.3:
            factors.append("High metric variance preceding the breach")
        if len(pre_breach) < 10:
            factors.append("Limited historical data for analysis")

        breach_severity = violation.severity.name

        action_items = [
            f"Review {violation.metric} monitoring and alerting thresholds",
            f"Investigate root cause: {root_cause}",
            "Document incident timeline and impact",
        ]

        if violation.metric.startswith("latency"):
            action_items.append("Consider scaling up resources or optimizing hot paths")
        elif violation.metric == "error_rate":
            action_items.append("Review recent deployments for potential regressions")

        return BreachPostMortem(
            breach_id=f"pm_{violation.violation_id}",
            agent_id=violation.agent_id,
            metric=violation.metric,
            breach_time=breach_time,
            resolution_time=time.time(),
            duration_seconds=time.time() - breach_time,
            root_cause=root_cause,
            impact=f"Metric {violation.metric} exceeded SLO target of "
                   f"{violation.slo_target} (actual: {violation.actual:.2f})",
            contributing_factors=factors,
            action_items=action_items,
            severity=breach_severity,
        )

    def generate_all_postmortems(self) -> list[BreachPostMortem]:
        """Generate post-mortems for all recent violations."""
        violations = list(self.sla_manager._violations)[-50:]
        return [self.generate_postmortem(v) for v in violations]


# ── Report exporter ────────────────────────────────────────────────────


class ReportExporter:
    """Exports reports in various formats."""

    def __init__(self) -> None:
        self._exporters = {
            ReportFormat.JSON: self._to_json,
            ReportFormat.MARKDOWN: self._to_markdown,
            ReportFormat.TEXT: self._to_text,
        }

    def export(
        self,
        report: ComplianceReport,
        fmt: ReportFormat = ReportFormat.JSON,
    ) -> str:
        """Export a report in the specified format.

        Args:
            report: The compliance report.
            fmt: Output format.

        Returns:
            Formatted report string.
        """
        exporter = self._exporters.get(fmt, self._to_json)
        return exporter(report)

    def export_dashboard(self, data: dict[str, Any], fmt: ReportFormat = ReportFormat.JSON) -> str:
        """Export dashboard data."""
        if fmt == ReportFormat.JSON:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)

    def _to_json(self, report: ComplianceReport) -> str:
        """Format as JSON."""
        return json.dumps({
            "report_id": report.report_id,
            "agent_id": report.agent_id,
            "period": {
                "start": report.period_start,
                "end": report.period_end,
            },
            "compliance_pct": report.compliance_pct,
            "total_checks": report.total_checks,
            "violations": report.violations,
            "slo_details": report.slo_details,
            "recommendations": report.recommendations,
        }, indent=2, default=str)

    def _to_markdown(self, report: ComplianceReport) -> str:
        """Format as Markdown."""
        lines = [
            f"# SLA Compliance Report: {report.agent_id}",
            f"",
            f"**Period**: {report.period_start} - {report.period_end}",
            f"**Overall Compliance**: {report.compliance_pct:.1f}%",
            f"**Total Checks**: {report.total_checks}",
            f"**Violations**: {report.violations}",
            f"",
            f"## SLO Details",
            f"",
            f"| Metric | Target | Compliance % | Avg Value | P95 Value |",
            f"|--------|--------|-------------|-----------|-----------|",
        ]

        for slo in report.slo_details:
            lines.append(
                f"| {slo['metric']} | {slo['comparator']} {slo['target']} | "
                f"{slo['compliance_pct']:.1f}% | {slo['avg_value']:.2f} | "
                f"{slo['p95_value']:.2f} |"
            )

        if report.recommendations:
            lines.append("")
            lines.append("## Recommendations")
            for rec in report.recommendations:
                lines.append(f"- {rec}")

        return "\n".join(lines)

    def _to_text(self, report: ComplianceReport) -> str:
        """Format as plain text."""
        lines = [
            f"SLA Compliance Report: {report.agent_id}",
            f"Period: {report.period_start} - {report.period_end}",
            f"Overall Compliance: {report.compliance_pct:.1f}%",
            f"Total Checks: {report.total_checks}, Violations: {report.violations}",
            "",
        ]
        for slo in report.slo_details:
            lines.append(
                f"  {slo['metric']}: {slo['comparator']} {slo['target']} "
                f"-> {slo['compliance_pct']:.1f}% compliant (avg={slo['avg_value']:.2f})"
            )

        if report.recommendations:
            lines.append("\nRecommendations:")
            for rec in report.recommendations:
                lines.append(f"  - {rec}")

        return "\n".join(lines)
