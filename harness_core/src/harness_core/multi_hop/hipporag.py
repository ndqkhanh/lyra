"""HippoRAG-2 — Personalized PageRank + dense embedding fusion.

Promoted from ``polaris-core/memory/ppr_fusion.py`` (v2.5 P42) per
[docs/211-cross-project-power-up-plan-with-tradeoffs.md] §9 milestone M3.
The original is tightly coupled to Polaris's ``ProgramGraph`` and ``Claim``;
this version uses :mod:`.types` Protocols so it runs on any graph + document
substrate.

HippoRAG 2 (arXiv:2502.14802, ICML 2025) shows that combining KG PPR + dense
embeddings sweeps factual + multi-hop + sense-making benchmarks simultaneously
in a single retrieval pass. The PPR walk is seeded by query-extracted entity
anchors; the fusion mixes cosine similarity with normalised PPR weights.
"""
from __future__ import annotations

import hashlib
import math
import re
import struct
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Protocol, Sequence

from .types import Document, Graph, Node

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-_]{2,}")


# --- Protocols (caller-injectable production wires) ----------------------


class Embedder(Protocol):
    """Minimal embedder protocol; production wires BGE-M3 / Voyage / OpenAI."""

    name: str
    dim: int

    def embed_batch(self, texts: Sequence[str]) -> List[List[float]]: ...


class EntityExtractor(Protocol):
    """Map a query string → list of graph node ids."""

    name: str

    def extract(self, query: str, *, graph: Graph) -> tuple[str, ...]: ...


# --- Helpers --------------------------------------------------------------


