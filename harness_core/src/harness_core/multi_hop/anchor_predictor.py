"""AnchorRAG-style anchor predictor for ambiguous entity linking.

AnchorRAG (arXiv:2509.01238) handles open-world KGQA where entity-mention
strings don't map cleanly to a single graph node. Three-agent pipeline:
Predictor (proposes candidates) → Retrievers (parallel multi-hop expansion) →
Supervisor (selects/merges/answers).

This module ships the **Predictor** as a reusable primitive. Production wires
an LLM-backed predictor through the :class:`AnchorPredictor` Protocol; tests
use the zero-dep :class:`TokenOverlapAnchorPredictor` (token-overlap +
prefix-match) as the cold-start fallback.

Per [docs/200-graph-grounded-multi-hop-retrieval.md](../../../../../../research/harness-engineering/docs/200-graph-grounded-multi-hop-retrieval.md)
§"AnchorRAG" and the per-project apply plans (Polaris [203], Atlas [218],
Helix [219], Cipher [221]) — anchor prediction is the Tier-1 fix when entity
linking is imperfect.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Optional, Protocol

from .types import Graph

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-_]{1,}")


@dataclass(frozen=True, order=True)
class AnchorCandidate:
    """One candidate anchor node with confidence + reason.

    Ordered by ``-confidence`` so ``sorted(candidates)`` returns most-likely
    first. (Reverse via ``score`` for descending sort.)
    """

    score: float  # negation of confidence for sort order
    confidence: float
    node_id: str
    reason: str = ""

    @classmethod
    def make(cls, *, node_id: str, confidence: float, reason: str = "") -> "AnchorCandidate":
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {confidence}")
        return cls(score=-confidence, confidence=confidence, node_id=node_id, reason=reason)


class AnchorPredictor(Protocol):
    """Predict ranked anchor-node candidates for a query."""

    name: str

    def predict(self, query: str, *, graph: Graph, top_k: int = 5) -> list[AnchorCandidate]: ...


# --- Default zero-dep predictor -------------------------------------------


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _has_prefix_match(query_tokens: set[str], target_tokens: set[str], min_len: int = 4) -> bool:
    """True if any query token is a prefix of a target token (or vice versa).

    Useful for entity disambiguation (e.g., "BRCA" prefix-matches "BRCA1").
    """
    for q in query_tokens:
        if len(q) < min_len:
            continue
        for t in target_tokens:
            if t.startswith(q) or q.startswith(t):
                return True
    return False


@dataclass
class TokenOverlapAnchorPredictor:
    """Zero-dep anchor predictor: Jaccard + prefix-match over node titles.

    For each node:
        confidence = max(jaccard(query, title), 0.6 * prefix_hit + 0.2 * id_overlap)

    >>> from harness_core.multi_hop.types import SimpleGraph, SimpleNode
    >>> g = SimpleGraph()
    >>> g.add_node(SimpleNode(id="brca1", title="BRCA1 gene"))
    >>> g.add_node(SimpleNode(id="brca2", title="BRCA2 gene"))
    >>> g.add_node(SimpleNode(id="tp53", title="TP53 tumor suppressor"))
    >>> p = TokenOverlapAnchorPredictor()
    >>> hits = p.predict("BRCA mutations", graph=g, top_k=5)
    >>> sorted({h.node_id for h in hits})
    ['brca1', 'brca2']
    """

    name: str = "token-overlap-anchor-predictor-v1"
    min_confidence: float = 0.05

    def predict(self, query: str, *, graph: Graph, top_k: int = 5) -> list[AnchorCandidate]:
        if not query.strip():
            return []
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        candidates: list[AnchorCandidate] = []
        for node in graph.all_nodes():
            title_tokens = _tokenize(node.title or "")
            id_tokens = _tokenize(node.id)

            jaccard = _jaccard(query_tokens, title_tokens)
            prefix_hit = (
                _has_prefix_match(query_tokens, title_tokens)
                or _has_prefix_match(query_tokens, id_tokens)
            )
            id_overlap = _jaccard(query_tokens, id_tokens)

            score = max(jaccard, 0.6 * (1.0 if prefix_hit else 0.0) + 0.2 * id_overlap)
            if score < self.min_confidence:
                continue

            reason_parts = []
            if jaccard > 0:
                reason_parts.append(f"jaccard={jaccard:.2f}")
            if prefix_hit:
                reason_parts.append("prefix-match")
            if id_overlap > 0:
                reason_parts.append(f"id-overlap={id_overlap:.2f}")
            reason = ", ".join(reason_parts) or "weak signal"

            candidates.append(
                AnchorCandidate.make(node_id=node.id, confidence=min(1.0, score), reason=reason)
            )

        # Sort: dataclass(order=True) on negated confidence → ascending = best-first.
        candidates.sort()
        return candidates[:top_k]


@dataclass
class FixedAnchorPredictor:
    """Stub predictor returning a fixed list of (node_id, confidence) pairs.

    Useful for tests + as a way to inject a known anchor set into the pipeline.
    """

    fixed: list[tuple[str, float]] = field(default_factory=list)
    name: str = "fixed-anchor-predictor"

    def predict(self, query: str, *, graph: Graph, top_k: int = 5) -> list[AnchorCandidate]:
        out: list[AnchorCandidate] = []
        for node_id, confidence in self.fixed:
            if node_id in graph:
                out.append(
                    AnchorCandidate.make(
                        node_id=node_id, confidence=confidence, reason="fixed predictor"
                    )
                )
        out.sort()
        return out[:top_k]


def merge_predictors(
    predictors: Iterable[AnchorPredictor],
    *,
    query: str,
    graph: Graph,
    top_k: int = 5,
    weights: Optional[list[float]] = None,
) -> list[AnchorCandidate]:
    """Merge multiple predictors; per-node confidence = weighted-max.

    Useful in production: stack a fast cheap predictor (token-overlap) with a
    slower expensive one (LLM) and merge by max confidence.
    """
    pred_list = list(predictors)
    if weights is None:
        weights = [1.0] * len(pred_list)
    if len(weights) != len(pred_list):
        raise ValueError("weights length must match predictors length")

    by_node: dict[str, AnchorCandidate] = {}
    for predictor, weight in zip(pred_list, weights):
        for cand in predictor.predict(query, graph=graph, top_k=top_k * 2):
            adj_conf = min(1.0, cand.confidence * weight)
            existing = by_node.get(cand.node_id)
            if existing is None or adj_conf > existing.confidence:
                by_node[cand.node_id] = AnchorCandidate.make(
                    node_id=cand.node_id,
                    confidence=adj_conf,
                    reason=f"merged: {predictor.name}",
                )
    merged = list(by_node.values())
    merged.sort()
    return merged[:top_k]


__all__ = [
    "AnchorCandidate",
    "AnchorPredictor",
    "FixedAnchorPredictor",
    "TokenOverlapAnchorPredictor",
    "merge_predictors",
]
