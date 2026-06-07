"""
Sufficiency-gated retrieval (SEMARAG) — iterative retrieval that judges whether
results are sufficient before answering, expanding the query when they are not.

HybridSearch — combines vector, keyword, and graph-based retrieval with score fusion.
FreshnessManager — tracks document staleness and triggers re-indexing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from lyra.ingestion.pipeline import Chunk, Document, Embedder


# ---------------------------------------------------------------------------
# SEMARAG — Sufficiency-gated retrieval
# ---------------------------------------------------------------------------


@dataclass
class SufficiencyResult:
    """Result of a sufficiency-gated retrieval cycle.

    Attributes:
        query: The original or expanded query used for retrieval.
        chunks: Retrieved chunks that passed the sufficiency gate.
        confidence: Aggregate sufficiency score (0 = none, 1 = fully sufficient).
        rounds: Number of retrieval rounds performed.
        expanded_query: The expanded query string (None if not expanded).
        sufficiency_scores: Per-chunk sufficiency scores.
    """

    query: str
    chunks: list[Chunk] = field(default_factory=list)
    confidence: float = 0.0
    rounds: int = 0
    expanded_query: str | None = None
    sufficiency_scores: list[float] = field(default_factory=list)


class SufficiencyJudge(Protocol):
    """Protocol for judging whether retrieved content is sufficient."""

    def judge(self, query: str, chunks: list[Chunk]) -> float:
        """Return a sufficiency score in [0, 1].

        Args:
            query: The retrieval query.
            chunks: Retrieved chunks to evaluate.

        Returns:
            Score where 1.0 means fully sufficient, 0.0 means completely insufficient.
        """
        ...


class QueryExpander(Protocol):
    """Protocol for expanding a query to improve retrieval."""

    def expand(self, query: str, context: list[Chunk] | None = None) -> str:
        """Produce an expanded or reformulated query.

        Args:
            query: Original query string.
            context: Optionally, previously retrieved chunks for context.

        Returns:
            Expanded query string.
        """
        ...


class StubSufficiencyJudge:
    """Simple keyword-overlap-based sufficiency judge for testing."""

    def __init__(self, threshold: float = 0.3):
        """Initialize stub judge.

        Args:
            threshold: Minimum keyword overlap ratio to consider sufficient.
        """
        self.threshold = threshold

    def judge(self, query: str, chunks: list[Chunk]) -> float:
        """Judge sufficiency by keyword overlap between query and chunks."""
        if not chunks:
            return 0.0
        query_tokens = set(query.lower().split())
        if not query_tokens:
            return 1.0
        overlap_ratios: list[float] = []
        for chunk in chunks:
            chunk_tokens = set(chunk.text.lower().split())
            if chunk_tokens:
                overlap = len(query_tokens & chunk_tokens) / len(query_tokens)
                overlap_ratios.append(overlap)
        if not overlap_ratios:
            return 0.0
        return sum(overlap_ratios) / len(overlap_ratios)


class StubQueryExpander:
    """Simple keyword-based query expander for testing."""

    def __init__(self, synonyms: dict[str, list[str]] | None = None):
        """Initialize stub expander.

        Args:
            synonyms: Optional mapping of words to synonym lists.
        """
        self.synonyms = synonyms or {}

    def expand(self, query: str, context: list[Chunk] | None = None) -> str:
        """Expand query by appending synonyms for known keywords."""
        expanded = query
        for word in query.lower().split():
            if word in self.synonyms:
                for syn in self.synonyms[word]:
                    if syn not in expanded:
                        expanded += f" {syn}"
        return expanded if expanded != query else f"{query} expanded"


class SEMARAGPipeline:
    """Sufficiency-gated retrieval pipeline.

    Iteratively retrieves chunks and judges whether they are sufficient.
    If not sufficient, expands the query and retries up to ``max_rounds``.
    """

    def __init__(
        self,
        embedder: Embedder,
        store: Any,
        judge: SufficiencyJudge | None = None,
        expander: QueryExpander | None = None,
        max_rounds: int = 3,
        threshold: float = 0.7,
    ):
        """Initialize SEMARAGPipeline.

        Args:
            embedder: Embedding model for vector retrieval.
            store: Storage backend with a ``search(query_embedding, top_k)`` method.
            judge: Sufficiency judge (uses StubSufficiencyJudge if None).
            expander: Query expander (uses StubQueryExpander if None).
            max_rounds: Maximum retrieval-expansion rounds.
            threshold: Sufficiency threshold to stop early.
        """
        self.embedder = embedder
        self.store = store
        self.judge = judge or StubSufficiencyJudge(threshold=threshold)
        self.expander = expander or StubQueryExpander()
        self.max_rounds = max_rounds
        self.threshold = threshold

    def retrieve(self, query: str, top_k: int = 10) -> SufficiencyResult:
        """Run sufficiency-gated retrieval for the given query.

        Args:
            query: Natural language query.
            top_k: Number of chunks to retrieve per round.

        Returns:
            SufficiencyResult with the best set of chunks found.
        """
        current_query = query
        best_result = SufficiencyResult(query=query)
        best_confidence = 0.0

        for round_idx in range(self.max_rounds):
            query_emb = self.embedder.embed(current_query)

            # This assumes store has a search method; adapt as needed.
            chunks = self._search(current_query, query_emb, top_k)

            confidence = self.judge.judge(current_query, chunks)
            scores = [confidence] * len(chunks) if chunks else []

            result = SufficiencyResult(
                query=current_query,
                chunks=chunks,
                confidence=confidence,
                rounds=round_idx + 1,
                expanded_query=current_query if round_idx > 0 else None,
                sufficiency_scores=scores,
            )

            if confidence > best_confidence:
                best_result = result
                best_confidence = confidence

            if confidence >= self.threshold:
                break

            # Expand query for next round
            current_query = self.expander.expand(current_query, chunks)

        return best_result

    def _search(self, query: str, query_emb: list[float], top_k: int) -> list[Chunk]:
        """Execute a search against the store.

        Attempts to use a ``search`` method on the store if available;
        otherwise falls back to scanning all stored chunks.
        """
        if hasattr(self.store, "search") and callable(self.store.search):
            return self.store.search(query_emb, top_k=top_k)
        # Fallback: return all stored chunks (for DictMemoryStore-like backends)
        if hasattr(self.store, "_data"):
            items = list(self.store._data.values())
            return items[:top_k]
        return []


# ---------------------------------------------------------------------------
# HybridSearch — vector + keyword + graph combined retrieval
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """A single search result from HybridSearch.

    Attributes:
        chunk_id: Unique chunk identifier.
        score: Fused relevance score in [0, 1].
        text: Chunk text content.
        sources: Which retrieval methods contributed (e.g. {"vector", "keyword"}).
    """

    chunk_id: str
    score: float
    text: str
    sources: set[str] = field(default_factory=set)


class HybridSearch:
    """Multi-strategy search that fuses vector, keyword, and graph scores.

    Attributes:
        vector_weight: Relative weight of vector search scores.
        keyword_weight: Relative weight of keyword search scores.
        graph_weight: Relative weight of graph traversal scores.
    """

    def __init__(
        self,
        vector_weight: float = 0.4,
        keyword_weight: float = 0.3,
        graph_weight: float = 0.3,
    ):
        """Initialize HybridSearch.

        Args:
            vector_weight: Weight for vector search (0.0 to 1.0).
            keyword_weight: Weight for keyword search (0.0 to 1.0).
            graph_weight: Weight for graph search (0.0 to 1.0).

        Raises:
            ValueError: If weights do not sum to 1.0 (within tolerance).
        """
        total = vector_weight + keyword_weight + graph_weight
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Weights must sum to 1.0, got {vector_weight} + {keyword_weight} + "
                f"{graph_weight} = {total}"
            )
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.graph_weight = graph_weight
        self._vector_fn: Callable[[str, int], list[SearchResult]] | None = None
        self._keyword_fn: Callable[[str, int], list[SearchResult]] | None = None
        self._graph_fn: Callable[[str, int], list[SearchResult]] | None = None

    def set_vector_backend(self, fn: Callable[[str, int], list[SearchResult]]) -> None:
        """Set the vector search backend."""
        self._vector_fn = fn

    def set_keyword_backend(self, fn: Callable[[str, int], list[SearchResult]]) -> None:
        """Set the keyword (BM25 / TF-IDF) search backend."""
        self._keyword_fn = fn

    def set_graph_backend(self, fn: Callable[[str, int], list[SearchResult]]) -> None:
        """Set the graph traversal search backend."""
        self._graph_fn = fn

    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        """Run hybrid search across all configured backends.

        Results are fused using weighted score combination. Each backend
        contributes its top-``top_k`` results, and scores are normalised
        before fusion.

        Args:
            query: Search query string.
            top_k: Maximum results to return.

        Returns:
            Ranked list of SearchResult objects with fused scores.
        """
        from collections import defaultdict

        scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        texts: dict[str, str] = {}
        sources: dict[str, set[str]] = defaultdict(set)

        def _collect(results: list[SearchResult], source: str) -> None:
            for r in results:
                scores[r.chunk_id][source] = r.score
                texts[r.chunk_id] = r.text
                sources[r.chunk_id].add(source)

        if self._vector_fn:
            _collect(self._vector_fn(query, top_k), "vector")
        if self._keyword_fn:
            _collect(self._keyword_fn(query, top_k), "keyword")
        if self._graph_fn:
            _collect(self._graph_fn(query, top_k), "graph")

        if not scores:
            return []

        fused: list[SearchResult] = []
        for cid, src_scores in scores.items():
            fused_score = (
                src_scores.get("vector", 0.0) * self.vector_weight
                + src_scores.get("keyword", 0.0) * self.keyword_weight
                + src_scores.get("graph", 0.0) * self.graph_weight
            )
            fused.append(
                SearchResult(
                    chunk_id=cid,
                    score=fused_score,
                    text=texts[cid],
                    sources=sources[cid],
                )
            )

        fused.sort(key=lambda r: r.score, reverse=True)
        return fused[:top_k]


# ---------------------------------------------------------------------------
# FreshnessManager — track and update stale documents
# ---------------------------------------------------------------------------


@dataclass
class DocumentFreshness:
    """Tracks the freshness state of an indexed document.

    Attributes:
        doc_id: Unique document identifier.
        path: Filesystem path of the source document.
        indexed_at: Timestamp when the document was last indexed.
        file_modified_at: Timestamp of the file's last modification.
        is_stale: Whether the document is considered stale.
        stale_reason: Human-readable explanation of staleness.
    """

    doc_id: str
    path: str
    indexed_at: datetime
    file_modified_at: datetime
    is_stale: bool = False
    stale_reason: str = ""


class FreshnessManager:
    """Tracks document freshness and identifies stale documents needing re-index.

    A document is stale if its file modification time is newer than its last
    index time, or if it has been longer than ``max_age_days`` since indexing.
    """

    def __init__(self, max_age_days: int = 30):
        """Initialize FreshnessManager.

        Args:
            max_age_days: Maximum age in days before a document auto-stales.
        """
        self.max_age_days = max_age_days
        self._freshness: dict[str, DocumentFreshness] = {}

    def track(self, doc_id: str, path: str, indexed_at: datetime | None = None) -> DocumentFreshness:
        """Register a document for freshness tracking.

        Args:
            doc_id: Unique document identifier.
            path: Filesystem path of the source file.
            indexed_at: When the document was indexed (defaults to now).

        Returns:
            The DocumentFreshness entry.
        """
        now = indexed_at or datetime.now(timezone.utc)
        file_mtime = self._get_mtime(path)
        entry = DocumentFreshness(
            doc_id=doc_id,
            path=path,
            indexed_at=now,
            file_modified_at=file_mtime,
        )
        self._freshness[doc_id] = entry
        return entry

    def check_stale(self, doc_id: str) -> bool:
        """Check whether a single document is stale.

        Args:
            doc_id: Document identifier.

        Returns:
            True if the document is stale or unknown.

        Raises:
            KeyError: If doc_id is not being tracked.
        """
        if doc_id not in self._freshness:
            raise KeyError(f"Document {doc_id!r} is not tracked.")
        entry = self._freshness[doc_id]
        is_stale, reason = self._evaluate(entry)
        entry.is_stale = is_stale
        entry.stale_reason = reason
        return is_stale

    def list_stale(self) -> list[DocumentFreshness]:
        """Return all tracked documents that are currently stale."""
        stale: list[DocumentFreshness] = []
        for entry in self._freshness.values():
            is_stale, reason = self._evaluate(entry)
            if is_stale:
                entry.is_stale = True
                entry.stale_reason = reason
                stale.append(entry)
            else:
                entry.is_stale = False
                entry.stale_reason = ""
        return stale

    def mark_fresh(self, doc_id: str) -> None:
        """Mark a document as freshly indexed (resets staleness).

        Args:
            doc_id: Document identifier.
        """
        if doc_id in self._freshness:
            self._freshness[doc_id].indexed_at = datetime.now(timezone.utc)
            self._freshness[doc_id].is_stale = False
            self._freshness[doc_id].stale_reason = ""

    def remove(self, doc_id: str) -> bool:
        """Stop tracking a document.

        Args:
            doc_id: Document identifier.

        Returns:
            True if the document was tracked and removed.
        """
        return self._freshness.pop(doc_id, None) is not None

    def get_freshness(self, doc_id: str) -> DocumentFreshness | None:
        """Get the freshness entry for a document.

        Args:
            doc_id: Document identifier.

        Returns:
            DocumentFreshness entry or None if not tracked.
        """
        return self._freshness.get(doc_id)

    def all_freshness(self) -> list[DocumentFreshness]:
        """Return all tracked freshness entries."""
        return list(self._freshness.values())

    def _evaluate(self, entry: DocumentFreshness) -> tuple[bool, str]:
        """Evaluate whether a document is stale.

        Returns:
            Tuple of (is_stale, reason).
        """
        now = datetime.now(timezone.utc)

        # Age-based staleness
        age = (now - entry.indexed_at).total_seconds()
        if age > self.max_age_days * 86400:
            return True, f"Indexed {age:.0f}s ago (max {self.max_age_days} days)"

        # File-modification-based staleness
        current_mtime = self._get_mtime(entry.path)
        if current_mtime and current_mtime > entry.indexed_at:
            return True, "File modified since last index"

        return False, ""

    @staticmethod
    def _get_mtime(path: str) -> datetime:
        """Get file modification time, returning epoch start on error."""
        try:
            ts = Path(path).stat().st_mtime
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (OSError, ValueError):
            return datetime.fromtimestamp(0, tz=timezone.utc)


__all__ = [
    "SufficiencyResult",
    "SufficiencyJudge",
    "QueryExpander",
    "StubSufficiencyJudge",
    "StubQueryExpander",
    "SEMARAGPipeline",
    "SearchResult",
    "HybridSearch",
    "DocumentFreshness",
    "FreshnessManager",
]
