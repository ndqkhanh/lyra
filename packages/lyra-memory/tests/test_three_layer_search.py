"""Tests for the 3-Layer Memory Search pattern."""
from __future__ import annotations

import pytest

from lyra_memory.search import (
    InMemorySearchBackend,
    Observation,
    SearchHit,
    SearchResult,
    ThreeLayerSearch,
    ThreeLayerSearchConfig,
    TimelineEntry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_obs(obs_id: str, title: str, content: str, created_at: float = 0.0) -> Observation:
    return Observation(
        id=obs_id,
        title=title,
        content=content,
        created_at=created_at,
        tags=["test"],
        source="test",
    )


def _populate_backend(backend: InMemorySearchBackend) -> None:
    backend.add(_make_obs("1", "Python patterns", "Python design patterns for agent development", 10.0))
    backend.add(_make_obs("2", "Memory systems", "Memory architecture with KV-cache and vector stores", 20.0))
    backend.add(_make_obs("3", "Voice pipeline", "Full-duplex voice pipeline with VAD and STT", 30.0))
    backend.add(_make_obs("4", "Hook system", "Hook pipeline expansion from 3 to 50 events", 40.0))
    backend.add(_make_obs("5", "Memory consolidation", "Dream cycle consolidation for long-term memory", 50.0))
    backend.add(_make_obs("6", "Provider routing", "Multi-provider abstraction with circuit breaker failover", 60.0))
    backend.add(_make_obs("7", "Python tooling", "Python developer tools and automation patterns", 70.0))
    backend.add(_make_obs("8", "Memory search", "Three-layer progressive memory search pattern", 80.0))


# ---------------------------------------------------------------------------
# InMemorySearchBackend
# ---------------------------------------------------------------------------


class TestInMemorySearchBackend:
    def test_add_and_size(self):
        backend = InMemorySearchBackend()
        assert backend.size == 0
        backend.add(_make_obs("1", "Test", "Hello world"))
        assert backend.size == 1

    def test_remove(self):
        backend = InMemorySearchBackend()
        backend.add(_make_obs("1", "Test", "Hello"))
        backend.remove("1")
        assert backend.size == 0

    def test_clear(self):
        backend = InMemorySearchBackend()
        backend.add(_make_obs("1", "T1", "C1"))
        backend.add(_make_obs("2", "T2", "C2"))
        backend.clear()
        assert backend.size == 0

    def test_search_returns_matches(self):
        backend = InMemorySearchBackend()
        _populate_backend(backend)
        hits = backend.search("memory", limit=10)
        assert len(hits) > 0
        assert all("memory" in h.snippet.lower() or "memory" in h.title.lower() for h in hits)

    def test_search_respects_limit(self):
        backend = InMemorySearchBackend()
        _populate_backend(backend)
        hits = backend.search("python", limit=1)
        assert len(hits) <= 1

    def test_search_scores_descending(self):
        backend = InMemorySearchBackend()
        _populate_backend(backend)
        hits = backend.search("memory")
        scores = [h.score for h in hits]
        assert scores == sorted(scores, reverse=True)

    def test_search_empty_query_returns_empty(self):
        backend = InMemorySearchBackend()
        _populate_backend(backend)
        hits = backend.search("")
        assert hits == []

    def test_search_no_match_returns_empty(self):
        backend = InMemorySearchBackend()
        backend.add(_make_obs("1", "X", "Y"))
        hits = backend.search("zzzz_nonexistent_query_term")
        assert hits == []

    def test_search_snippet_truncation(self):
        backend = InMemorySearchBackend()
        long_content = "word " * 250  # > 200 chars
        backend.add(_make_obs("1", "Test", long_content))
        hits = backend.search("word")
        assert len(hits) == 1
        assert len(hits[0].snippet) <= 200

    def test_timeline_returns_context(self):
        backend = InMemorySearchBackend()
        _populate_backend(backend)
        entries = backend.timeline("4", depth_before=2, depth_after=1)
        # Order: 2, 3, 4(anchor), 5
        assert len(entries) > 0
        offsets = [e.anchor_offset for e in entries]
        assert 0 in offsets  # anchor is present

    def test_timeline_missing_anchor(self):
        backend = InMemorySearchBackend()
        entries = backend.timeline("nonexistent")
        assert entries == []

    def test_timeline_clamps_at_start(self):
        backend = InMemorySearchBackend()
        _populate_backend(backend)
        entries = backend.timeline("1", depth_before=10, depth_after=2)
        offsets = [e.anchor_offset for e in entries]
        assert min(offsets) >= -1  # can't go before start

    def test_get_observations(self):
        backend = InMemorySearchBackend()
        _populate_backend(backend)
        obs = backend.get_observations(["1", "5"])
        assert len(obs) == 2
        assert {o.id for o in obs} == {"1", "5"}

    def test_get_observations_missing_ids(self):
        backend = InMemorySearchBackend()
        backend.add(_make_obs("1", "T", "C"))
        obs = backend.get_observations(["1", "999"])
        assert len(obs) == 1
        assert obs[0].id == "1"


# ---------------------------------------------------------------------------
# ThreeLayerSearch orchestrator
# ---------------------------------------------------------------------------


class TestThreeLayerSearch:
    @pytest.fixture
    def backend(self):
        b = InMemorySearchBackend()
        _populate_backend(b)
        return b

    @pytest.fixture
    def search(self, backend):
        return ThreeLayerSearch(backend)

    def test_layer1_search_returns_result(self, search):
        result = search.layer1_search("memory")
        assert isinstance(result, SearchResult)
        assert result.query == "memory"
        assert len(result.hits) > 0
        assert result.tokens_saved > 0

    def test_layer1_search_respects_config_limit(self, backend):
        search = ThreeLayerSearch(backend, ThreeLayerSearchConfig(search_limit=2))
        result = search.layer1_search("python")
        assert len(result.hits) <= 2

    def test_layer1_search_min_score_filter(self, backend):
        search = ThreeLayerSearch(backend, ThreeLayerSearchConfig(min_score=1.0))
        result = search.layer1_search("memory")
        # Only exact matches would score 1.0
        assert all(h.score >= 1.0 for h in result.hits)

    def test_layer2_timeline(self, search):
        entries = search.layer2_timeline("4")
        assert isinstance(entries, list)
        assert all(isinstance(e, TimelineEntry) for e in entries)

    def test_layer3_fetch(self, search):
        obs = search.layer3_fetch(["1", "2"])
        assert len(obs) == 2
        assert all(isinstance(o, Observation) for o in obs)

    def test_layer3_fetch_unknown_ids(self, search):
        obs = search.layer3_fetch(["nonexistent"])
        assert obs == []

    def test_last_hits_cached(self, search):
        search.layer1_search("python memory")
        assert len(search.last_hits) > 0

    def test_full_pipeline(self, search):
        result = search.full_pipeline("memory", fetch_ids=["2", "5"], anchor_id="2")
        assert len(result.hits) > 0
        assert len(result.timeline) > 0
        assert len(result.observations) == 2
        assert result.tokens_saved >= 0
        assert "layer1_hits" in result.layer_stats
        assert "layer3_fetched" in result.layer_stats

    def test_full_pipeline_layer1_only(self, search):
        result = search.full_pipeline("hook system")
        assert len(result.hits) > 0
        assert result.timeline == []
        assert result.observations == []

    def test_auto_fetch_top(self, backend):
        search = ThreeLayerSearch(backend, ThreeLayerSearchConfig(auto_fetch_top=2))
        result = search.layer1_search("memory")
        assert len(result.observations) == 2

    def test_tokens_saved_positive(self, search):
        result = search.layer1_search("memory")
        assert result.tokens_saved > 0


# ---------------------------------------------------------------------------
# SearchHit, TimelineEntry, Observation — data integrity
# ---------------------------------------------------------------------------


class TestDataTypes:
    def test_search_hit_defaults(self):
        hit = SearchHit(id="x", score=0.5)
        assert hit.title == ""
        assert hit.snippet == ""
        assert hit.metadata == {}

    def test_timeline_entry_fields(self):
        te = TimelineEntry(id="a", anchor_offset=0, title="T", snippet="S", timestamp=1.0)
        assert te.anchor_offset == 0
        assert te.title == "T"

    def test_observation_fields(self):
        obs = Observation(
            id="o1",
            content="full content here",
            title="Title",
            created_at=100.0,
            tags=["tag1"],
            source="test",
        )
        assert obs.content == "full content here"
        assert obs.tags == ["tag1"]


# ---------------------------------------------------------------------------
# ThreeLayerSearchConfig
# ---------------------------------------------------------------------------


class TestConfig:
    def test_defaults(self):
        cfg = ThreeLayerSearchConfig()
        assert cfg.search_limit == 20
        assert cfg.timeline_depth == 3
        assert cfg.min_score == 0.0
        assert cfg.auto_fetch_top == 0

    def test_custom(self):
        cfg = ThreeLayerSearchConfig(
            search_limit=5, timeline_depth=10, min_score=0.3, auto_fetch_top=3
        )
        assert cfg.search_limit == 5
        assert cfg.auto_fetch_top == 3
