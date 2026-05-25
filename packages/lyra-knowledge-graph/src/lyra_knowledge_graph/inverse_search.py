"""Backward chaining from conclusions — find supporting and refuting evidence paths.

Enables inverse search: given a conclusion, trace back through the graph
to find all paths that support or refute it. Provides hypothesis scoring
and counter-claim generation.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HypothesisScore:
    """Aggregate evidence score for a hypothesis."""
    claim: str
    supporting_paths: int = 0
    refuting_paths: int = 0
    total_evidence: float = 0.0
    net_score: float = 0.0
    confidence: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "supporting_paths": self.supporting_paths,
            "refuting_paths": self.refuting_paths,
            "total_evidence": self.total_evidence,
            "net_score": self.net_score,
            "confidence": self.confidence,
            "details": dict(self.details),
        }


class InverseSearchEngine:
    """Backward chaining engine — trace from conclusions to evidence.

    Given a graph and a conclusion/claim, find all evidence paths
    that lead to (support) or contradict (refute) the conclusion.
    """

    def __init__(self, graph: Any) -> None:
        self._graph = graph

    # ── Path Discovery ─────────────────────────────────────────────────────

    def find_supporting_paths(self, conclusion: str,
                              graph: Any | None = None,
                              max_depth: int = 6) -> list[list[dict[str, Any]]]:
        """Find all paths that support a conclusion.

        Traverses incoming edges looking for SUPPORTS, CITES, EXTENDS,
        and DEPENDS_ON relations.
        """
        return self._find_paths_by_relation(
            conclusion, graph or self._graph, max_depth,
            {"supports", "cites", "extends", "depends_on"},
        )

    def find_refuting_paths(self, conclusion: str,
                            graph: Any | None = None,
                            max_depth: int = 6) -> list[list[dict[str, Any]]]:
        """Find all paths that refute/contradict a conclusion.

        Traverses incoming edges looking for REFUTES relations.
        """
        return self._find_paths_by_relation(
            conclusion, graph or self._graph, max_depth,
            {"refutes"},
        )

    def _find_paths_by_relation(self, node_id: str,
                                graph: Any,
                                max_depth: int,
                                relations: set[str]) -> list[list[dict[str, Any]]]:
        """Generic backward traversal following specific relation types."""
        if node_id not in graph.nodes:
            return []

        paths: list[list[dict[str, Any]]] = []

        def dfs(current: str, target: str, path: list[dict[str, Any]],
                visited: set[str], depth: int) -> None:
            if depth > max_depth:
                return
            try:
                incoming = graph.get_incoming_edges(current)
            except Exception:
                return

            for edge in incoming:
                if edge.relation.value not in relations:
                    continue
                step = {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "relation": edge.relation.value,
                    "confidence": edge.confidence,
                }
                # Check if this is a direct support for the conclusion
                if edge.source_id == target:
                    paths.append(path + [step])
                elif edge.source_id not in visited:
                    visited.add(edge.source_id)
                    path.append(step)
                    dfs(edge.source_id, target, path, visited, depth + 1)
                    path.pop()
                    visited.discard(edge.source_id)

        dfs(node_id, node_id, [], {node_id}, 0)
        return paths

    # ── Hypothesis Scoring ─────────────────────────────────────────────────

    def score_hypothesis(self, claim_node_id: str,
                         evidence_graph: Any | None = None) -> HypothesisScore:
        """Aggregate evidence for a claim and produce a HypothesisScore."""
        graph = evidence_graph or self._graph
        if claim_node_id not in graph.nodes:
            return HypothesisScore(
                claim=claim_node_id,
                confidence=0.0,
                details={"error": f"Claim node '{claim_node_id}' not found in graph"},
            )

        supporting = self.find_supporting_paths(claim_node_id, graph)
        refuting = self.find_refuting_paths(claim_node_id, graph)

        total_support_confidence = sum(
            step.get("confidence", 1.0) for path in supporting for step in path
        ) if supporting else 0.0

        total_refute_confidence = sum(
            step.get("confidence", 1.0) for path in refuting for step in path
        ) if refuting else 0.0

        total_evidence = total_support_confidence + total_refute_confidence
        net = total_support_confidence - total_refute_confidence

        if total_evidence > 0:
            # Normalize to -1..1, then map to 0..1 confidence
            normalized = net / total_evidence if total_evidence > 0 else 0.0
            confidence = (normalized + 1.0) / 2.0
        else:
            confidence = 0.5  # No evidence = neutral

        return HypothesisScore(
            claim=claim_node_id,
            supporting_paths=len(supporting),
            refuting_paths=len(refuting),
            total_evidence=total_evidence,
            net_score=net,
            confidence=confidence,
            details={
                "supporting_path_count": len(supporting),
                "refuting_path_count": len(refuting),
                "supporting_confidence_sum": total_support_confidence,
                "refuting_confidence_sum": total_refute_confidence,
                "claim_label": graph.nodes[claim_node_id].label
                if claim_node_id in graph.nodes else claim_node_id,
            },
        )

    # ── Counter-Claims ─────────────────────────────────────────────────────

    def generate_counter_claims(self, claim_node_id: str,
                                max_count: int = 5) -> list[str]:
        """Generate alternative explanations or counter-claims.

        Uses graph structure to find contradictory or alternative paths.
        Returns text descriptions of counter-claims.
        """
        graph = self._graph
        if claim_node_id not in graph.nodes:
            return []

        claim_node = graph.nodes[claim_node_id]
        counters: list[str] = []

        # Strategy 1: Find nodes that refute via direct edges
        refuting = self.find_refuting_paths(claim_node_id)
        for path in refuting:
            for step in path:
                src_id = step["source_id"]
                if src_id in graph.nodes:
                    src_node = graph.nodes[src_id]
                    counters.append(
                        f"'{src_node.label}' contradicts '{claim_node.label}' "
                        f"(confidence: {step['confidence']:.2f})"
                    )
                    if len(counters) >= max_count:
                        return counters

        # Strategy 2: Find siblings with opposite relations
        try:
            incoming = graph.get_incoming_edges(claim_node_id)
        except Exception:
            incoming = []

        shared_sources: dict[str, list[Any]] = defaultdict(list)
        for edge in incoming:
            shared_sources[edge.source_id].append(edge)

        for src_id, edges in shared_sources.items():
            relations_found = {e.relation.value for e in edges}
            if "supports" in relations_found and "refutes" in relations_found:
                if src_id in graph.nodes:
                    src_node = graph.nodes[src_id]
                    counters.append(
                        f"'{src_node.label}' both supports and refutes "
                        f"'{claim_node.label}' (contradictory source)"
                    )
                    if len(counters) >= max_count:
                        return counters

        # Strategy 3: Find supporting chain for a refuting claim
        if refuting:
            for path in refuting:
                for step in path:
                    alt_support = self.find_supporting_paths(step["source_id"])
                    if alt_support:
                        counters.append(
                            f"Refuting path via '{step['source_id']}' is supported "
                            f"by {len(alt_support)} evidence chains"
                        )
                        if len(counters) >= max_count:
                            return counters

        return counters

    # ── Graph Statistics ──────────────────────────────────────────────────

    def get_citation_count(self, node_id: str) -> int:
        """Count how many CITES edges point to a node."""
        if node_id not in self._graph.nodes:
            return 0
        return sum(
            1 for e in self._graph.get_incoming_edges(node_id)
            if e.relation.value == "cites"
        )

    def get_support_score(self, node_id: str) -> float:
        """Compute a support score: (supports - refutes) / total evidence edges."""
        if node_id not in self._graph.nodes:
            return 0.0
        incoming = self._graph.get_incoming_edges(node_id)
        supports = sum(1 for e in incoming if e.relation.value == "supports")
        refutes = sum(1 for e in incoming if e.relation.value == "refutes")
        total = supports + refutes
        if total == 0:
            return 0.0
        return (supports - refutes) / total
