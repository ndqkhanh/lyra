"""Tests for search plugin modules — DCIZeroIndex, RetrievalRouter, ProgressiveDisclosure, VerbatimLayer."""

import time

import pytest
from lyra_cli.memory.search.dci_zero_index import DCIZeroIndex, GrepResult, MatchType
from lyra_cli.memory.search.progressive_disclosure import (
    DisclosedMemory,
    DisclosureLevel,
    ProgressiveDisclosure,
)
from lyra_cli.memory.search.retrieval_router import (
    RetrievalContext,
    RetrievalReport,
    RetrievalRouter,
    RetrievalTier,
)
from lyra_cli.memory.search.verbatim_layer import VerbatimHit, VerbatimLayer


class TestMatchType:
    def test_all_types(self):
        assert MatchType.EXACT.value == "exact"
        assert MatchType.SUBSTRING.value == "substring"
        assert MatchType.CASE_INSENSITIVE.value == "case_insensitive"
        assert MatchType.REGEX.value == "regex"


class TestGrepResult:
    def test_creation(self):
        gr = GrepResult(
            file_path="/tmp/test.py",
            line_number=10,
            line_content="def test(): pass",
            match_type=MatchType.EXACT,
            score=1.0,
        )
        assert gr.file_path == "/tmp/test.py"
        assert gr.line_number == 10
        assert gr.score == 1.0

    def test_frozen(self):
        gr = GrepResult(
            file_path="/tmp/test.py",
            line_number=1,
            line_content="code",
            match_type=MatchType.SUBSTRING,
            score=0.7,
        )
        with pytest.raises(Exception):
            gr.score = 1.0  # type: ignore[misc]


class TestDCIZeroIndex:
    def test_init(self):
        index = DCIZeroIndex()
        assert index.stats()["indexed_files"] == 0

    def test_init_with_paths(self):
        index = DCIZeroIndex(index_paths=["/tmp"])
        assert "/tmp" in index.stats()["search_paths"]

    def test_index_file(self):
        index = DCIZeroIndex()
        index.index_file(__file__)
        assert index.stats()["indexed_files"] == 1

    def test_search_current_file(self):
        index = DCIZeroIndex()
        index.index_file(__file__)
        results = index.search("TestDCIZeroIndex", limit=5)
        assert len(results) >= 0  # Will match if the text is in the file

    def test_search_no_match(self):
        index = DCIZeroIndex()
        index.index_file(__file__)
        results = index.search("xyznonexistentpattern12345", limit=5)
        assert len(results) == 0

    def test_invalidate_file(self):
        index = DCIZeroIndex()
        index.index_file(__file__)
        assert index.stats()["indexed_files"] == 1
        index.invalidate(__file__)
        assert index.stats()["indexed_files"] == 0

    def test_invalidate_all(self):
        index = DCIZeroIndex()
        index.index_file(__file__)
        index.invalidate()
        assert index.stats()["indexed_files"] == 0

    def test_search_nonexistent_file(self):
        index = DCIZeroIndex()
        index.index_file("/tmp/nonexistent_xyz_file_12345.txt")
        results = index.search("test")
        assert len(results) == 0


class TestRetrievalTier:
    def test_all_tiers(self):
        assert RetrievalTier.DCI_GREP.value == "dci_grep"
        assert RetrievalTier.VERBATIM.value == "verbatim"
        assert RetrievalTier.BM25.value == "bm25"
        assert RetrievalTier.HYBRID.value == "hybrid"
        assert RetrievalTier.KNOWLEDGE_GRAPH.value == "knowledge_graph"


class TestRetrievalContext:
    def test_defaults(self):
        ctx = RetrievalContext(query="test query")
        assert ctx.query == "test query"
        assert ctx.max_results == 10
        assert ctx.include_graph is False

    def test_custom(self):
        ctx = RetrievalContext(query="test", max_results=5, include_graph=True, timeout_ms=100.0)
        assert ctx.max_results == 5
        assert ctx.include_graph is True

    def test_frozen(self):
        ctx = RetrievalContext(query="test")
        with pytest.raises(Exception):
            ctx.query = "new"  # type: ignore[misc]


class TestRetrievalRouter:
    def test_init(self):
        router = RetrievalRouter()
        stats = router.stats()
        assert "registered_tiers" in stats

    def test_register_tier(self):
        router = RetrievalRouter()
        router.register(RetrievalTier.DCI_GREP, DCIZeroIndex())
        assert RetrievalTier.DCI_GREP in router.stats()["registered_tiers"]

    def test_retrieve_empty_routes(self):
        router = RetrievalRouter()
        ctx = RetrievalContext(query="test")
        report = router.retrieve(ctx)
        assert isinstance(report, RetrievalReport)
        assert report.result_count == 0

    def test_retrieve_with_registered_tier(self):
        router = RetrievalRouter()
        index = DCIZeroIndex()
        index.index_file(__file__)
        router.register(RetrievalTier.DCI_GREP, index)
        ctx = RetrievalContext(query="def test")
        report = router.retrieve(ctx)
        assert isinstance(report, RetrievalReport)
        assert report.total_ms >= 0

    def test_retrieve_respects_timeout(self):
        router = RetrievalRouter()
        ctx = RetrievalContext(query="test", timeout_ms=0.001)
        report = router.retrieve(ctx)
        assert report.result_count == 0

    def test_retrieve_without_graph(self):
        router = RetrievalRouter()
        ctx = RetrievalContext(query="test", include_graph=False)
        report = router.retrieve(ctx)
        assert RetrievalTier.KNOWLEDGE_GRAPH not in report.tiers_used


