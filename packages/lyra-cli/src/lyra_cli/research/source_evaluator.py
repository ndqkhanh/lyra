"""
Source credibility evaluation for multi-hop research.

Evaluates source trustworthiness based on source type, citation chains,
cross-references, and contradiction detection.  Inspired by the Code
Researcher paper's approach to evidence verification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto


class SourceType(Enum):
    """Categorisation of source origin for credibility weighting."""

    ACADEMIC_PAPER = auto()
    OFFICIAL_DOCS = auto()
    TECHNICAL_REPORT = auto()
    EXPERT_BLOG = auto()
    NEWS_ARTICLE = auto()
    SOCIAL_MEDIA = auto()
    USER_FORUM = auto()
    UNKNOWN = auto()


# Baseline credibility for each source type (0.0 – 1.0).
BASE_CREDIBILITY: dict[SourceType, float] = {
    SourceType.ACADEMIC_PAPER: 0.90,
    SourceType.OFFICIAL_DOCS: 0.85,
    SourceType.TECHNICAL_REPORT: 0.75,
    SourceType.EXPERT_BLOG: 0.65,
    SourceType.NEWS_ARTICLE: 0.55,
    SourceType.SOCIAL_MEDIA: 0.35,
    SourceType.USER_FORUM: 0.30,
    SourceType.UNKNOWN: 0.40,
}


@dataclass(frozen=True)
class SourceProfile:
    """Evaluated profile of a single information source."""

    source_id: str
    url: str
    source_type: SourceType
    title: str
    credibility_score: float
    citation_count: int
    detected_biases: tuple[str, ...] = field(default_factory=tuple)
    cited_by: tuple[str, ...] = field(default_factory=tuple)  # source_ids
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass(frozen=True)
class ContradictionReport:
    """A detected contradiction between two sources."""

    source_a_id: str
    source_b_id: str
    claim_a: str
    claim_b: str
    severity: float = 1.0  # 0.0 (trivial) to 1.0 (critical)


class SourceCredibility:
    """
    Evaluates and tracks source trustworthiness.

    Aggregates multiple signals:
    - Baseline credibility from source type
    - Citation chain depth (cited-by count)
    - Cross-reference consistency
    - Contradiction detection

    Provides consensus scoring for sets of sources.
    """

    def __init__(self) -> None:
        self._sources: dict[str, SourceProfile] = {}
        self._contradictions: list[ContradictionReport] = []

    # ---- evaluation -----------------------------------------------------

    def evaluate_source(
        self,
        source_id: str,
        url: str,
        source_type: SourceType = SourceType.UNKNOWN,
        title: str = "",
        citation_count: int = 0,
        detected_biases: list[str] | None = None,
        cited_by: list[str] | None = None,
    ) -> SourceProfile:
        """Create or update a source profile with a credibility score."""
        base = BASE_CREDIBILITY.get(source_type, 0.4)

        # Citation bonus: modest boost for being cited (diminishing returns)
        citation_bonus = min(citation_count * 0.02, 0.1)

        # Bias penalty
        biases = tuple(detected_biases or [])
        bias_penalty = len(biases) * 0.05

        raw = base + citation_bonus - bias_penalty
        score = max(0.0, min(1.0, raw))

        profile = SourceProfile(
            source_id=source_id,
            url=url,
            source_type=source_type,
            title=title,
            credibility_score=round(score, 3),
            citation_count=citation_count,
            detected_biases=biases,
            cited_by=tuple(cited_by or []),
        )
        self._sources[source_id] = profile
        return profile

    def get_source(self, source_id: str) -> SourceProfile | None:
        """Retrieve a source profile by ID."""
        return self._sources.get(source_id)

    def get_all_sources(self) -> list[SourceProfile]:
        """Return all evaluated sources."""
        return list(self._sources.values())

    # ---- citation chains ------------------------------------------------

    def get_citation_chain(self, source_id: str) -> list[SourceProfile]:
        """
        Walk the citation graph backwards from *source_id*.

        Returns the chain starting from the root (most-cited ancestor)
        to the given source.
        """
        chain: list[SourceProfile] = []
        visited: set[str] = set()
        current_id: str | None = source_id

        while current_id is not None and current_id not in visited:
            visited.add(current_id)
            profile = self._sources.get(current_id)
            if profile is None:
                break
            chain.append(profile)
            # Follow first cited_by as the "parent" citation
            parent_id = profile.cited_by[0] if profile.cited_by else None
            current_id = parent_id

        chain.reverse()
        return chain

    def get_consensus_score(self, source_ids: list[str]) -> float:
        """
        Compute an aggregate credibility score for a set of sources.

        Returns a weighted average where higher-credibility sources
        contribute more, and contradictions reduce the consensus.
        """
        if not source_ids:
            return 0.0

        scores = []
        for sid in source_ids:
            profile = self._sources.get(sid)
            if profile is not None:
                scores.append(profile.credibility_score)

        if not scores:
            return 0.0

        # Weighted average: each score is its own weight
        total_weight = sum(scores)
        if total_weight == 0:
            return 0.0
        weighted = sum(s * s for s in scores) / total_weight

        # Contradiction penalty
        contradiction_penalty = self._count_contradictions_in(source_ids) * 0.1
        return max(0.0, min(1.0, round(weighted - contradiction_penalty, 3)))

    # ---- contradictions -------------------------------------------------

    def detect_contradictions(
        self,
        source_a_id: str,
        source_b_id: str,
        claim_a: str,
        claim_b: str,
        severity: float = 1.0,
    ) -> ContradictionReport:
        """Record a contradiction between two sources."""
        report = ContradictionReport(
            source_a_id=source_a_id,
            source_b_id=source_b_id,
            claim_a=claim_a,
            claim_b=claim_b,
            severity=severity,
        )
        self._contradictions.append(report)
        return report

    def get_contradictions(
        self,
        source_id: str | None = None,
    ) -> list[ContradictionReport]:
        """Return contradictions, optionally filtered by source."""
        if source_id is None:
            return self._contradictions.copy()

        return [
            c
            for c in self._contradictions
            if c.source_a_id == source_id or c.source_b_id == source_id
        ]

    # ---- helpers --------------------------------------------------------

    def _count_contradictions_in(self, source_ids: list[str]) -> int:
        """Count contradictions where *both* sources are in the given set.

        A contradiction only matters for consensus when both sides of the
        disagreement are present in the evaluated set.
        """
        ids_set = set(source_ids)
        count = 0
        for c in self._contradictions:
            if c.source_a_id in ids_set and c.source_b_id in ids_set:
                count += 1
        return count
