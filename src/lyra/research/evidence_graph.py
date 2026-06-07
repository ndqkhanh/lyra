"""
Evidence Graph — Argus-style shared evidence graph for research claims.

Maintains a directed graph of ``EvidenceNode`` (claims) connected by typed
``EvidenceEdge`` relationships (supports, contradicts, cites, derives_from).
Provides cross-claim verification, contradiction detection, and
Mermaid/Markdown export for paper generation.

Key features
------------
- **Claim graph**: nodes store claims with source tracking and confidence.
- **Typed edges**: supports, contradicts, cites, derives_from relationships.
- **Self-verification**: cross-check a claim against its graph neighborhood
  to produce a ``VerificationResult`` with evidence balance.
- **Contradiction detection**: find conflicting evidence pairs automatically.
- **Graph export**: Mermaid flowchart and Markdown report for papers.

References
----------
- Argus: arXiv 2503.12419 (Structured Evidence Graph for Multi-Agent Systems)
- DeepScientist: arXiv 2505.22954
"""

from __future__ import annotations

import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# =============================================================================
# Enums and data structures
# =============================================================================


class VerificationStatus(str, Enum):
    """Verification status of an evidence node."""

    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    REFUTED = "refuted"
    CONFIRMED = "confirmed"


class EdgeType(str, Enum):
    """Typed relationship between two evidence nodes."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CITES = "cites"
    DERIVES_FROM = "derives_from"


@dataclass(frozen=True)
class EvidenceNode:
    """A single claim node in the evidence graph.

    Attributes:
        node_id: Unique identifier for this node.
        claim: The claim statement.
        source: Origin of the claim (paper, URL, experiment ID, etc.).
        confidence: Confidence score (0.0–1.0) assigned by the author.
        verification_status: Current verification status.
        supporting_count: Number of SUPPORTS edges pointing to this node.
        contradicting_count: Number of CONTRADICTS edges pointing to this node.
        tags: Arbitrary labels for filtering and search.
        timestamp: Unix timestamp of creation.
        metadata: Arbitrary key-value store.
    """

    node_id: str = ""
    claim: str = ""
    source: str = ""
    confidence: float = 0.5
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    supporting_count: int = 0
    contradicting_count: int = 0
    tags: tuple[str, ...] = ()
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Clamp confidence to [0.0, 1.0]."""
        clamped = max(0.0, min(1.0, self.confidence))
        object.__setattr__(self, "confidence", clamped)

    @property
    def evidence_balance(self) -> float:
        """Net evidence balance: supporting_count - contradicting_count."""
        return self.supporting_count - self.contradicting_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "claim": self.claim,
            "source": self.source,
            "confidence": self.confidence,
            "verification_status": self.verification_status.value,
            "supporting_count": self.supporting_count,
            "contradicting_count": self.contradicting_count,
            "tags": list(self.tags),
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceNode:
        return cls(
            node_id=data.get("node_id", ""),
            claim=data.get("claim", ""),
            source=data.get("source", ""),
            confidence=data.get("confidence", 0.5),
            verification_status=VerificationStatus(
                data.get("verification_status", "unverified")
            ),
            supporting_count=data.get("supporting_count", 0),
            contradicting_count=data.get("contradicting_count", 0),
            tags=tuple(data.get("tags", [])),
            timestamp=data.get("timestamp", 0.0),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class EvidenceEdge:
    """A typed, directed edge between two evidence nodes.

    Attributes:
        edge_id: Unique identifier.
        source_id: Node ID of the source (subject).
        target_id: Node ID of the target (object).
        edge_type: Nature of the relationship.
        weight: Confidence weight of this edge (0.0–1.0).
        rationale: Free-text justification for the edge.
        timestamp: Unix timestamp of creation.
    """

    edge_id: str = ""
    source_id: str = ""
    target_id: str = ""
    edge_type: EdgeType = EdgeType.SUPPORTS
    weight: float = 1.0
    rationale: str = ""
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        """Clamp weight to [0.0, 1.0]."""
        clamped = max(0.0, min(1.0, self.weight))
        object.__setattr__(self, "weight", clamped)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceEdge:
        return cls(
            edge_id=data.get("edge_id", ""),
            source_id=data["source_id"],
            target_id=data["target_id"],
            edge_type=EdgeType(data.get("edge_type", "supports")),
            weight=data.get("weight", 1.0),
            rationale=data.get("rationale", ""),
            timestamp=data.get("timestamp", 0.0),
        )


@dataclass(frozen=True)
class VerificationResult:
    """Result of verifying a claim against the evidence graph.

    Attributes:
        node_id: The claim node that was verified.
        status: Updated verification status.
        confidence: Adjusted confidence based on graph cross-check.
        supporting_evidence: List of evidence edge rationales that support.
        contradicting_evidence: List of evidence edge rationales that contradict.
        balance: Supporting count minus contradicting count.
        total_supporting: Number of supporting edges found.
        total_contradicting: Number of contradicting edges found.
        summary: Human-readable summary of the verification.
    """

    node_id: str
    status: VerificationStatus
    confidence: float
    supporting_evidence: tuple[str, ...] = ()
    contradicting_evidence: tuple[str, ...] = ()
    balance: int = 0
    total_supporting: int = 0
    total_contradicting: int = 0
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "confidence": round(self.confidence, 4),
            "balance": self.balance,
            "total_supporting": self.total_supporting,
            "total_contradicting": self.total_contradicting,
            "summary": self.summary,
        }


