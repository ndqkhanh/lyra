"""
Research Quality Evaluation system.

Provides 6-axis quality metrics, trend tracking, and self-evaluation
for completed research sessions. All evaluation is rule/heuristic-based
— no LLM calls.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from lyra_research.orchestrator import ResearchProgress


# ---------------------------------------------------------------------------
# ResearchQualityMetrics
# ---------------------------------------------------------------------------

@dataclass
class ResearchQualityMetrics:
    """6-axis quality evaluation of a research session.

    Based on DeepResearch-ReportEval, ResearcherBench, and FML-bench.
    """

    session_id: str
    topic: str

    # Axis 1: Coverage (checklist_answered / checklist_total)
    coverage_score: float = 0.0       # Target: >= 0.85
    coverage_detail: str = ""

    # Axis 2: Citation Fidelity (verified_citations / total_claims)
    citation_fidelity: float = 0.0    # Target: 1.00 (hard gate)
    citation_detail: str = ""

    # Axis 3: Source Breadth (unique_sources / sources_found)
    source_breadth: float = 0.0       # Target: >= 0.60
    breadth_detail: str = ""

    # Axis 4: Insight Depth (heuristic from report sections)
    insight_depth: float = 0.0        # Target: >= 0.75
    depth_detail: str = ""

    # Axis 5: Gap Detection (gaps_found / gaps_expected)
    gap_detection: float = 0.0        # Target: >= 0.60
    gap_detail: str = ""

    # Axis 6: Contradiction Coverage (contested_flagged / total_claims heuristic)
    contradiction_coverage: float = 0.0  # Target: >= 0.50
    contradiction_detail: str = ""

    # Overall (weighted)
    overall_score: float = 0.0
    passed: bool = False
    issues: List[str] = field(default_factory=list)
    measured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Weights
    WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        "coverage": 0.25,
        "citation": 0.30,     # Highest: no hallucinations
        "breadth": 0.15,
        "depth": 0.15,
        "gap": 0.10,
        "contradiction": 0.05,
    })

    def compute_overall(self) -> float:
        """Compute weighted overall score."""
        w = self.WEIGHTS
        return (
            w["coverage"] * self.coverage_score
            + w["citation"] * self.citation_fidelity
            + w["breadth"] * self.source_breadth
            + w["depth"] * self.insight_depth
            + w["gap"] * self.gap_detection
            + w["contradiction"] * self.contradiction_coverage
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON persistence."""
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "coverage_score": self.coverage_score,
            "coverage_detail": self.coverage_detail,
            "citation_fidelity": self.citation_fidelity,
            "citation_detail": self.citation_detail,
            "source_breadth": self.source_breadth,
            "breadth_detail": self.breadth_detail,
            "insight_depth": self.insight_depth,
            "depth_detail": self.depth_detail,
            "gap_detection": self.gap_detection,
            "gap_detail": self.gap_detail,
            "contradiction_coverage": self.contradiction_coverage,
            "contradiction_detail": self.contradiction_detail,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "issues": self.issues,
            "measured_at": self.measured_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# ResearchQualityEvaluator
# ---------------------------------------------------------------------------

class ResearchQualityEvaluator:
    """Computes ResearchQualityMetrics from a completed research session.

    All evaluation is rule-based — no LLM calls.
    """

    # Hard gates
    MIN_CITATION_FIDELITY = 1.0
    MIN_COVERAGE = 0.75

    def evaluate(
        self,
        progress: ResearchProgress,
        checklist_total: int = 10,
        checklist_answered: int = 0,
        sources_found: int = 0,
        gaps_expected: int = 3,
    ) -> ResearchQualityMetrics:
        """Compute all 6 quality axes from a completed research progress."""
        report = progress.report
        metrics = ResearchQualityMetrics(
            session_id=progress.session_id,
            topic=progress.topic,
        )

        # Axis 1: Coverage
        metrics.coverage_score = checklist_answered / max(checklist_total, 1)
        metrics.coverage_detail = (
            f"{checklist_answered}/{checklist_total} checklist items answered"
        )

        # Axis 2: Citation Fidelity (from report if available)
        if report is not None:
            metrics.citation_fidelity = report.citation_fidelity
            metrics.citation_detail = f"Fidelity: {report.citation_fidelity:.0%}"
        else:
            metrics.citation_fidelity = 0.0
            metrics.citation_detail = "No report generated"

        # Axis 3: Source Breadth
        papers = progress.papers_analyzed
        repos = progress.repos_analyzed
        used = papers + repos
        metrics.source_breadth = min(used / max(sources_found, 1), 1.0)
        metrics.breadth_detail = f"{used} of {sources_found} sources used"

        # Axis 4: Insight Depth (heuristic: report has tables + gaps + next steps)
        metrics.insight_depth = self._score_insight_depth(report)
        metrics.depth_detail = f"Depth score: {metrics.insight_depth:.2f}"

        # Axis 5: Gap Detection
        metrics.gap_detection = min(
            progress.gaps_found / max(gaps_expected, 1), 1.0
        )
        metrics.gap_detail = (
            f"{progress.gaps_found} gaps found (expected >= {gaps_expected})"
        )

        # Axis 6: Contradiction Coverage (heuristic: has contested_claims_section)
        if report is not None and report.contested_claims_section:
            metrics.contradiction_coverage = 0.8
            metrics.contradiction_detail = "Contested claims section present"
        else:
            metrics.contradiction_coverage = 0.0
            metrics.contradiction_detail = "No contested claims documented"

        # Overall
        metrics.overall_score = metrics.compute_overall()

        # Gates
        issues: List[str] = []
        if metrics.citation_fidelity < self.MIN_CITATION_FIDELITY:
            issues.append(
                f"Citation fidelity {metrics.citation_fidelity:.0%} below required 100%"
            )
        if metrics.coverage_score < self.MIN_COVERAGE:
            issues.append(
                f"Coverage {metrics.coverage_score:.0%} below required 75%"
            )
        if metrics.gap_detection < 0.6:
            issues.append(
                f"Gap detection {metrics.gap_detection:.0%} below target 60%"
            )

        metrics.issues = issues
        metrics.passed = len([i for i in issues if "required" in i]) == 0
        return metrics

    def _score_insight_depth(self, report: Optional[Any]) -> float:
        """Heuristic: report sections that indicate depth."""
        if report is None:
            return 0.0
        score = 0.0
        if report.taxonomy_section:
            score += 0.25
        # Has table if best_papers_section contains a pipe character
        if report.best_papers_section and "|" in report.best_papers_section:
            score += 0.25
        if report.gaps_section:
            score += 0.25
        if report.next_steps_section:
            score += 0.25
        return score

    def is_deliverable(self, metrics: ResearchQualityMetrics) -> bool:
        """True if report passes all hard gates."""
        return (
            metrics.citation_fidelity >= self.MIN_CITATION_FIDELITY
            and metrics.coverage_score >= self.MIN_COVERAGE
        )


