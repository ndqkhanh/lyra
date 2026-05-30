"""3-Layer Memory Search — 10x token savings through progressive retrieval.

Inspired by the claude-mem search pattern:
  1. search(query)      → Lightweight index with IDs and scores
  2. timeline(anchor)   → Context around interesting results
  3. get_observations() → Full details only for filtered IDs

The key insight: most search results never need full details fetched.
Only results that pass filtering criteria expand to full observations.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class SearchHit:
    """Lightweight search result — returned by Layer 1 (search)."""

    id: str
    score: float
    title: str = ""
    snippet: str = ""  # short preview (~100 chars)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TimelineEntry:
    """Context entry around an anchor — returned by Layer 2 (timeline)."""

    id: str
    anchor_offset: int  # 0 = the anchor itself, negative = before, positive = after
    title: str = ""
    snippet: str = ""
    timestamp: float = 0.0


@dataclass
class Observation:
    """Full memory observation — returned by Layer 3 (get_observations)."""

    id: str
    content: str
    title: str = ""
    created_at: float = 0.0
    tags: list[str] = field(default_factory=list)
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Search backend protocol
# ---------------------------------------------------------------------------


class SearchBackend:
    """Protocol-like base for the underlying search engine.

    Implementations wrap: in-memory dict, SQLite FTS5, pgvector, etc.
    """

    def search(self, query: str, limit: int = 20) -> list[SearchHit]:
        raise NotImplementedError

    def timeline(
        self, anchor_id: str, depth_before: int = 3, depth_after: int = 3
    ) -> list[TimelineEntry]:
        raise NotImplementedError

    def get_observations(self, ids: Sequence[str]) -> list[Observation]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory backend (default, no dependencies)
# ---------------------------------------------------------------------------


@dataclass
class _IndexedObservation:
    """Internal: observation with pre-built search index fields."""

    observation: Observation
    tokens: set[str]  # tokenized content for simple term-match scoring


class InMemorySearchBackend(SearchBackend):
    """Simple in-memory search backend using term-frequency scoring.

    Suitable for testing and small-to-medium memory stores.
    For production use, swap with pgvector or another vector backend.
    """

    def __init__(self) -> None:
        self._obs: dict[str, _IndexedObservation] = {}
        self._ids: list[str] = []  # insertion-ordered for timeline

    # ------------------------------------------------------------------
    # Data management
    # ------------------------------------------------------------------

    def add(self, obs: Observation) -> None:
        tokens = set(obs.content.lower().split()) | set(obs.title.lower().split())
        self._obs[obs.id] = _IndexedObservation(observation=obs, tokens=tokens)
        self._ids.append(obs.id)

    def remove(self, obs_id: str) -> None:
        self._obs.pop(obs_id, None)
        if obs_id in self._ids:
            self._ids.remove(obs_id)

    def clear(self) -> None:
        self._obs.clear()
        self._ids.clear()

    @property
    def size(self) -> int:
        return len(self._obs)

    # ------------------------------------------------------------------
    # SearchBackend interface
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 20) -> list[SearchHit]:
        query_tokens = set(query.lower().split())
        if not query_tokens:
            return []

        scored: list[tuple[float, _IndexedObservation]] = []
        for idx_obs in self._obs.values():
            overlap = len(query_tokens & idx_obs.tokens)
            if overlap == 0:
                continue
            # TF-IDF-lite: overlap count normalized by observation length
            score = overlap / max(len(idx_obs.tokens), 1)
            if score > 0:
                scored.append((score, idx_obs))

        scored.sort(key=lambda x: x[0], reverse=True)
        hits: list[SearchHit] = []
        for score, idx_obs in scored[:limit]:
            obs = idx_obs.observation
            snippet = obs.content[:200] if len(obs.content) > 200 else obs.content
            hits.append(
                SearchHit(
                    id=obs.id,
                    score=round(score, 4),
                    title=obs.title,
                    snippet=snippet,
                    metadata=dict(obs.metadata),
                )
            )
        return hits

    def timeline(
        self, anchor_id: str, depth_before: int = 3, depth_after: int = 3
    ) -> list[TimelineEntry]:
        if anchor_id not in self._ids:
            return []

        anchor_idx = self._ids.index(anchor_id)
        start = max(0, anchor_idx - depth_before)
        end = min(len(self._ids), anchor_idx + depth_after + 1)

        entries: list[TimelineEntry] = []
        for i in range(start, end):
            obs_id = self._ids[i]
            obs = self._obs[obs_id].observation
            entries.append(
                TimelineEntry(
                    id=obs.id,
                    anchor_offset=i - anchor_idx,
                    title=obs.title,
                    snippet=obs.content[:100] if len(obs.content) > 100 else obs.content,
                    timestamp=obs.created_at,
                )
            )
        return entries

    def get_observations(self, ids: Sequence[str]) -> list[Observation]:
        return [
            self._obs[oid].observation
            for oid in ids
            if oid in self._obs
        ]


# ---------------------------------------------------------------------------
# Three-layer orchestrator
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """Aggregated result from a 3-layer search."""

    query: str
    hits: list[SearchHit] = field(default_factory=list)
    timeline: list[TimelineEntry] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    tokens_saved: int = 0  # estimated token savings vs fetching all
    layer_stats: dict[str, int] = field(default_factory=dict)


@dataclass
class ThreeLayerSearchConfig:
    """Configuration for the 3-layer search orchestrator."""

    search_limit: int = 20  # max hits from layer 1
    timeline_depth: int = 3  # entries before/after anchor in layer 2
    min_score: float = 0.0  # minimum score to include in results
    auto_fetch_top: int = 0  # auto-fetch this many top hits in layer 3 (0=manual)


class ThreeLayerSearch:
    """Orchestrator for 3-layer progressive memory retrieval.

    Usage pattern::

        search = ThreeLayerSearch(backend)
        result = search.layer1_search("user preferences")
        # result.hits has lightweight index (~50-100 tokens each)
        # Review hits, decide which IDs need context:

        timeline = search.layer2_timeline(anchor_id="mem_42")
        # Get context around the interesting hit

        observations = search.layer3_fetch(["mem_42", "mem_7"])
        # Only fetch full details for the filtered set
    """

    def __init__(
        self,
        backend: SearchBackend,
        config: ThreeLayerSearchConfig | None = None,
    ) -> None:
        self._backend = backend
        self._config = config or ThreeLayerSearchConfig()
        self._last_hits: list[SearchHit] = []

    # ------------------------------------------------------------------
    # Layer 1: Lightweight search
    # ------------------------------------------------------------------

    def layer1_search(self, query: str) -> SearchResult:
        """Search and return lightweight index (IDs, scores, snippets).

        Token cost: ~50-100 tokens per hit vs ~500+ for full observations.
        """
        hits = self._backend.search(query, limit=self._config.search_limit)
        if self._config.min_score > 0:
            hits = [h for h in hits if h.score >= self._config.min_score]
        self._last_hits = hits

        # Estimate tokens saved: each full obs would be ~500 tokens,
        # snippet is ~100 tokens → ~400 tokens saved per hit
        tokens_saved = len(hits) * 400

        result = SearchResult(
            query=query,
            hits=list(hits),
            tokens_saved=tokens_saved,
            layer_stats={"layer1_hits": len(hits)},
        )

        # Auto-fetch top N if configured
        if self._config.auto_fetch_top > 0:
            top_ids = [h.id for h in hits[: self._config.auto_fetch_top]]
            result.observations = self.layer3_fetch(top_ids)
            result.layer_stats["layer3_auto_fetched"] = len(result.observations)

        return result

    # ------------------------------------------------------------------
    # Layer 2: Timeline context
    # ------------------------------------------------------------------

    def layer2_timeline(self, anchor_id: str) -> list[TimelineEntry]:
        """Get timeline context around an anchor observation.

        Returns entries before and after the anchor for context without
        fetching full observation content.
        """
        return self._backend.timeline(
            anchor_id,
            depth_before=self._config.timeline_depth,
            depth_after=self._config.timeline_depth,
        )

    # ------------------------------------------------------------------
    # Layer 3: Full observation fetch
    # ------------------------------------------------------------------

    def layer3_fetch(self, ids: Sequence[str]) -> list[Observation]:
        """Fetch full observations for specific IDs.

        Only call this for IDs that passed filtering in layers 1-2.
        This is the expensive layer — call sparingly.
        """
        return self._backend.get_observations(ids)

    # ------------------------------------------------------------------
    # Convenience: full pipeline
    # ------------------------------------------------------------------

    def full_pipeline(
        self,
        query: str,
        fetch_ids: Sequence[str] | None = None,
        anchor_id: str | None = None,
    ) -> SearchResult:
        """Run the full 3-layer pipeline in one call.

        If fetch_ids is provided, those IDs are fetched in layer 3.
        If anchor_id is provided, timeline context is built in layer 2.
        Otherwise only layer 1 runs.
        """
        result = self.layer1_search(query)

        if anchor_id is not None:
            result.timeline = self.layer2_timeline(anchor_id)
            result.layer_stats["layer2_entries"] = len(result.timeline)

        if fetch_ids is not None:
            result.observations = self.layer3_fetch(fetch_ids)
            result.layer_stats["layer3_fetched"] = len(result.observations)

        # Recalculate token savings
        full_obs_tokens = len(result.hits) * 500
        actual_tokens = (
            len(result.hits) * 100  # snippets
            + len(result.timeline) * 80  # timeline entries
            + len(result.observations) * 500  # full observations
        )
        result.tokens_saved = max(0, full_obs_tokens - actual_tokens)

        return result

    @property
    def last_hits(self) -> list[SearchHit]:
        return list(self._last_hits)
