"""Discovery Gate — Quality gate between Discovery → Analysis."""
from __future__ import annotations

from lyra_research.discovery import ResearchSource
from lyra_research.quality.quality_criterion import QualityCriterion
from lyra_research.quality.quality_gate import QualityGate


class DiscoveryGate(QualityGate):
    """
    Quality gate between Discovery → Analysis.

    Criteria:
    - Minimum 10 sources discovered
    - At least 3 different source types (diversity)
    - Average quality score >= 0.6
    """

    def __init__(self) -> None:
        """Initialize discovery gate with criteria."""

        def check_min_sources(sources: list[ResearchSource]) -> float:
            """Check minimum number of sources."""
            return float(len(sources))

        def check_source_diversity(sources: list[ResearchSource]) -> float:
            """Check diversity of source types."""
            if not sources:
                return 0.0
            unique_types = len({s.source_type.value for s in sources})
            return float(unique_types)

        def check_avg_quality(sources: list[ResearchSource]) -> float:
            """Check average quality score from metadata."""
            if not sources:
                return 0.0
            # Quality score is stored in metadata during analysis
            # For discovery gate, we use a heuristic based on citations/stars
            quality_scores = []
            for s in sources:
                # Check if quality_score is in metadata
                if "quality_score" in s.metadata:
                    quality_scores.append(s.metadata["quality_score"])
                else:
                    # Heuristic: sources with citations/stars are higher quality
                    score = 0.5  # Base score
                    if s.citations > 0:
                        score += 0.3
                    if s.stars > 0:
                        score += 0.2
                    quality_scores.append(score)

            if not quality_scores:
                return 0.0
            return sum(quality_scores) / len(quality_scores)

        criteria = [
            QualityCriterion(
                name="min_sources",
                check_fn=check_min_sources,
                severity="critical",
                threshold=10.0,
            ),
            QualityCriterion(
                name="source_diversity",
                check_fn=check_source_diversity,
                severity="high",
                threshold=3.0,
            ),
            QualityCriterion(
                name="avg_quality",
                check_fn=check_avg_quality,
                severity="medium",
                threshold=0.6,
            ),
        ]

        super().__init__("DiscoveryGate", criteria)