# ---------------------------------------------------------------------------
# QualityTrendTracker
# ---------------------------------------------------------------------------

class QualityTrendTracker:
    """Tracks ResearchQualityMetrics across sessions and measures improvement.

    Persistence: JSON at ~/.lyra/quality_trends.json
    """

    def __init__(self, store_path: Optional[Path] = None) -> None:
        self.store_path = store_path or Path.home() / ".lyra" / "quality_trends.json"
        self._records: List[Dict[str, Any]] = []
        self._load()

    def record(self, metrics: ResearchQualityMetrics) -> None:
        """Save a quality measurement."""
        self._records.append(metrics.to_dict())
        self._save()

    def get_trend(self, axis: str = "overall_score", last_n: int = 10) -> List[float]:
        """Get the last N values for a quality axis.

        Args:
            axis: One of: "overall_score", "coverage_score", "citation_fidelity",
                  "source_breadth", "insight_depth", "gap_detection"
        """
        values = [r.get(axis, 0.0) for r in self._records]
        return values[-last_n:]

    def is_improving(self, axis: str = "overall_score", window: int = 3) -> bool:
        """True if the last `window` values trend upward."""
        trend = self.get_trend(axis, last_n=window)
        if len(trend) < 2:
            return False
        return trend[-1] > trend[0]

    def average(self, axis: str = "overall_score") -> float:
        """Average value for an axis across all recorded sessions."""
        vals = [r.get(axis, 0.0) for r in self._records]
        return sum(vals) / len(vals) if vals else 0.0

    def summary(self) -> Dict[str, Any]:
        """Return a summary dict of averages and trends for all axes."""
        axes = [
            "overall_score",
            "coverage_score",
            "citation_fidelity",
            "source_breadth",
            "insight_depth",
            "gap_detection",
        ]
        return {
            "total_sessions": len(self._records),
            "averages": {ax: round(self.average(ax), 3) for ax in axes},
            "improving": {ax: self.is_improving(ax) for ax in axes},
        }

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps(self._records, default=str))

    def _load(self) -> None:
        if self.store_path.exists():
            try:
                self._records = json.loads(self.store_path.read_text())
            except Exception:
                self._records = []


# ---------------------------------------------------------------------------
# SelfEvaluationAgent
# ---------------------------------------------------------------------------

class SelfEvaluationAgent:
    """Automatically evaluates a research session after completion.

    Called by ResearchOrchestrator after step 9 (Report).
    Stores results to QualityTrendTracker.
    """

    def __init__(self, trend_tracker: Optional[QualityTrendTracker] = None) -> None:
        self.evaluator = ResearchQualityEvaluator()
        self.tracker = trend_tracker or QualityTrendTracker()

    def evaluate_and_track(
        self,
        progress: ResearchProgress,
        checklist_total: int = 10,
        checklist_answered: int = 0,
        sources_found: int = 0,
    ) -> ResearchQualityMetrics:
        """Evaluate quality and persist to trend tracker. Returns metrics."""
        metrics = self.evaluator.evaluate(
            progress=progress,
            checklist_total=checklist_total,
            checklist_answered=checklist_answered,
            sources_found=sources_found,
        )
        self.tracker.record(metrics)
        return metrics

    def format_report(self, metrics: ResearchQualityMetrics) -> str:
        """Format quality metrics as a readable string for output."""
        lines = [
            "\nResearch Quality Report",
            "-" * 40,
            f"Coverage:         {metrics.coverage_score:>6.0%}  "
            f"{'OK' if metrics.coverage_score >= 0.75 else 'LOW'}",
            f"Citation Fidelity:{metrics.citation_fidelity:>6.0%}  "
            f"{'OK' if metrics.citation_fidelity >= 1.0 else 'LOW'}",
            f"Source Breadth:   {metrics.source_breadth:>6.0%}",
            f"Insight Depth:    {metrics.insight_depth:>6.0%}",
            f"Gap Detection:    {metrics.gap_detection:>6.0%}",
            f"Contradiction:    {metrics.contradiction_coverage:>6.0%}",
            "-" * 40,
            f"Overall:          {metrics.overall_score:>6.0%}  "
            f"{'PASS' if metrics.passed else 'FAIL'}",
        ]
        if metrics.issues:
            lines.append("\nIssues:")
            for issue in metrics.issues:
                lines.append(f"  - {issue}")
        return "\n".join(lines)