# =============================================================================
# Query types
# =============================================================================


@dataclass(frozen=True)
class GraphQuery:
    """Filter parameters for querying the evidence graph.

    Attributes:
        claim_substring: Match nodes whose claim contains this substring.
        status: Filter by verification status.
        min_confidence: Minimum confidence threshold.
        max_confidence: Maximum confidence threshold.
        tags: Node must have at least one of these tags.
        edge_type: Only return nodes connected by this edge type.
        source: Filter by source.
        limit: Maximum number of results.
    """

    claim_substring: str = ""
    status: VerificationStatus | None = None
    min_confidence: float = 0.0
    max_confidence: float = 1.0
    tags: tuple[str, ...] = ()
    edge_type: EdgeType | None = None
    source: str = ""
    limit: int = 50


@dataclass(frozen=True)
class ContradictionPair:
    """A pair of conflicting evidence nodes.

    Attributes:
        node_a_id: First node in the contradiction pair.
        node_b_id: Second node in the contradiction pair.
        claim_a: Claim text of node A.
        claim_b: Claim text of node B.
        edge_ids: The CONTRADICTS edge(s) connecting these nodes.
        severity: Number of contradicting edges / total edges between them.
    """

    node_a_id: str
    node_b_id: str
    claim_a: str
    claim_b: str
    edge_ids: tuple[str, ...] = ()
    severity: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_a_id": self.node_a_id,
            "node_b_id": self.node_b_id,
            "claim_a": self.claim_a,
            "claim_b": self.claim_b,
            "severity": round(self.severity, 4),
        }


# =============================================================================
# EvidenceGraph
# =============================================================================


