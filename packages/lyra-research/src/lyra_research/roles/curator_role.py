"""Curator Role — Curates knowledge for persistent storage.

Quality control for knowledge acceptance:
- Validates report quality (from review)
- Decides accept/reject for knowledge base
- Versions knowledge entries
- Manages knowledge lifecycle
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from lyra_core.context.layered_context import LayeredContextManager
from lyra_research.curation.curation_workflow import CurationWorkflow, DecisionType
from lyra_research.curation.curator_metrics import CuratorMetrics
from lyra_research.curation.knowledge_entry import (
    EntryStatus,
    KnowledgeEntry as CurationKnowledgeEntry,
)
from lyra_research.curation.knowledge_store import KnowledgeStore
from lyra_research.curation.knowledge_versioning import VersionManager
from lyra_research.roles.role_base import Role, RoleResult, RoleStatus
from lyra_research.roles.review_role import ReviewResult
from lyra_research.reporter import ResearchReport


@dataclass
class KnowledgeEntry:
    """Single knowledge entry for curation (legacy compatibility)."""

    entry_id: str
    report: ResearchReport
    review: ReviewResult
    version: int
    accepted: bool
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CurationResult(RoleResult):
    """Result from curator role."""

    accepted: bool = False
    knowledge_entry: KnowledgeEntry | None = None
    rejection_reason: str | None = None
    quality_gate_passed: bool = False


class CuratorRole(Role[CurationResult]):
    """
    Curator Role — Curates knowledge for persistent storage.

    Model: claude-opus-4-7 (deepest reasoning for quality control)
    """

    # Quality gates
    MIN_QUALITY_SCORE = 0.7
    MIN_SOURCES_ANALYZED = 5
    MAX_CRITICAL_ISSUES = 0
    MAX_HIGH_ISSUES = 2

    def __init__(
        self,
        context_manager: LayeredContextManager,
        storage_path: Path | None = None,
    ) -> None:
        """
        Initialize curator role.

        Args:
            context_manager: Layered context manager
            storage_path: Path to knowledge store (default: .lyra/knowledge)
        """
        super().__init__("Curator", "claude-opus-4-7", context_manager)
        self.version_counter = 1

        # Initialize curation components
        self.workflow = CurationWorkflow(quality_threshold=self.MIN_QUALITY_SCORE)
        self.version_manager = VersionManager()
        self.metrics = CuratorMetrics()

        # Initialize knowledge store
        if storage_path is None:
            storage_path = Path.cwd() / ".lyra" / "knowledge"
        self.knowledge_store = KnowledgeStore(storage_path)

    async def execute(
        self, report: ResearchReport, review: ReviewResult
    ) -> CurationResult:
        """
        Execute curation decision.

        Args:
            report: Research report
            review: Review result

        Returns:
            CurationResult with accept/reject decision
        """
        result = CurationResult(
            role_name=self.name,
            status=RoleStatus.RUNNING,
            data=None,
        )

        try:
            # Quality gate checks
            quality_checks = self._run_quality_gates(report, review)

            # Decision: accept or reject
            accepted = all(quality_checks.values())

            if accepted:
                # Create curation knowledge entry
                curation_entry = CurationKnowledgeEntry(
                    content=report.executive_summary,
                    source=report.topic,
                    quality_score=review.overall_quality_score,
                    category="research",
                    tags=[report.topic] + (getattr(report, "metadata", {}).get("tags", [])),
                    status=EntryStatus.PENDING,
                )

                # Review with workflow
                decision = self.workflow.review(curation_entry)

                # Apply decision
                if decision.decision_type == DecisionType.APPROVE:
                    approved_entry = self.workflow.approve(curation_entry)

                    # Create version
                    self.version_manager.create_version(
                        approved_entry,
                        changed_by="curator_role",
                        reason="Initial approval",
                    )

                    # Store in knowledge store
                    self.knowledge_store.store(approved_entry)

                    # Record metrics
                    self.metrics.record_decision(decision, review.overall_quality_score)

                    # Create legacy knowledge entry
                    entry = KnowledgeEntry(
                        entry_id=approved_entry.id,
                        report=report,
                        review=review,
                        version=approved_entry.version,
                        accepted=True,
                        created_at=approved_entry.created_at,
                        metadata={
                            "quality_score": review.overall_quality_score,
                            "sources_used": report.sources_used,
                            "quality_checks": quality_checks,
                            "curation_entry_id": approved_entry.id,
                        },
                    )

                    result.accepted = True
                    result.knowledge_entry = entry
                    result.quality_gate_passed = True
                    result.data = entry

                else:
                    # Rejection or revision request
                    rejection_reason = decision.reason
                    if decision.feedback:
                        rejection_reason += f" - {decision.feedback}"

                    result.accepted = False
                    result.rejection_reason = rejection_reason
                    result.quality_gate_passed = False
                    result.data = None

                    # Record metrics
                    self.metrics.record_decision(decision, review.overall_quality_score)

            else:
                # Rejection with reason
                failed_checks = [k for k, v in quality_checks.items() if not v]
                rejection_reason = f"Failed quality gates: {', '.join(failed_checks)}"

                result.accepted = False
                result.rejection_reason = rejection_reason
                result.quality_gate_passed = False
                result.data = None

            result.metadata = {
                "accepted": accepted,
                "quality_checks": quality_checks,
                "quality_score": review.overall_quality_score,
                "curator_metrics": self.metrics.get_metrics(),
            }

            # Set final status
            result.status = RoleStatus.SUCCESS

            return result

        except Exception as e:
            result.status = RoleStatus.FAILED
            result.error = str(e)
            return result

    def _run_quality_gates(
        self, report: ResearchReport, review: ReviewResult
    ) -> Dict[str, bool]:
        """
        Run quality gate checks.

        Args:
            report: Research report
            review: Review result

        Returns:
            Dict of check name -> passed status
        """
        checks = {}

        # Gate 1: Review approval
        checks["review_approved"] = review.approved

        # Gate 2: Quality score threshold
        checks["quality_score"] = review.overall_quality_score >= self.MIN_QUALITY_SCORE

        # Gate 3: Source coverage
        checks["source_coverage"] = report.sources_used >= self.MIN_SOURCES_ANALYZED

        # Gate 4: Critical issues
        critical_issues = sum(
            1 for issue in review.issues if issue.severity == "critical"
        )
        checks["no_critical_issues"] = critical_issues <= self.MAX_CRITICAL_ISSUES

        # Gate 5: High issues
        high_issues = sum(1 for issue in review.issues if issue.severity == "high")
        checks["limited_high_issues"] = high_issues <= self.MAX_HIGH_ISSUES

        # Gate 6: Report completeness
        checks["has_papers"] = len(report.best_papers_section or "") > 0
        checks["has_summary"] = len(report.executive_summary) >= 100

        # Gate 7: References
        checks["has_references"] = len(report.references_section or "") > 0

        return checks

    def _generate_entry_id(self, report: ResearchReport) -> str:
        """
        Generate unique entry ID for knowledge entry.

        Args:
            report: Research report

        Returns:
            Unique entry ID
        """
        import hashlib

        # Hash title + timestamp for uniqueness
        content = f"{report.topic}_{datetime.now(timezone.utc).isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def validate_input(self, input_data: Any) -> bool:
        """
        Validate input (report + review).

        Args:
            input_data: Tuple of (report, review)

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(input_data, tuple):
            return False

        if len(input_data) != 2:
            return False

        report, review = input_data

        if not isinstance(report, ResearchReport):
            return False

        if not isinstance(review, ReviewResult):
            return False

        return True

    def validate_output(self, curation_data: Any) -> bool:
        """
        Validate curation output.

        Args:
            curation_data: Curation result data (KnowledgeEntry or None)

        Returns:
            True if valid, False otherwise
        """
        # Allow None for rejected entries
        if curation_data is None:
            return True

        if not isinstance(curation_data, KnowledgeEntry):
            return False

        if not curation_data.entry_id:
            return False

        if not curation_data.report:
            return False

        if not curation_data.review:
            return False

        return True