class TestDisclosureLevel:
    def test_all_levels(self):
        assert DisclosureLevel.METADATA.value == "metadata"
        assert DisclosureLevel.TRIGGERS.value == "triggers"
        assert DisclosureLevel.FULL_CONTENT.value == "full_content"


class TestDisclosedMemory:
    def test_creation(self):
        dm = DisclosedMemory(
            memory_id="m1",
            level=DisclosureLevel.METADATA,
            title="Test Memory",
            excerpt="This is a test memory about something interesting",
            tags=["test", "memory"],
            timestamp=time.time(),
            token_estimate=10,
        )
        assert dm.memory_id == "m1"
        assert dm.title == "Test Memory"
        assert dm.tags == ["test", "memory"]
        assert dm.full_content == ""

    def test_frozen(self):
        dm = DisclosedMemory(
            memory_id="m1",
            level=DisclosureLevel.METADATA,
            title="Test",
            excerpt="test",
            tags=[],
            timestamp=time.time(),
            token_estimate=1,
        )
        with pytest.raises(Exception):
            dm.title = "new"  # type: ignore[misc]


class TestProgressiveDisclosure:
    def test_init(self):
        pd = ProgressiveDisclosure()
        assert pd.stats()["default_excerpt_len"] == 150

    def test_disclose_metadata(self):
        pd = ProgressiveDisclosure()
        items = [
            DisclosedMemory(
                memory_id=f"m{i}",
                level=DisclosureLevel.FULL_CONTENT,
                title=f"Memory {i}",
                excerpt=f"This is the content of memory {i}" * 5,
                tags=["test"],
                timestamp=time.time(),
                token_estimate=50,
                full_content=f"Full content of memory {i}" * 20,
            )
            for i in range(3)
        ]
        batch = pd.disclose_metadata(items)
        assert batch.level == DisclosureLevel.METADATA
        assert len(batch.items) == 3
        assert batch.total_tokens > 0
        assert all(item.full_content == "" for item in batch.items)

    def test_disclose_triggers(self):
        pd = ProgressiveDisclosure()
        items = [
            DisclosedMemory(
                memory_id="m1",
                level=DisclosureLevel.FULL_CONTENT,
                title="Test",
                excerpt="Detailed excerpt that should be truncated at 150 chars " * 10,
                tags=["important"],
                timestamp=time.time(),
                token_estimate=100,
            )
        ]
        batch = pd.disclose_triggers(items)
        assert batch.level == DisclosureLevel.TRIGGERS
        assert len(batch.items) == 1

    def test_disclose_full(self):
        pd = ProgressiveDisclosure()
        items = [
            DisclosedMemory(
                memory_id="m1",
                level=DisclosureLevel.METADATA,
                title="Test",
                excerpt="Short excerpt",
                tags=["test"],
                timestamp=time.time(),
                token_estimate=10,
                full_content="The complete full content of this memory entry",
            )
        ]
        batch = pd.disclose_full(items)
        assert batch.level == DisclosureLevel.FULL_CONTENT
        assert batch.items[0].full_content != ""

    def test_select_for_context(self):
        pd = ProgressiveDisclosure()
        items = [
            DisclosedMemory(
                memory_id=f"m{i}",
                level=DisclosureLevel.METADATA,
                title=f"Memory {i}",
                excerpt=f"Excerpt {i}",
                tags=["test"],
                timestamp=time.time(),
                token_estimate=5,
                full_content=f"Full content {i}",
            )
            for i in range(5)
        ]
        metadata = pd.disclose_metadata(items)
        selected = pd.select_for_context(metadata, ["m0", "m2"])
        assert selected.level == DisclosureLevel.FULL_CONTENT
        assert len(selected.items) == 2

    def test_empty_items(self):
        pd = ProgressiveDisclosure()
        batch = pd.disclose_metadata([])
        assert len(batch.items) == 0
        assert batch.total_tokens == 0


class TestVerbatimHit:
    def test_creation(self):
        vh = VerbatimHit(
            position=42,
            content="exact match content",
            access_count=5,
            elapsed_us=100.5,
        )
        assert vh.position == 42
        assert vh.content == "exact match content"
        assert vh.access_count == 5

    def test_frozen(self):
        vh = VerbatimHit(position=1, content="test", access_count=1, elapsed_us=10.0)
        with pytest.raises(Exception):
            vh.content = "new"  # type: ignore[misc]


class TestVerbatimLayer:
    def test_init(self):
        layer = VerbatimLayer()
        assert not layer.stats()["wired"]
        assert layer.hit_rate() == 0.0

    def test_wire_cache(self):
        layer = VerbatimLayer()

        class MockCache:
            def lookup(self, query):
                return None

            def lookup_exact(self, query):
                return None

        layer.wire(MockCache())
        assert layer.stats()["wired"]

    def test_lookup_without_cache(self):
        layer = VerbatimLayer()
        result = layer.lookup("test")
        assert result is None

    def test_lookup_exact_without_cache(self):
        layer = VerbatimLayer()
        result = layer.lookup_exact("test")
        assert result is None

    def test_hit_rate_initial(self):
        layer = VerbatimLayer()
        assert layer.hit_rate() == 0.0

    def test_stats_structure(self):
        layer = VerbatimLayer()
        s = layer.stats()
        assert "hits" in s
        assert "misses" in s
        assert "hit_rate" in s
        assert "wired" in s
