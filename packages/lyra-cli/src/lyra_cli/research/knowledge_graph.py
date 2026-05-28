"""
Research knowledge graph.

Builds a semantic graph of research findings, supports Personalized
PageRank (PPR) for relevance ranking, and detects knowledge gaps
where evidence is sparse or contradictory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Finding:
    """A single research finding with provenance."""

    finding_id: str
    content: str
    confidence: float = 1.0
    sources: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass(frozen=True)
class FindingRelation:
    """A semantic relation between two findings."""

    relation_id: str
    source_id: str
    target_id: str
    relation_type: str  # "supports", "contradicts", "extends", "related_to"
    strength: float = 1.0  # 0.0 – 1.0


@dataclass(frozen=True)
class KnowledgeGap:
    """An identified knowledge gap in the research graph."""

    gap_id: str
    description: str
    related_finding_ids: tuple[str, ...] = field(default_factory=tuple)
    suggested_query: str = ""
    priority: float = 0.5  # 0.0 (low) – 1.0 (high)


class ResearchKnowledgeGraph:
    """
    Semantic graph of research findings.

    Supports:
    - Finding insertion with provenance tracking
    - Semantic relations between findings
    - Personalized PageRank for relevance scoring
    - Knowledge gap detection (sparse regions, contradictions)
    """

    def __init__(self) -> None:
        self._findings: dict[str, Finding] = {}
        self._relations: dict[str, FindingRelation] = {}
        # Adjacency: finding_id -> list of relation_ids (outgoing)
        self._outgoing: dict[str, list[str]] = {}
        # Adjacency: finding_id -> list of relation_ids (incoming)
        self._incoming: dict[str, list[str]] = {}

    # ---- mutation -------------------------------------------------------

    def add_finding(self, finding: Finding) -> str:
        """Add a finding node to the graph."""
        self._findings[finding.finding_id] = finding
        return finding.finding_id

    def add_relation(self, relation: FindingRelation) -> str:
        """Add a semantic relation between two findings."""
        if relation.source_id not in self._findings:
            raise KeyError(f"Source finding {relation.source_id} not found")
        if relation.target_id not in self._findings:
            raise KeyError(f"Target finding {relation.target_id} not found")

        self._relations[relation.relation_id] = relation

        # Update adjacency
        self._outgoing.setdefault(relation.source_id, []).append(
            relation.relation_id
        )
        self._incoming.setdefault(relation.target_id, []).append(
            relation.relation_id
        )

        return relation.relation_id

    # ---- query ----------------------------------------------------------

    def get_finding(self, finding_id: str) -> Finding | None:
        """Retrieve a finding by ID."""
        return self._findings.get(finding_id)

    def get_finding_count(self) -> int:
        """Return the number of findings in the graph."""
        return len(self._findings)

    def get_relation_count(self) -> int:
        """Return the number of relations in the graph."""
        return len(self._relations)

    def get_all_findings(self) -> list[Finding]:
        """Return all findings."""
        return list(self._findings.values())

    def find_findings_by_tag(self, tag: str) -> list[Finding]:
        """Return findings that have the given tag."""
        return [
            f for f in self._findings.values()
            if tag in f.tags
        ]

    def get_neighbors(
        self,
        finding_id: str,
        direction: str = "both",
    ) -> list[tuple[Finding, FindingRelation]]:
        """
        Get neighboring findings connected by relations.
        """
        neighbors: list[tuple[Finding, FindingRelation]] = []

        seen: set[str] = set()
        relation_ids: list[str] = []
        if direction in ("outgoing", "both"):
            relation_ids.extend(self._outgoing.get(finding_id, []))
        if direction in ("incoming", "both"):
            relation_ids.extend(self._incoming.get(finding_id, []))

        for rid in relation_ids:
            rel = self._relations.get(rid)
            if rel is None:
                continue
            # Determine the "other" finding
            if rel.source_id == finding_id:
                other_id = rel.target_id
            else:
                other_id = rel.source_id
            if other_id in seen:
                continue
            seen.add(other_id)
            other = self._findings.get(other_id)
            if other is not None:
                neighbors.append((other, rel))

        return neighbors

    # ---- PPR relevance --------------------------------------------------

    def compute_ppr(
        self,
        query_finding_ids: list[str],
        damping: float = 0.85,
        iterations: int = 20,
    ) -> dict[str, float]:
        """
        Compute Personalized PageRank scores.

        Higher scores mean more relevant to the query findings.
        """
        if not self._findings:
            return {}

        scores: dict[str, float] = dict.fromkeys(self._findings, 0.0)
        # Personalization vector: uniform over query findings
        teleport = 1.0 / len(query_finding_ids) if query_finding_ids else 0.0
        for fid in query_finding_ids:
            if fid in scores:
                scores[fid] = teleport

        for _ in range(iterations):
            new_scores: dict[str, float] = dict.fromkeys(self._findings, 0.0)

            for finding_id in self._findings:
                # Teleport probability
                if finding_id in query_finding_ids:
                    new_scores[finding_id] += (1.0 - damping) * teleport
                else:
                    new_scores[finding_id] += 0.0

                # Propagate from incoming neighbors
                for neighbor, rel in self.get_neighbors(
                    finding_id, direction="incoming"
                ):
                    out_degree = len(
                        self._outgoing.get(neighbor.finding_id, [])
                    )
                    if out_degree > 0:
                        contribution = (
                            scores[neighbor.finding_id] / out_degree
                        )
                        new_scores[finding_id] += (
                            damping * contribution * rel.strength
                        )

            scores = new_scores

        return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))

    def get_relevant_findings(
        self,
        query_finding_ids: list[str],
        top_k: int = 5,
    ) -> list[tuple[Finding, float]]:
        """Return the top-k findings most relevant to the query set."""
        ppr = self.compute_ppr(query_finding_ids)

        results: list[tuple[Finding, float]] = []
        for fid, score in ppr.items():
            if fid in query_finding_ids:
                continue  # skip the query nodes themselves
            finding = self._findings.get(fid)
            if finding is not None:
                results.append((finding, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    # ---- knowledge gaps -------------------------------------------------

    def find_knowledge_gaps(self) -> list[KnowledgeGap]:
        """
        Detect knowledge gaps in the graph.

        A gap is identified when:
        - A finding has no outgoing relations (isolated leaf)
        - A finding has contradictory relations pointing to it
        - A region has low connectivity (orphan findings)
        """
        gaps: list[KnowledgeGap] = []

        # 1. Orphan findings (no relations at all)
        orphans = [
            fid for fid in self._findings
            if not self._outgoing.get(fid)
            and not self._incoming.get(fid)
        ]
        for fid in orphans:
            finding = self._findings[fid]
            gaps.append(KnowledgeGap(
                gap_id=f"gap_orphan_{fid}",
                description=(
                    f"Finding '{finding.content[:60]}...' has no connections"
                ),
                related_finding_ids=(fid,),
                suggested_query=finding.content,
                priority=0.6,
            ))

        # 2. Contradictory relations (two findings with contradicting edges)
        for rid, rel in self._relations.items():
            if rel.relation_type == "contradicts":
                source = self._findings.get(rel.source_id)
                target = self._findings.get(rel.target_id)
                if source is not None and target is not None:
                    gaps.append(KnowledgeGap(
                        gap_id=f"gap_contradiction_{rid}",
                        description=(
                            f"Contradiction between '{source.content[:40]}...' "
                            f"and '{target.content[:40]}...'"
                        ),
                        related_finding_ids=(rel.source_id, rel.target_id),
                        suggested_query=(
                            f"Resolve: {source.content} vs {target.content}"
                        ),
                        priority=0.8,
                    ))

        # 3. Low connectivity: findings with only one relation
        low_connectivity = [
            fid for fid in self._findings
            if len(self._outgoing.get(fid, []))
               + len(self._incoming.get(fid, []))
               == 1
        ]
        for fid in low_connectivity:
            finding = self._findings[fid]
            gaps.append(KnowledgeGap(
                gap_id=f"gap_sparse_{fid}",
                description=(
                    f"Finding '{finding.content[:60]}...' has only one "
                    f"connection — further evidence needed"
                ),
                related_finding_ids=(fid,),
                suggested_query=finding.content,
                priority=0.4,
            ))

        return gaps