def _normalize(vec: Sequence[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return list(vec)
    return [v / norm for v in vec]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


# --- Stub implementations (zero-dep defaults) -----------------------------


@dataclass
class HashEmbedder:
    """Deterministic hash-based embedder for tests + cold-start.

    Uses unigram + 4-char prefix + 6-char prefix + bigram hashes into a fixed
    dim. No ML deps; identical input → identical output → reproducible tests.
    """

    dim: int = 256
    name: str = "hash-embedder-v1"

    def embed_batch(self, texts: Sequence[str]) -> List[List[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> List[float]:
        text = (text or "").lower()
        vec = [0.0] * self.dim
        for word in text.split():
            for tok in (word, word[:4], word[:6]):
                if not tok:
                    continue
                vec[self._hash_to_idx(tok)] += 1.0
        compact = "".join(c for c in text if c.isalnum())
        for i in range(len(compact) - 1):
            vec[self._hash_to_idx(compact[i : i + 2])] += 0.5
        return _normalize(vec)

    def _hash_to_idx(self, token: str) -> int:
        h = hashlib.sha1(token.encode("utf-8")).digest()
        return struct.unpack(">I", h[:4])[0] % self.dim


@dataclass
class TitleEntityExtractor:
    """Extract entity ids by token-matching the query against node titles.

    Default extractor — zero-dependency. LLM-backed entity linkers (e.g. an
    AnchorRAG anchor predictor) drop in via the Protocol; this is the
    cold-start fallback.
    """

    name: str = "title-entity-extractor-v1"

    def extract(self, query: str, *, graph: Graph) -> tuple[str, ...]:
        if not query.strip():
            return ()
        query_tokens = {t.lower() for t in _TOKEN_RE.findall(query)}
        if not query_tokens:
            return ()
        matched: list[str] = []
        for node in graph.all_nodes():
            title_tokens = {t.lower() for t in _TOKEN_RE.findall(node.title or "")}
            if query_tokens & title_tokens:
                matched.append(node.id)
            elif query_tokens & {t.lower() for t in _TOKEN_RE.findall(node.id)}:
                matched.append(node.id)
        return tuple(matched)


# --- PPR walk -------------------------------------------------------------


@dataclass
class PersonalizedPageRank:
    """Sparse-iteration PPR over a directed adjacency dict.

    Operates on adjacency dicts so the same algorithm runs over any graph
    substrate that conforms to :class:`.types.Graph`. Convergence: typically
    <20 iterations for graphs up to 10K nodes.
    """

    alpha: float = 0.15  # teleport probability
    max_iters: int = 30
    tol: float = 1e-6

    def walk(
        self,
        *,
        adjacency: dict[str, list[str]],
        seeds: Sequence[str],
    ) -> dict[str, float]:
        """Run PPR seeded at ``seeds``; return per-node weight."""
        if not adjacency:
            return {}
        nodes = list(adjacency.keys())
        if not seeds:
            seed_set = set(nodes)  # uniform restart = global PageRank
        else:
            seed_set = {s for s in seeds if s in adjacency}
            if not seed_set:
                seed_set = set(nodes)  # seeds didn't match — fall back uniform
        seed_weight = 1.0 / len(seed_set)
        teleport = {node: (seed_weight if node in seed_set else 0.0) for node in nodes}
        rank = dict(teleport)

        inv_out_degree = {
            node: (1.0 / len(adjacency[node]) if adjacency[node] else 0.0)
            for node in nodes
        }
        in_neighbours: dict[str, list[str]] = {node: [] for node in nodes}
        for src, dsts in adjacency.items():
            for dst in dsts:
                if dst in in_neighbours:
                    in_neighbours[dst].append(src)

        for _ in range(self.max_iters):
            new_rank: dict[str, float] = {}
            delta = 0.0
            for node in nodes:
                inflow = sum(
                    rank[src] * inv_out_degree[src] for src in in_neighbours[node]
                )
                new_value = self.alpha * teleport[node] + (1 - self.alpha) * inflow
                new_rank[node] = new_value
                delta += abs(new_value - rank[node])
            rank = new_rank
            if delta < self.tol:
                break
        return rank


def graph_to_adjacency(graph: Graph) -> dict[str, list[str]]:
    """Convert a :class:`.types.Graph` to PPR-walk adjacency dict.

    Edges are *directed* (src → dst); for symmetric similarity we add the
    reverse direction so PPR walks reach back-references. Orphan edges
    (whose endpoints aren't in the node set) are silently dropped.
    """
    adj: dict[str, list[str]] = {n.id: [] for n in graph.all_nodes()}
    for edge in graph.all_edges():
        if edge.src in adj and edge.dst in adj:
            adj[edge.src].append(edge.dst)
            adj[edge.dst].append(edge.src)
    return adj


# --- The retriever --------------------------------------------------------


@dataclass(frozen=True)
class RetrievalResult:
    """One ranked document from a HippoRAG retrieval call."""

    document: Document
    score: float
    cosine_score: float = 0.0
    ppr_score: float = 0.0
    reason: str = ""


@dataclass
class HippoRAGRetriever:
    """HippoRAG-2: PPR walk over the graph + dense cosine over docs.

    Built once (``build_index``); queried many times (``retrieve``).
    Re-build when the graph mutates or the embedding model upgrades.

    >>> from harness_core.multi_hop.types import SimpleGraph, SimpleDocument
    >>> g = SimpleGraph.from_pairs([("alice", "bob"), ("bob", "casablanca")])
    >>> r = HippoRAGRetriever(graph=g)
    >>> r.build_index([SimpleDocument(doc_id="d1", text="alice married bob",
    ...                                anchor_node_id="alice"),
    ...                SimpleDocument(doc_id="d2", text="bob directed casablanca",
    ...                                anchor_node_id="bob")])
    >>> hits = r.retrieve("who directed casablanca", top_k=2)
    >>> [h.document.doc_id for h in hits]  # bob is the bridge entity
    ['d2', 'd1']
    """

    graph: Graph
    embedder: Embedder = field(default_factory=HashEmbedder)
    entity_extractor: EntityExtractor = field(default_factory=TitleEntityExtractor)
    ppr: PersonalizedPageRank = field(default_factory=PersonalizedPageRank)
    alpha: float = 0.5  # cosine vs PPR mix; 1.0 = pure dense, 0.0 = pure PPR

    _docs_by_id: dict[str, Document] = field(default_factory=dict, init=False)
    _doc_embeddings: dict[str, List[float]] = field(default_factory=dict, init=False)
    _doc_anchors: dict[str, tuple[str, ...]] = field(default_factory=dict, init=False)
    _adjacency: dict[str, list[str]] = field(default_factory=dict, init=False)

    def build_index(self, docs: Iterable[Document]) -> None:
        """Embed every document and compute its anchor nodes."""
        self._docs_by_id = {}
        self._doc_embeddings = {}
        self._doc_anchors = {}
        doc_list = list(docs)
        self._adjacency = graph_to_adjacency(self.graph)
        if not doc_list:
            return
        embeddings = self.embedder.embed_batch([d.text for d in doc_list])
        for doc, embedding in zip(doc_list, embeddings):
            self._docs_by_id[doc.doc_id] = doc
            self._doc_embeddings[doc.doc_id] = _normalize(embedding)
            anchors: list[str] = []
            anchor = getattr(doc, "anchor_node_id", None)
            if anchor and anchor in self.graph:
                anchors.append(anchor)
            extracted = self.entity_extractor.extract(doc.text, graph=self.graph)
            for nid in extracted:
                if nid not in anchors:
                    anchors.append(nid)
            self._doc_anchors[doc.doc_id] = tuple(anchors)

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> List[RetrievalResult]:
        """Run HippoRAG retrieval. Returns top-K ranked documents."""
        if not self._docs_by_id:
            return []

        # 1. Embed the query.
        query_embedding = _normalize(self.embedder.embed_batch([query])[0])

        # 2. PPR walk seeded by query entities.
        seeds = self.entity_extractor.extract(query, graph=self.graph)
        ppr_weights = self.ppr.walk(adjacency=self._adjacency, seeds=seeds)

        # Normalise PPR weights to [0, 1] so fusion is balanced with cosine.
        max_ppr = max(ppr_weights.values()) if ppr_weights else 0.0
        if max_ppr > 0:
            ppr_weights = {k: v / max_ppr for k, v in ppr_weights.items()}

        # 3. Score every doc.
        scored: List[RetrievalResult] = []
        for doc_id, doc in self._docs_by_id.items():
            embedding = self._doc_embeddings.get(doc_id, [])
            cosine_score = cosine(query_embedding, embedding)
            anchors = self._doc_anchors.get(doc_id, ())
            ppr_score = max(
                (ppr_weights.get(anchor, 0.0) for anchor in anchors),
                default=0.0,
            )
            score = self.alpha * cosine_score + (1 - self.alpha) * ppr_score
            if score < min_score:
                continue
            scored.append(
                RetrievalResult(
                    document=doc,
                    score=score,
                    cosine_score=cosine_score,
                    ppr_score=ppr_score,
                    reason=f"alpha={self.alpha} cos={cosine_score:.3f} ppr={ppr_score:.3f}",
                )
            )

        scored.sort(key=lambda r: (-r.score, r.document.doc_id))
        return scored[:top_k]


__all__ = [
    "Embedder",
    "EntityExtractor",
    "HashEmbedder",
    "HippoRAGRetriever",
    "PersonalizedPageRank",
    "RetrievalResult",
    "TitleEntityExtractor",
    "cosine",
    "graph_to_adjacency",
]
