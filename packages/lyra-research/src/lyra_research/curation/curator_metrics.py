"""Curator Metrics — Performance tracking for curator role."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from lyra_research.curation.curation_workflow import CurationDecision, DecisionType


@dataclass
class CuratorMetrics:
    """
    Tracks curator performance metrics.

    Monitors curation decisions, quality scores, and acceptance rates
    to measure curator effectiveness.
    """

    total_reviewed: int = 0
    approved: int = 0
    rejected: int = 0
    revised: int = 0
    avg_quality_score: float = 0.0
    acceptance_rate: float = 0.0
    quality_scores: List[float] = field(default_factory=list)
    decisions: List[CurationDecision] = field(default_factory=list)

    def record_decision(self, decision: CurationDecision, quality_score: float) -> None:
        """
        Record curation decision.

        Args:
            decision: Curation decision made
            quality_score: Quality score of the entry
        """
        self.total_reviewed += 1
        self.quality_scores.append(quality_score)
        self.decisions.append(decision)

        # Update counters
        if decision.decision_type == DecisionType.APPROVE:
            self.approved += 1
        elif decision.decision_type == DecisionType.REJECT:
            self.rejected += 1
        elif decision.decision_type == DecisionType.REQUEST_REVISION:
            self.revised += 1

        # Recalculate metrics
        self._recalculate_metrics()

    def _recalculate_metrics(self) -> None:
        """Recalculate derived metrics."""
        # Average quality score
        if self.quality_scores:
            self.avg_quality_score = sum(self.quality_scores) / len(self.quality_scores)
        else:
            self.avg_quality_score = 0.0

        # Acceptance rate (approved / total)
        if self.total_reviewed > 0:
            self.acceptance_rate = self.approved / self.total_reviewed
        else:
            self.acceptance_rate = 0.0

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get curator performance metrics.

        Returns:
            Dictionary of metrics
        """
        return {
            "total_reviewed": self.total_reviewed,
            "approved": self.approved,
            "rejected": self.rejected,
            "revised": self.revised,
            "avg_quality_score": round(self.avg_quality_score, 3),
            "acceptance_rate": round(self.acceptance_rate, 3),
            "rejection_rate": round(
                self.rejected / self.total_reviewed if self.total_reviewed > 0 else 0.0,
                3,
            ),
            "revision_rate": round(
                self.revised / self.total_reviewed if self.total_reviewed > 0 else 0.0,
                3,
            ),
        }

    def get_decision_breakdown(self) -> Dict[str, int]:
        """
        Get breakdown of decisions by type.

        Returns:
            Dictionary mapping decision type to count
        """
        return {
            "approved": self.approved,
            "rejected": self.rejected,
            "revised": self.revised,
        }

    def get_quality_stats(self) -> Dict[str, float]:
        """
        Get quality score statistics.

        Returns:
            Dictionary of quality statistics
        """
        if not self.quality_scores:
            return {
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0,
                "median": 0.0,
            }

        sorted_scores = sorted(self.quality_scores)
        n = len(sorted_scores)
        median = (
            sorted_scores[n // 2]
            if n % 2 == 1
            else (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2
        )

        return {
            "avg": round(self.avg_quality_score, 3),
            "min": round(min(self.quality_scores), 3),
            "max": round(max(self.quality_scores), 3),
            "median": round(median, 3),
        }

    def reset(self) -> None:
        """Reset all metrics to zero."""
        self.total_reviewed = 0
        self.approved = 0
        self.rejected = 0
        self.revised = 0
        self.avg_quality_score = 0.0
        self.acceptance_rate = 0.0
        self.quality_scores = []
        self.decisions = []
