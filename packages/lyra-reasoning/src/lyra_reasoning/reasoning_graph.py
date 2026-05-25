"""
Reasoning Graph — Persistent Chain-of-Thought Graph for Cross-Session Learning.

Structures CoT reasoning as a directed graph of evidence nodes connected by
typed relations (supports, contradicts, refines, derives_from), enabling
pattern mining, contradiction detection, and cross-session reasoning
consolidation.
"""

from __future__ import annotations

import copy
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

__all__ = [
    "EvidenceNode",
    "ReasoningEdge",
    "ReasoningGraph",
]

_VALID_EVIDENCE_TYPES = frozenset({"fact", "assumption", "inference", "observation"})
_VALID_RELATIONS = frozenset({"supports", "contradicts", "refines", "derives_from"})


@dataclass(frozen=True)
class EvidenceNode:
    """A single evidence node in the reasoning graph.

    Attributes:
        node_id: Unique identifier for this node.
        claim: The textual claim or statement.
        evidence_type: One of ``fact``, ``assumption``, ``inference``,
            or ``observation``.
        confidence: Confidence score in the range ``[0.0, 1.0]``.
        sources: Tuple of source identifiers (e.g. file paths, document IDs).
        timestamp: Unix timestamp of when this node was created.
    """

    node_id: str
    claim: str
    evidence_type: str = "observation"
    confidence: float = 0.5
    sources: Tuple[str, ...] = field(default_factory=tuple)
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self: EvidenceNode) -> None:
        """Validate field values after initialisation."""
        if self.evidence_type not in _VALID_EVIDENCE_TYPES:
            raise ValueError(
                f"Invalid evidence_type {self.evidence_type!r}; "
                f"must be one of {sorted(_VALID_EVIDENCE_TYPES)}"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0.0, 1.0], got {self.confidence}"
            )


@dataclass(frozen=True)
class ReasoningEdge:
    """A directed relation between two evidence nodes.

    Attributes:
        edge_id: Unique identifier for this edge.
        from_node: The ``node_id`` of the source node.
        to_node: The ``node_id`` of the target node.
        relation: The type of relation — one of ``supports``,
            ``contradicts``, ``refines``, or ``derives_from``.
        strength: Relation strength in the range ``[0.0, 1.0]``.
        explanation: Human-readable explanation for this edge.
    """

    edge_id: str
    from_node: str
    to_node: str
    relation: str = "supports"
    strength: float = 0.5
    explanation: str = ""

    def __post_init__(self: ReasoningEdge) -> None:
        """Validate field values after initialisation."""
        if self.relation not in _VALID_RELATIONS:
            raise ValueError(
                f"Invalid relation {self.relation!r}; "
                f"must be one of {sorted(_VALID_RELATIONS)}"
            )
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(
                f"strength must be in [0.0, 1.0], got {self.strength}"
            )


