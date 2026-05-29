"""Curation Gate — Final quality gate before knowledge storage."""
from __future__ import annotations

from lyra_research.quality.quality_criterion import QualityCriterion
from lyra_research.quality.quality_gate import QualityGate
from lyra_research.roles.curator_role import KnowledgeEntry


class CurationGate(QualityGate):
    """
    Final quality gate before knowledge storage.

    Criteria:
    - Entry was accepted by curator
    - Quality score >= 0.7
    - Report has valid entry ID
    """

    def __init__(self) -> None:
        """Initialize curation gate with criteria."""

        def check_accepted(entry: KnowledgeEntry | None) -> float:
            """Check if entry was accepted."""
            if entry is None:
                return 0.0
            return 1.0 if entry.accepted else 0.0

        def check_quality_score(entry: KnowledgeEntry | None) -> float:
            """Check quality score from review."""
            if entry is None or entry.review is None:
                return 0.0
            return entry.review.overall_quality_score

        def check_valid_entry_id(entry: KnowledgeEntry | None) -> float:
            """Check for valid entry ID."""
            if entry is None or not entry.entry_id:
                return 0.0
            return 1.0 if len(entry.entry_id) > 0 else 0.0

        criteria = [
            QualityCriterion(
                name="accepted",
                check_fn=check_accepted,
                severity="critical",
                threshold=1.0,
            ),
            QualityCriterion(
                name="quality_score",
                check_fn=check_quality_score,
                severity="high",
                threshold=0.7,
            ),
            QualityCriterion(
                name="valid_entry_id",
                check_fn=check_valid_entry_id,
                severity="medium",
                threshold=1.0,
            ),
        ]

        super().__init__("CurationGate", criteria)
