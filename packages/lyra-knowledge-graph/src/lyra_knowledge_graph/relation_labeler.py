"""Confidence-tagged relationship labeling for knowledge graph edges.

Labels edges as EXTRACTED (from explicit source), INFERRED (from reasoning),
or AMBIGUOUS (uncertain). Provides confidence scoring and label propagation.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EdgeLabel(Enum):
    """Confidence categories for edge provenance."""
    EXTRACTED = "extracted"
    INFERRED = "inferred"
    AMBIGUOUS = "ambiguous"

    @property
    def base_confidence(self) -> float:
        if self == EdgeLabel.EXTRACTED:
            return 0.9
        if self == EdgeLabel.INFERRED:
            return 0.6
        return 0.3


@dataclass(frozen=True)
class LabeledEdge:
    """An edge with a provenance label and confidence score."""
    source_id: str
    target_id: str
    relation_type: str
    label: EdgeLabel
    confidence: float
    properties: dict[str, Any] = field(default_factory=dict)
    evidence: str = ""


class RelationLabeler:
    """Classify and score relationships between entities in a graph.

    Assigns EXTRACTED / INFERRED / AMBIGUOUS labels based on available
    evidence, and can propagate labels across connected nodes.
    """

    def __init__(self) -> None:
        self._relation_keywords: dict[str, list[str]] = {
            "supports": [
                "confirms", "validates", "proves", "demonstrates", "shows",
                "indicates", "suggests", "implies", "supports", "reinforces",
            ],
            "refutes": [
                "contradicts", "disproves", "invalidates", "refutes", "challenges",
                "opposes", "counters", "disputes", "negates",
            ],
            "cites": [
                "references", "quotes", "cites", "mentions", "notes", "states",
            ],
            "depends_on": [
                "requires", "depends on", "needs", "prerequisite", "builds upon",
                "extends", "inherits from",
            ],
            "relates_to": [
                "relates to", "associated with", "connected to", "linked to",
                "corresponds to", "similar to",
            ],
            "extends": [
                "extends", "expands", "enhances", "augments", "builds on",
                "generalizes", "specializes",
            ],
        }

    # ── Labeling ────────────────────────────────────────────────────────────

    def label_edge(self, source_label: str, target_label: str,
                   context: str = "", source_confidence: float = 1.0) -> LabeledEdge:
        """Create a LabeledEdge by analyzing the relationship context.

        The relation type is inferred from keyword matching in the
        optional context string. Confidence combines source confidence
        with label base confidence.
        """
        relation_type = self._classify_relation(context)
        label = self._determine_label(source_confidence, bool(context), relation_type)
        confidence = self._score_confidence(label, source_confidence, context)
        return LabeledEdge(
            source_id="",
            target_id="",
            relation_type=relation_type,
            label=label,
            confidence=confidence,
            properties={"relation_type": relation_type},
            evidence=context,
        )

    def label_batch(self, pairs: list[tuple[str, str, str, float]]) -> list[LabeledEdge]:
        """Label multiple (source, target, context, confidence) pairs."""
        return [
            self.label_edge(src, tgt, ctx, conf)
            for src, tgt, ctx, conf in pairs
        ]

    # ── Propagation ─────────────────────────────────────────────────────────

    def propagate_labels(self, graph: Any) -> dict[str, EdgeLabel]:
        """Propagate labels across connected nodes using BFS.

        Returns a dict mapping node_id to the propagated label.
        Nodes reached only via INFERRED edges get INFERRED label;
        nodes with at least one EXTRACTED path get EXTRACTED.
        """
        propagated: dict[str, EdgeLabel] = {}
        # Start from all nodes that have an EXTRACTED incoming edge
        frontier: list[str] = []
        for edge in graph.edges:
            props = getattr(edge, "properties", {})
            label_str = props.get("label", "ambiguous")
            if label_str == "extracted":
                propagated[edge.target_id] = EdgeLabel.EXTRACTED
                frontier.append(edge.target_id)

        visited = set(frontier)
        while frontier:
            current = frontier.pop(0)
            try:
                neighbors = graph.get_neighbors(current)
            except Exception:
                continue
            for nbr in neighbors:
                if nbr.node_id not in visited:
                    visited.add(nbr.node_id)
                    if current in propagated:
                        propagated[nbr.node_id] = EdgeLabel.INFERRED
                        frontier.append(nbr.node_id)

        # Remaining unlabeled nodes are AMBIGUOUS
        for nid in graph.nodes:
            if nid not in propagated:
                propagated[nid] = EdgeLabel.AMBIGUOUS

        return propagated

    # ── Classification ──────────────────────────────────────────────────────

    def classify_relation_type(self, text: str) -> str:
        """Classify the relation type from text context."""
        return self._classify_relation(text)

    def get_confidence(self, source_confidence: float,
                       context_present: bool) -> float:
        """Compute combined confidence for a relation."""
        label = self._determine_label(source_confidence, context_present, "relates_to")
        return self._score_confidence(label, source_confidence,
                                      "context" if context_present else "")

    # ── Internal ────────────────────────────────────────────────────────────

    def _classify_relation(self, context: str) -> str:
        """Classify relation type by keyword matching."""
        if not context:
            return "relates_to"
        lower = context.lower()
        scores: dict[str, int] = defaultdict(int)
        for rtype, keywords in self._relation_keywords.items():
            for kw in keywords:
                if kw in lower:
                    scores[rtype] += 1
        if not scores:
            return "relates_to"
        return max(scores, key=scores.get)

    def _determine_label(self, source_confidence: float,
                         has_context: bool,
                         relation_type: str) -> EdgeLabel:
        """Determine the provenance label for an edge."""
        if source_confidence >= 0.8 and has_context:
            return EdgeLabel.EXTRACTED
        if source_confidence >= 0.5 or has_context:
            return EdgeLabel.INFERRED
        return EdgeLabel.AMBIGUOUS

    def _score_confidence(self, label: EdgeLabel,
                          source_confidence: float,
                          context: str) -> float:
        """Compute final confidence as weighted combination."""
        base = label.base_confidence
        context_boost = 0.1 if context else 0.0
        raw = base * 0.6 + source_confidence * 0.3 + context_boost
        return min(raw, 1.0)