class ReasoningGraph:
    """A directed graph that structures reasoning as typed evidence relations.

    Supports graph-based chain-of-thought persistence, contradiction detection,
    pattern mining, and cross-session graph merging.
    """

    def __init__(self: ReasoningGraph) -> None:
        self._nodes: Dict[str, EvidenceNode] = {}
        self._edges: Dict[str, ReasoningEdge] = {}
        self._outgoing: Dict[str, List[str]] = defaultdict(list)
        self._incoming: Dict[str, List[str]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_node(self: ReasoningGraph, node: EvidenceNode) -> str:
        """Add an evidence node.

        Returns:
            The ``node_id`` of the added node.

        Raises:
            ValueError: If a node with the same ID already exists.
        """
        if node.node_id in self._nodes:
            raise ValueError(f"Node {node.node_id!r} already exists in the graph")
        self._nodes[node.node_id] = node
        return node.node_id

    def add_edge(self: ReasoningGraph, edge: ReasoningEdge) -> str:
        """Add a reasoning edge between two existing nodes.

        Returns:
            The ``edge_id`` of the added edge.

        Raises:
            ValueError: If the edge already exists, or if the referenced
                nodes do not exist.
        """
        if edge.edge_id in self._edges:
            raise ValueError(f"Edge {edge.edge_id!r} already exists in the graph")
        if edge.from_node not in self._nodes:
            raise ValueError(f"Source node {edge.from_node!r} not found")
        if edge.to_node not in self._nodes:
            raise ValueError(f"Target node {edge.to_node!r} not found")

        self._edges[edge.edge_id] = edge
        self._outgoing[edge.from_node].append(edge.edge_id)
        self._incoming[edge.to_node].append(edge.edge_id)
        return edge.edge_id

    # ------------------------------------------------------------------
    # Query utilities
    # ------------------------------------------------------------------

    def get_node(self: ReasoningGraph, node_id: str) -> Optional[EvidenceNode]:
        """Look up a node by ID, returning ``None`` if absent."""
        return self._nodes.get(node_id)

    def get_edge(self: ReasoningGraph, edge_id: str) -> Optional[ReasoningEdge]:
        """Look up an edge by ID, returning ``None`` if absent."""
        return self._edges.get(edge_id)

    def get_support_chain(self: ReasoningGraph, node_id: str) -> List[EvidenceNode]:
        """Walk the graph to discover all evidence that supports *node_id*.

        Performs a backward traversal following ``supports`` and ``refines``
        edges (directed *toward* the queried node), collecting nodes that
        constitute the evidential chain.  Duplicates are excluded.

        Returns:
            A list of ``EvidenceNode`` instances in traversal order
            (deepest ancestor first).
        """
        if node_id not in self._nodes:
            return []

        visited: Set[str] = set()
        queue: deque = deque()
        queue.append(node_id)
        visited.add(node_id)

        while queue:
            current = queue.popleft()
            for edge_id in self._incoming.get(current, []):
                edge = self._edges[edge_id]
                if edge.relation in ("supports", "refines"):
                    src = edge.from_node
                    if src not in visited:
                        visited.add(src)
                        queue.append(src)

        # Return all visited nodes *except* the queried node itself
        return [self._nodes[nid] for nid in visited if nid != node_id]

    def get_contradictions(self: ReasoningGraph, node_id: str) -> List[EvidenceNode]:
        """Find nodes that contradict the claim made by *node_id*.

        Traverses ``contradicts`` edges in both directions — a node may
        contradict *node_id*, or *node_id* may contradict another node.

        Returns:
            A list of ``EvidenceNode`` instances that stand in contradiction.
        """
        if node_id not in self._nodes:
            return []

        contradicting: Set[str] = set()

        for edge_id in self._outgoing.get(node_id, []):
            edge = self._edges[edge_id]
            if edge.relation == "contradicts":
                contradicting.add(edge.to_node)

        for edge_id in self._incoming.get(node_id, []):
            edge = self._edges[edge_id]
            if edge.relation == "contradicts":
                contradicting.add(edge.from_node)

        return [self._nodes[nid] for nid in contradicting]

    # ------------------------------------------------------------------
    # Pattern mining
    # ------------------------------------------------------------------

    def find_patterns(self: ReasoningGraph) -> List[Dict[str, Any]]:
        """Mine common reasoning subgraph structures.

        Currently detects three pattern types:

        - ``observation→inference→conclusion`` chains (2-hop via
          ``derives_from`` / ``supports``)
        - ``contradiction_pairs`` (direct ``contradicts`` edges)
        - ``refinement_chains`` (3+ nodes linked by ``refines``)

        Returns:
            A list of dictionaries with keys ``pattern_type``, ``frequency``,
            and ``example_node_ids``.
        """
        patterns: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        # --- Pattern 1: observation → inference → conclusion ---
        chain_count = 0
        chain_examples: List[str] = []
        for nid, node in self._nodes.items():
            if node.evidence_type != "observation":
                continue
            for eid in self._outgoing.get(nid, []):
                edge = self._edges[eid]
                if edge.relation not in ("derives_from", "supports"):
                    continue
                mid = edge.to_node
                mid_node = self._nodes.get(mid)
                if mid_node is None or mid_node.evidence_type != "inference":
                    continue
                for eid2 in self._outgoing.get(mid, []):
                    edge2 = self._edges[eid2]
                    if edge2.relation not in ("derives_from", "supports"):
                        continue
                    tid = edge2.to_node
                    tgt_node = self._nodes.get(tid)
                    if tgt_node is not None and tgt_node.evidence_type == "conclusion":
                        chain_count += 1
                        key = f"{nid}:{mid}:{tid}"
                        if key not in seen:
                            seen.add(key)
                            if len(chain_examples) < 3:
                                chain_examples = [nid, mid, tid]

        if chain_count > 0:
            patterns.append({
                "pattern_type": "observation_inference_conclusion",
                "frequency": chain_count,
                "example_node_ids": chain_examples,
            })

        # --- Pattern 2: contradiction pairs ---
        contradiction_pairs = 0
        contradiction_examples: List[str] = []
        for eid, edge in self._edges.items():
            if edge.relation == "contradicts":
                contradiction_pairs += 1
                if len(contradiction_examples) < 3:
                    contradiction_examples = [edge.from_node, edge.to_node]

        if contradiction_pairs > 0:
            patterns.append({
                "pattern_type": "contradiction_pair",
                "frequency": contradiction_pairs,
                "example_node_ids": contradiction_examples,
            })

        # --- Pattern 3: refinement chains (3+ nodes via refines) ---
        refinement_chains = 0
        refinement_examples: List[str] = []
        visited_edges: Set[str] = set()

        for start_nid in self._nodes:
            if start_nid in visited_edges:
                continue
            chain: List[str] = []
            cur = start_nid
            while cur:
                next_nid: Optional[str] = None
                for eid in self._outgoing.get(cur, []):
                    edge = self._edges[eid]
                    if edge.relation == "refines":
                        next_nid = edge.to_node
                        visited_edges.add(cur)
                        break
                if next_nid is None:
                    break
                if not chain:
                    chain.append(cur)
                chain.append(next_nid)
                cur = next_nid

            if len(chain) >= 3:
                refinement_chains += 1
                if len(refinement_examples) < 3:
                    refinement_examples = chain[:3]

        if refinement_chains > 0:
            patterns.append({
                "pattern_type": "refinement_chain",
                "frequency": refinement_chains,
                "example_node_ids": refinement_examples,
            })

        return patterns

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def prune_weak(self: ReasoningGraph, confidence_threshold: float = 0.3) -> int:
        """Remove nodes below *confidence_threshold* and dangling edges.

        Nodes whose ``confidence`` field is strictly below the threshold are
        removed along with all edges that reference them.  Edges whose
        ``from_node`` or ``to_node`` no longer exist are also removed.

        Returns:
            The total number of removed nodes.
        """
        to_remove: Set[str] = {
            nid for nid, node in self._nodes.items()
            if node.confidence < confidence_threshold
        }

        # Remove weak nodes
        for nid in to_remove:
            self._remove_node_edges(nid)
            del self._nodes[nid]

        # Remove dangling edges (orphaned from_node or to_node)
        dangling = [
            eid for eid, edge in self._edges.items()
            if edge.from_node not in self._nodes or edge.to_node not in self._nodes
        ]
        for eid in dangling:
            edge = self._edges[eid]
            self._remove_edge_from_index(edge)
            del self._edges[eid]

        return len(to_remove)

    def _remove_node_edges(self: ReasoningGraph, node_id: str) -> None:
        """Remove all edges connected to *node_id*."""
        for eid in list(self._outgoing.get(node_id, [])):
            edge = self._edges.pop(eid, None)
            if edge is not None:
                self._remove_edge_from_index(edge)
        for eid in list(self._incoming.get(node_id, [])):
            edge = self._edges.pop(eid, None)
            if edge is not None:
                self._remove_edge_from_index(edge)
        self._outgoing.pop(node_id, None)
        self._incoming.pop(node_id, None)

    def _remove_edge_from_index(self: ReasoningGraph, edge: ReasoningEdge) -> None:
        """Remove an edge from the adjacency indexes."""
        out_list = self._outgoing.get(edge.from_node)
        if out_list is not None and edge.edge_id in out_list:
            out_list.remove(edge.edge_id)
        in_list = self._incoming.get(edge.to_node)
        if in_list is not None and edge.edge_id in in_list:
            in_list.remove(edge.edge_id)

    # ------------------------------------------------------------------
    # Graph merging
    # ------------------------------------------------------------------

    def merge_graphs(self: ReasoningGraph, other: ReasoningGraph) -> ReasoningGraph:
        """Combine two reasoning graphs, deduplicating similar nodes.

        Two nodes are considered duplicates when they share the same
        ``evidence_type`` and their ``claim`` strings have a Jaccard-like
        word overlap >= 0.7.  In case of a duplicate, the node with the
        higher confidence is kept.

        Returns:
            A new ``ReasoningGraph`` containing the merged result.
            The original graphs are not mutated.
        """
        merged = ReasoningGraph()
        merged._nodes = copy.deepcopy(self._nodes)
        merged._edges = copy.deepcopy(self._edges)

        # Rebuild adjacency for the copy
        merged._rebuild_adjacency()

        # Track node_id remapping for edges coming from ``other``
        remap: Dict[str, str] = {}

        for nid, node in other._nodes.items():
            dup = merged._find_duplicate(node)
            if dup is not None:
                # Keep the higher-confidence node
                if node.confidence > merged._nodes[dup].confidence:
                    merged._nodes[dup] = node
                remap[nid] = dup
            else:
                # Fresh ID to avoid collisions
                new_id = f"{nid}__merged"
                merged._nodes[new_id] = node
                remap[nid] = new_id

        # Copy edges with remapped node IDs
        for eid, edge in other._edges.items():
            new_from = remap.get(edge.from_node, edge.from_node)
            new_to = remap.get(edge.to_node, edge.to_node)
            new_eid = f"{eid}__merged"
            new_edge = ReasoningEdge(
                edge_id=new_eid,
                from_node=new_from,
                to_node=new_to,
                relation=edge.relation,
                strength=edge.strength,
                explanation=edge.explanation,
            )
            merged._edges[new_eid] = new_edge
            merged._outgoing[new_from].append(new_eid)
            merged._incoming[new_to].append(new_eid)

        return merged

    def _rebuild_adjacency(self: ReasoningGraph) -> None:
        """Rebuild outgoing/incoming indexes from the stored edges."""
        self._outgoing.clear()
        self._incoming.clear()
        for eid, edge in self._edges.items():
            self._outgoing[edge.from_node].append(eid)
            self._incoming[edge.to_node].append(eid)

    def _find_duplicate(self: ReasoningGraph, node: EvidenceNode) -> Optional[str]:
        """Find a node in this graph similar to *node*, or return ``None``."""
        for nid, existing in self._nodes.items():
            if existing.evidence_type != node.evidence_type:
                continue
            if self._word_overlap(existing.claim, node.claim) >= 0.7:
                return nid
        return None

    @staticmethod
    def _word_overlap(a: str, b: str) -> float:
        """Jaccard-like word overlap between two strings."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a and not words_b:
            return 1.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self: ReasoningGraph) -> Dict[str, Any]:
        """Serialize the graph to a JSON-compatible dictionary.

        Returns:
            A dict with ``nodes`` and ``edges`` keys.
        """
        return {
            "nodes": {
                nid: {
                    "node_id": node.node_id,
                    "claim": node.claim,
                    "evidence_type": node.evidence_type,
                    "confidence": node.confidence,
                    "sources": list(node.sources),
                    "timestamp": node.timestamp,
                }
                for nid, node in self._nodes.items()
            },
            "edges": {
                eid: {
                    "edge_id": edge.edge_id,
                    "from_node": edge.from_node,
                    "to_node": edge.to_node,
                    "relation": edge.relation,
                    "strength": edge.strength,
                    "explanation": edge.explanation,
                }
                for eid, edge in self._edges.items()
            },
        }

    @classmethod
    def from_dict(cls: type[ReasoningGraph], data: Dict[str, Any]) -> ReasoningGraph:
        """Deserialize a graph from a dictionary produced by :meth:`to_dict`.

        Args:
            data: A dict with ``nodes`` and ``edges`` keys.

        Returns:
            A new ``ReasoningGraph`` instance.
        """
        graph = cls()
        for nid, ndata in data.get("nodes", {}).items():
            node = EvidenceNode(
                node_id=ndata["node_id"],
                claim=ndata["claim"],
                evidence_type=ndata.get("evidence_type", "observation"),
                confidence=ndata.get("confidence", 0.5),
                sources=tuple(ndata.get("sources", [])),
                timestamp=ndata.get("timestamp", time.time()),
            )
            graph._nodes[nid] = node

        for eid, edata in data.get("edges", {}).items():
            edge = ReasoningEdge(
                edge_id=edata["edge_id"],
                from_node=edata["from_node"],
                to_node=edata["to_node"],
                relation=edata.get("relation", "supports"),
                strength=edata.get("strength", 0.5),
                explanation=edata.get("explanation", ""),
            )
            graph._edges[eid] = edge

        graph._rebuild_adjacency()
        return graph

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self: ReasoningGraph) -> Dict[str, Any]:
        """Compute aggregate statistics for the graph.

        Returns:
            A dictionary with keys ``total_nodes``, ``total_edges``,
            ``avg_confidence``, ``pattern_count``, and
            ``contradiction_count``.
        """
        total_nodes = len(self._nodes)
        total_edges = len(self._edges)
        avg_confidence = (
            sum(n.confidence for n in self._nodes.values()) / total_nodes
            if total_nodes > 0
            else 0.0
        )
        patterns = self.find_patterns()
        pattern_count = len(patterns)
        contradiction_count = sum(
            1 for e in self._edges.values() if e.relation == "contradicts"
        )
        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "avg_confidence": round(avg_confidence, 4),
            "pattern_count": pattern_count,
            "contradiction_count": contradiction_count,
        }