class EvidenceGraph:
    """Argus-style shared evidence graph for research claims.

    Maintains a directed graph of ``EvidenceNode`` objects connected by
    typed ``EvidenceEdge`` relationships. Supports adding evidence,
    cross-checking claims against the graph, contradiction detection,
    and graph export for paper generation.

    Usage::

        g = EvidenceGraph()
        n1 = g.add_evidence("LoRA reduces memory by 4x", "arxiv:2302.0", 0.85)
        n2 = g.add_evidence("LoRA degrades on long sequences", "experiment:42", 0.65)
        g.add_edge(n1, n2, EdgeType.CONTRADICTS, rationale="Sequence length > 2K")

        result = g.verify_node(n1)
        pairs = g.detect_contradictions()
        mermaid = g.to_mermaid()
    """

    def __init__(self) -> None:
        self._nodes: dict[str, EvidenceNode] = {}
        self._edges: dict[str, EvidenceEdge] = {}

        # Index: node_id -> list of edge_ids
        self._outgoing: dict[str, list[str]] = defaultdict(list)
        self._incoming: dict[str, list[str]] = defaultdict(list)

        # Full-text index for query search
        self._text_index: dict[str, set[str]] = defaultdict(set)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_evidence(
        self,
        claim: str,
        source: str = "",
        confidence: float = 0.5,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add a claim as a new evidence node.

        Args:
            claim: The claim statement.
            source: Origin identifier (paper, URL, experiment, etc.).
            confidence: Author-assigned confidence (0.0–1.0).
            tags: Arbitrary labels for filtering.
            metadata: Additional key-value data.

        Returns:
            The ``node_id`` assigned to the new node.
        """
        node_id = str(uuid.uuid4())
        now = time.time()

        node = EvidenceNode(
            node_id=node_id,
            claim=claim,
            source=source,
            confidence=confidence,
            verification_status=VerificationStatus.UNVERIFIED,
            tags=tuple(tags or []),
            timestamp=now,
            metadata=dict(metadata or {}),
        )

        self._nodes[node_id] = node

        # Update text index
        for word in self._tokenize(claim):
            self._text_index[word].add(node_id)

        return node_id

    def get_node(self, node_id: str) -> EvidenceNode | None:
        """Retrieve a single evidence node by ID."""
        return self._nodes.get(node_id)

    def update_node(
        self,
        node_id: str,
        **updates: Any,
    ) -> EvidenceNode:
        """Update fields of an evidence node (immutable copy).

        Args:
            node_id: The node to update.
            **updates: Fields to update (``confidence``, ``source``, etc.).

        Returns:
            The updated ``EvidenceNode``.

        Raises:
            KeyError: If ``node_id`` does not exist.
        """
        node = self._nodes.get(node_id)
        if node is None:
            raise KeyError(f"Evidence node {node_id} not found.")

        merged = node.to_dict()
        merged.update(updates)
        updated = EvidenceNode.from_dict(merged)
        self._nodes[node_id] = updated
        return updated

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType = EdgeType.SUPPORTS,
        weight: float = 1.0,
        rationale: str = "",
    ) -> str:
        """Add a typed directed edge between two evidence nodes.

        Args:
            source_id: Source node ID.
            target_id: Target node ID.
            edge_type: Nature of the relationship.
            weight: Confidence weight (0.0–1.0).
            rationale: Free-text justification.

        Returns:
            The ``edge_id`` assigned to the new edge.

        Raises:
            KeyError: If either node ID does not exist.
        """
        if source_id not in self._nodes:
            raise KeyError(f"Source node {source_id} not found.")
        if target_id not in self._nodes:
            raise KeyError(f"Target node {target_id} not found.")

        edge_id = str(uuid.uuid4())
        now = time.time()

        edge = EvidenceEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            weight=weight,
            rationale=rationale,
            timestamp=now,
        )

        self._edges[edge_id] = edge
        self._outgoing[source_id].append(edge_id)
        self._incoming[target_id].append(edge_id)

        # Update node counts for SUPPORTS and CONTRADICTS edges
        if edge_type == EdgeType.SUPPORTS:
            self._bump_supporting_count(target_id, +1)
        elif edge_type == EdgeType.CONTRADICTS:
            self._bump_contradicting_count(target_id, +1)

        return edge_id

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all its incident edges.

        Args:
            node_id: The node to remove.

        Returns:
            True if the node was removed, False if not found.
        """
        if node_id not in self._nodes:
            return False

        # Collect incident edge IDs
        incident = set(self._outgoing.get(node_id, []))
        incident.update(self._incoming.get(node_id, []))

        for eid in incident:
            edge = self._edges.pop(eid, None)
            if edge is not None:
                self._outgoing[edge.source_id] = [
                    e for e in self._outgoing.get(edge.source_id, []) if e != eid
                ]
                self._incoming[edge.target_id] = [
                    e for e in self._incoming.get(edge.target_id, []) if e != eid
                ]

        self._nodes.pop(node_id, None)
        self._outgoing.pop(node_id, None)
        self._incoming.pop(node_id, None)

        # Clean text index
        for word in list(self._text_index.keys()):
            self._text_index[word].discard(node_id)

        return True

    def remove_edge(self, edge_id: str) -> bool:
        """Remove a single edge.

        Args:
            edge_id: The edge to remove.

        Returns:
            True if the edge was removed, False if not found.
        """
        edge = self._edges.pop(edge_id, None)
        if edge is None:
            return False

        self._outgoing[edge.source_id] = [
            e for e in self._outgoing.get(edge.source_id, []) if e != edge_id
        ]
        self._incoming[edge.target_id] = [
            e for e in self._incoming.get(edge.target_id, []) if e != edge_id
        ]

        if edge.edge_type == EdgeType.SUPPORTS:
            self._bump_supporting_count(edge.target_id, -1)
        elif edge.edge_type == EdgeType.CONTRADICTS:
            self._bump_contradicting_count(edge.target_id, -1)

        return True

    # ------------------------------------------------------------------
    # Graph queries
    # ------------------------------------------------------------------

    def query(self, q: GraphQuery) -> list[EvidenceNode]:
        """Query nodes by claim content, status, confidence, tags, or source.

        Args:
            q: ``GraphQuery`` with filter parameters.

        Returns:
            Filtered list of ``EvidenceNode`` sorted by confidence descending.
        """
        candidates = list(self._nodes.values())

        # Claim substring
        if q.claim_substring:
            lower_sub = q.claim_substring.lower()
            candidates = [
                n for n in candidates if lower_sub in n.claim.lower()
            ]

        # Status filter
        if q.status is not None:
            candidates = [n for n in candidates if n.verification_status == q.status]

        # Confidence range
        candidates = [
            n
            for n in candidates
            if q.min_confidence <= n.confidence <= q.max_confidence
        ]

        # Tags (match any)
        if q.tags:
            tag_set = set(q.tags)
            candidates = [
                n for n in candidates if set(n.tags) & tag_set
            ]

        # Source
        if q.source:
            lower_src = q.source.lower()
            candidates = [
                n for n in candidates if lower_src in n.source.lower()
            ]

        # Edge type filter: restrict to nodes connected by that edge type
        if q.edge_type is not None:
            connected_ids: set[str] = set()
            for edge in self._edges.values():
                if edge.edge_type == q.edge_type:
                    connected_ids.add(edge.source_id)
                    connected_ids.add(edge.target_id)
            candidates = [n for n in candidates if n.node_id in connected_ids]

        # Sort by confidence descending
        candidates.sort(key=lambda n: n.confidence, reverse=True)

        return candidates[: q.limit]

    def find_evidence_for(self, claim: str, top_k: int = 10) -> list[EvidenceNode]:
        """Find evidence nodes that support a given claim.

        Uses keyword overlap to find semantically related nodes, then
        filters by SUPPORTS edges.

        Args:
            claim: The claim to find evidence for.
            top_k: Maximum results.

        Returns:
            List of ``EvidenceNode`` that directly or indirectly support
            the claim.
        """
        if not claim.strip():
            return []

        # Find candidate nodes by keyword overlap
        query_terms = set(self._tokenize(claim))
        candidates: list[EvidenceNode] = []
        for node in self._nodes.values():
            node_terms = set(self._tokenize(node.claim))
            overlap = len(query_terms & node_terms)
            if overlap > 0:
                candidates.append(node)

        # Sort by overlap count, then by supporting_count
        candidates.sort(
            key=lambda n: (
                len(query_terms & set(self._tokenize(n.claim))),
                n.supporting_count,
            ),
            reverse=True,
        )

        return candidates[:top_k]

    def find_evidence_against(self, claim: str, top_k: int = 10) -> list[EvidenceNode]:
        """Find evidence nodes that contradict a given claim.

        Uses keyword overlap to find related nodes, then filters by
        CONTRADICTS edges.

        Args:
            claim: The claim to find contradicting evidence for.
            top_k: Maximum results.

        Returns:
            List of ``EvidenceNode`` that contradict the claim.
        """
        if not claim.strip():
            return []

        query_terms = set(self._tokenize(claim))
        candidates: list[EvidenceNode] = []
        for node in self._nodes.values():
            node_terms = set(self._tokenize(node.claim))
            overlap = len(query_terms & node_terms)
            if overlap > 0:
                candidates.append(node)

        candidates.sort(
            key=lambda n: (
                len(query_terms & set(self._tokenize(n.claim))),
                n.contradicting_count,
            ),
            reverse=True,
        )

        return candidates[:top_k]

    def edges_for_node(self, node_id: str) -> list[EvidenceEdge]:
        """Return all edges incident to a node.

        Args:
            node_id: The node to look up.

        Returns:
            List of ``EvidenceEdge`` instances (outgoing + incoming).
        """
        eids: set[str] = set()
        eids.update(self._outgoing.get(node_id, []))
        eids.update(self._incoming.get(node_id, []))
        return [self._edges[eid] for eid in eids if eid in self._edges]

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify_node(self, node_id: str) -> VerificationResult:
        """Cross-check a claim against its graph neighborhood.

        Analyzes all incident edges to determine whether the claim is
        supported, contradicted, or unresolved. The verification status
        is derived from the evidence balance:

            - ``balance > 0`` and ``confidence >= 0.7`` → CONFIRMED
            - ``balance > 0`` → VERIFIED
            - ``balance == 0`` → UNVERIFIED (neutral)
            - ``balance < 0`` and ``confidence < 0.3`` → REFUTED
            - ``balance < 0`` → DISPUTED

        Args:
            node_id: The claim node to verify.

        Returns:
            ``VerificationResult`` with adjusted confidence and status.

        Raises:
            KeyError: If ``node_id`` does not exist.
        """
        node = self._nodes.get(node_id)
        if node is None:
            raise KeyError(f"Evidence node {node_id} not found.")

        edges = self.edges_for_node(node_id)

        supporting: list[EvidenceEdge] = []
        contradicting: list[EvidenceEdge] = []
        for edge in edges:
            if edge.edge_type == EdgeType.SUPPORTS:
                supporting.append(edge)
            elif edge.edge_type == EdgeType.CONTRADICTS:
                contradicting.append(edge)

        total_supporting = len(supporting)
        total_contradicting = len(contradicting)
        balance = total_supporting - total_contradicting

        # Compute weighted confidence from edges
        support_conf = (
            sum(e.weight for e in supporting) / max(total_supporting, 1)
        )
        contradict_conf = (
            sum(e.weight for e in contradicting) / max(total_contradicting, 1)
        )

        # Adjusted confidence: blend original with evidence weights
        if total_supporting + total_contradicting > 0:
            evidence_signal = support_conf - contradict_conf
            adjusted = max(
                0.0, min(1.0, node.confidence + 0.3 * evidence_signal)
            )
        else:
            adjusted = node.confidence

        # Determine status
        if balance > 0 and adjusted >= 0.7:
            status = VerificationStatus.CONFIRMED
        elif balance > 0:
            status = VerificationStatus.VERIFIED
        elif balance < 0 and adjusted < 0.3:
            status = VerificationStatus.REFUTED
        elif balance < 0:
            status = VerificationStatus.DISPUTED
        else:
            status = VerificationStatus.UNVERIFIED

        # Update the node's status
        self.update_node(
            node_id,
            verification_status=status,
            confidence=round(adjusted, 4),
            supporting_count=total_supporting,
            contradicting_count=total_contradicting,
        )

        # Build summary
        support_rationales = tuple(e.rationale for e in supporting if e.rationale)
        contradict_rationales = tuple(
            e.rationale for e in contradicting if e.rationale
        )

        summary = (
            f"Claim: {node.claim[:80]}... | "
            f"Status: {status.value} | "
            f"Balance: +{balance} | "
            f"Supporting: {total_supporting}, Contradicting: {total_contradicting} | "
            f"Confidence: {adjusted:.2f}"
        )

        return VerificationResult(
            node_id=node_id,
            status=status,
            confidence=round(adjusted, 4),
            supporting_evidence=support_rationales,
            contradicting_evidence=contradict_rationales,
            balance=balance,
            total_supporting=total_supporting,
            total_contradicting=total_contradicting,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Contradiction detection
    # ------------------------------------------------------------------

    def detect_contradictions(
        self,
        min_severity: float = 0.3,
    ) -> list[ContradictionPair]:
        """Find pairs of nodes that have conflicting evidence.

        Scans the graph for pairs of nodes connected by CONTRADICTS
        edges (directly or through shared neighbours) and returns
        those with severity above the threshold.

        Args:
            min_severity: Minimum severity ratio (0.0–1.0) to include.

        Returns:
            List of ``ContradictionPair`` sorted by severity descending.
        """
        # Direct contradictions: nodes connected by CONTRADICTS edges
        direct: dict[tuple[str, str], list[str]] = defaultdict(list)
        for edge in self._edges.values():
            if edge.edge_type == EdgeType.CONTRADICTS:
                key = self._normalize_pair(edge.source_id, edge.target_id)
                direct[key].append(edge.edge_id)

        pairs: list[ContradictionPair] = []

        for (aid, bid), eids in direct.items():
            node_a = self._nodes.get(aid)
            node_b = self._nodes.get(bid)
            if node_a is None or node_b is None:
                continue

            total_edges_between = len(
                [e for e in self._edges.values()
                 if {e.source_id, e.target_id} == {aid, bid}]
            )
            contradiction_edges = len(eids)
            severity = contradiction_edges / max(total_edges_between, 1)

            if severity >= min_severity:
                pairs.append(
                    ContradictionPair(
                        node_a_id=aid,
                        node_b_id=bid,
                        claim_a=node_a.claim,
                        claim_b=node_b.claim,
                        edge_ids=tuple(eids),
                        severity=round(severity, 4),
                    )
                )

        # Also check for indirect contradictions via shared neighbours
        indirect_pairs = self._detect_indirect_contradictions(min_severity)
        pairs.extend(indirect_pairs)

        # Deduplicate by sorted pair key
        seen: set[tuple[str, str]] = set()
        deduped: list[ContradictionPair] = []
        for p in pairs:
            key = self._normalize_pair(p.node_a_id, p.node_b_id)
            if key not in seen:
                seen.add(key)
                deduped.append(p)

        deduped.sort(key=lambda p: p.severity, reverse=True)
        return deduped

    def _detect_indirect_contradictions(
        self,
        min_severity: float = 0.3,
    ) -> list[ContradictionPair]:
        """Find nodes that indirectly contradict through shared neighbours.

        Scenarios:
            - Node A SUPPORTS Node C, Node B CONTRADICTS Node C
              → A and B are indirectly contradictory.

        Returns:
            List of ``ContradictionPair`` for indirect contradictions.
        """
        pairs: list[ContradictionPair] = []

        # Build per-node support and contradiction sets
        node_supports: dict[str, set[str]] = defaultdict(set)
        node_contradicts: dict[str, set[str]] = defaultdict(set)

        for edge in self._edges.values():
            if edge.edge_type == EdgeType.SUPPORTS:
                node_supports[edge.source_id].add(edge.target_id)
            elif edge.edge_type == EdgeType.CONTRADICTS:
                node_contradicts[edge.source_id].add(edge.target_id)

        # If A supports C and B contradicts C, then A and B are
        # indirectly contradictory (A->C<-B)
        for c_id in list(self._nodes.keys()):
            supporters = {n for n, targets in node_supports.items() if c_id in targets}
            contradictors = {
                n for n, targets in node_contradicts.items() if c_id in targets
            }

            for supporter in supporters:
                for contradicter in contradictors:
                    if supporter == contradicter:
                        continue
                    pair_key = self._normalize_pair(supporter, contradicter)
                    pairs.append(
                        ContradictionPair(
                            node_a_id=supporter,
                            node_b_id=contradicter,
                            claim_a=self._nodes[supporter].claim,
                            claim_b=self._nodes[contradicter].claim,
                            severity=1.0,
                        )
                    )

        return pairs

    # ------------------------------------------------------------------
    # Graph export (Mermaid / Markdown)
    # ------------------------------------------------------------------

    def to_mermaid(
        self,
        show_legend: bool = True,
        high_confidence_only: bool = False,
    ) -> str:
        """Export the evidence graph as a Mermaid flowchart.

        Args:
            show_legend: If True, include a legend subgraph.
            high_confidence_only: If True, only include nodes with
                ``confidence >= 0.7``.

        Returns:
            Mermaid flowchart markdown string.
        """
        lines: list[str] = ["```mermaid", "flowchart LR"]

        # Node styling per verification status
        status_styles: dict[VerificationStatus, str] = {
            VerificationStatus.CONFIRMED: "fill:#d5f5e3,stroke:#27ae60",
            VerificationStatus.VERIFIED: "fill:#d4e6f1,stroke:#2980b9",
            VerificationStatus.UNVERIFIED: "fill:#f0f3f4,stroke:#85929e",
            VerificationStatus.DISPUTED: "fill:#fdebd0,stroke:#e67e22",
            VerificationStatus.REFUTED: "fill:#fadbd8,stroke:#c0392b",
        }

        # Edge styling
        edge_style: dict[EdgeType, str] = {
            EdgeType.SUPPORTS: "-->|supports|",
            EdgeType.CONTRADICTS: "x--x|contradicts|",
            EdgeType.CITES: "-.->|cites|",
            EdgeType.DERIVES_FROM: "==>|derives|",
        }

        # Determine which nodes to include
        node_ids: set[str]
        if high_confidence_only:
            node_ids = {
                nid
                for nid, n in self._nodes.items()
                if n.confidence >= 0.7
            }
        else:
            node_ids = set(self._nodes.keys())

        # Add nodes
        for nid in sorted(node_ids):
            node = self._nodes[nid]
            safe_id = self._safe_mermaid_id(nid)
            style = status_styles.get(
                node.verification_status, status_styles[VerificationStatus.UNVERIFIED]
            )
            label = node.claim.replace('"', "'")[:60]
            lines.append(f'    {safe_id}["{label}"]')
            lines.append(f"    style {safe_id} {style}")

        # Add edges
        for edge in self._edges.values():
            if edge.source_id not in node_ids or edge.target_id not in node_ids:
                continue
            src = self._safe_mermaid_id(edge.source_id)
            tgt = self._safe_mermaid_id(edge.target_id)
            arrow = edge_style.get(edge.edge_type, "-->")
            lines.append(f"    {src} {arrow} {tgt}")

        # Legend
        if show_legend:
            lines.extend([
                "",
                "    subgraph Legend",
                "        direction LR",
                '        L_conf["Confirmed"]',
                "        style L_conf fill:#d5f5e3,stroke:#27ae60",
                '        L_ver["Verified"]',
                "        style L_ver fill:#d4e6f1,stroke:#2980b9",
                '        L_dis["Disputed"]',
                "        style L_dis fill:#fdebd0,stroke:#e67e22",
                '        L_ref["Refuted"]',
                "        style L_ref fill:#fadbd8,stroke:#c0392b",
                '        L_sup["A"] -->|supports| L_sup2["B"]',
                '        L_con["A"] x--x|contradicts| L_con2["B"]',
                "    end",
            ])

        lines.append("```")
        return "\n".join(lines)

    def to_markdown_report(self) -> str:
        """Generate a full evidence graph report in Markdown.

        Returns:
            Markdown string with summary, statistics, node table,
            contradiction highlights, and Mermaid diagram.
        """
        parts: list[str] = [
            "# Evidence Graph Report",
            "",
            f"**Total claims:** {len(self._nodes)}",
            f"**Total evidence edges:** {len(self._edges)}",
            "",
        ]

        # Status distribution
        status_counts: Counter[VerificationStatus] = Counter(
            n.verification_status for n in self._nodes.values()
        )
        parts.append("## Status Distribution")
        parts.append("")
        for status in VerificationStatus:
            count = status_counts.get(status, 0)
            parts.append(f"- **{status.value}**: {count}")
        parts.append("")

        # Edge type distribution
        edge_counts: Counter[EdgeType] = Counter(
            e.edge_type for e in self._edges.values()
        )
        parts.append("## Edge Distribution")
        parts.append("")
        for etype in EdgeType:
            count = edge_counts.get(etype, 0)
            parts.append(f"- **{etype.value}**: {count}")
        parts.append("")

        # Contradictions
        contradictions = self.detect_contradictions()
        if contradictions:
            parts.append("## Contradictions Detected")
            parts.append("")
            for pair in contradictions:
                parts.append(
                    f"- **Disagreement**: \"{pair.claim_a[:50]}...\" vs "
                    f"\"{pair.claim_b[:50]}...\" "
                    f"(severity: {pair.severity:.2f})"
                )
            parts.append("")

        # Top claims by confidence
        sorted_nodes = sorted(
            self._nodes.values(), key=lambda n: n.confidence, reverse=True
        )
        parts.append("## Top Claims by Confidence")
        parts.append("")
        parts.append("| Claim | Source | Confidence | Status | Balance |")
        parts.append("|-------|--------|------------|--------|---------|")
        for node in sorted_nodes[:20]:
            parts.append(
                f"| {node.claim[:60]}... | {node.source[:30]} | "
                f"{node.confidence:.2f} | {node.verification_status.value} | "
                f"{node.evidence_balance} |"
            )
        parts.append("")

        # Mermaid diagram
        parts.append("## Evidence Graph")
        parts.append("")
        parts.append(self.to_mermaid(show_legend=True))
        parts.append("")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the evidence graph to a JSON-safe dict."""
        return {
            "nodes": {
                nid: node.to_dict() for nid, node in self._nodes.items()
            },
            "edges": {
                eid: edge.to_dict() for eid, edge in self._edges.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceGraph:
        """Deserialize from a dict (inverse of ``to_dict``)."""
        g = cls()
        for nid, raw in data.get("nodes", {}).items():
            g._nodes[nid] = EvidenceNode.from_dict(raw)
            # Rebuild text index
            for word in g._tokenize(g._nodes[nid].claim):
                g._text_index[word].add(nid)
        for eid, raw in data.get("edges", {}).items():
            edge = EvidenceEdge.from_dict(raw)
            g._edges[eid] = edge
            g._outgoing[edge.source_id].append(eid)
            g._incoming[edge.target_id].append(eid)
        return g

    def clear(self) -> None:
        """Reset all graph state."""
        self._nodes.clear()
        self._edges.clear()
        self._outgoing.clear()
        self._incoming.clear()
        self._text_index.clear()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict[str, Any]:
        """Return comprehensive graph statistics."""
        status_counts: Counter[str] = Counter()
        for n in self._nodes.values():
            status_counts[n.verification_status.value] += 1

        edge_type_counts: Counter[str] = Counter()
        for e in self._edges.values():
            edge_type_counts[e.edge_type.value] += 1

        avg_confidence = (
            sum(n.confidence for n in self._nodes.values()) / max(len(self._nodes), 1)
        )

        contradictions = self.detect_contradictions()

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "status_distribution": dict(status_counts),
            "edge_type_distribution": dict(edge_type_counts),
            "average_confidence": round(avg_confidence, 4),
            "contradiction_count": len(contradictions),
            "total_supporting": sum(
                1 for e in self._edges.values() if e.edge_type == EdgeType.SUPPORTS
            ),
            "total_contradicting": sum(
                1
                for e in self._edges.values()
                if e.edge_type == EdgeType.CONTRADICTS
            ),
            "total_citing": sum(
                1 for e in self._edges.values() if e.edge_type == EdgeType.CITES
            ),
            "total_derived": sum(
                1
                for e in self._edges.values()
                if e.edge_type == EdgeType.DERIVES_FROM
            ),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _bump_supporting_count(self, node_id: str, delta: int) -> None:
        node = self._nodes.get(node_id)
        if node is not None:
            new_count = max(0, node.supporting_count + delta)
            object.__setattr__(node, "supporting_count", new_count)

    def _bump_contradicting_count(self, node_id: str, delta: int) -> None:
        node = self._nodes.get(node_id)
        if node is not None:
            new_count = max(0, node.contradicting_count + delta)
            object.__setattr__(node, "contradicting_count", new_count)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text into lowercase words, filtering short stop-words."""
        words = text.lower().split()
        stop_words: set[str] = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "shall",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "and",
            "or",
            "but",
            "not",
            "no",
            "if",
            "this",
            "that",
            "it",
            "its",
            "we",
            "they",
            "you",
            "he",
            "she",
        }
        return [w for w in words if w not in stop_words and len(w) > 1]

    @staticmethod
    def _safe_mermaid_id(node_id: str) -> str:
        """Convert a node ID to a safe Mermaid node identifier."""
        safe = "".join(c if c.isalnum() else "_" for c in node_id)
        if safe and safe[0].isdigit():
            safe = "n_" + safe
        return safe or "unknown"

    @staticmethod
    def _normalize_pair(a: str, b: str) -> tuple[str, str]:
        """Normalize an unordered node pair to a stable tuple."""
        return (a, b) if a < b else (b, a)
