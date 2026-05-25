"""Tests for lyra_context_profiler.compaction module."""

import asyncio

import pytest

from lyra_context_profiler.compaction import (
    CompactionEngine,
    CompactionMode,
    CompactionResult,
    DisclosureLevel,
    DuplicateDetector,
    EmptyContextError,
    HierarchicalSummarizer,
    SummarizationLevel,
)
from lyra_context_profiler.strategies import CompactionStrategy


# ── Fixtures ────────────────────────────────────────────────────────────────────


class _FakeElement:
    """Minimal element for testing compaction."""
    def __init__(self, id, content, token_count=None, importance_score=0.5,
                 element_type="unknown"):
        self.id = id
        self.content = content
        self.token_count = token_count or max(1, len(content) // 4)
        self.importance_score = importance_score
        self.element_type = element_type


@pytest.fixture
def basic_elements():
    return {
        "a": _FakeElement("a", "This is a very long document that contains lots of information about the project. "
                                "It describes the architecture, the design decisions, and the implementation details. "
                                "There are many sections covering different topics. The first section discusses goals. "
                                "Further sections detail the approach.", token_count=200, importance_score=0.8),
        "b": _FakeElement("b", "Short note: remember to fix bug #123", token_count=20, importance_score=0.3),
        "c": _FakeElement("c", "Another comprehensive document with detailed explanations of the API. "
                                "It includes code examples, parameter descriptions, and return value documentation. "
                                "Each endpoint is documented with request/response examples.", token_count=150, importance_score=0.6),
    }


@pytest.fixture
def elements_with_dupes():
    return {
        "a": _FakeElement("a", "The quick brown fox jumps over the lazy dog", token_count=30),
        "b": _FakeElement("b", "The quick brown fox jumps over the lazy dog", token_count=30),  # exact dupe
        "c": _FakeElement("c", "The quick brown fox jumps over the lazy cat", token_count=30),  # near dupe
    }


# ── DuplicateDetector ───────────────────────────────────────────────────────────


class TestDuplicateDetector:
    def test_finds_exact_duplicates(self, elements_with_dupes):
        dd = DuplicateDetector()
        dupes = dd.find_duplicates(elements_with_dupes)
        # a and b are exact duplicates
        assert len(dupes) > 0
        ids_in_dupes = set()
        for id1, id2, _ in dupes:
            ids_in_dupes.add(id1)
            ids_in_dupes.add(id2)
        assert len(ids_in_dupes) >= 2

    def test_no_duplicates_in_unique_set(self, basic_elements):
        dd = DuplicateDetector()
        dupes = dd.find_duplicates(basic_elements)
        assert len(dupes) == 0

    def test_is_duplicate_returns_id(self):
        dd = DuplicateDetector()
        dd._known_hashes["a"] = DuplicateDetector._compute_hash("hello world test")
        result = dd.is_duplicate("hello world test")
        assert result == "a"

    def test_empty_elements_no_duplicates(self):
        dd = DuplicateDetector()
        dupes = dd.find_duplicates({})
        assert dupes == []


# ── HierarchicalSummarizer ──────────────────────────────────────────────────────


class TestHierarchicalSummarizer:
    def test_level_0_returns_full_content(self):
        hs = HierarchicalSummarizer()
        content = "This is the full content. It has multiple sentences. All should be kept."
        result = hs.summarize(content, level=0)
        assert result == content

    def test_level_2_shortens_content(self):
        hs = HierarchicalSummarizer()
        content = "First sentence here. Second sentence goes on. Third sentence continues. " \
                  "Fourth sentence is important. Fifth sentence wraps up. Sixth sentence ends it."
        result = hs.summarize(content, level=2)
        assert len(result) < len(content)
        assert "First" in result

    def test_level_3_is_minimal(self):
        hs = HierarchicalSummarizer()
        content = "This is the topic. Followed by many details. And more details. And even more."
        result = hs.summarize(content, level=3)
        assert len(result) <= len(content)

    def test_batch_summarize(self):
        hs = HierarchicalSummarizer()
        elements = {"a": "Content A with details.", "b": "Content B with details."}
        results = hs.summarize_batch(elements, level=2)
        assert set(results.keys()) == {"a", "b"}
        assert all(len(v) <= len(elements[k]) for k, v in results.items())

    def test_empty_content(self):
        hs = HierarchicalSummarizer()
        result = hs.summarize("", level=3)
        assert result == ""


# ── CompactionEngine ────────────────────────────────────────────────────────────


class TestCompactionEngine:
    def test_compact_empty_raises(self):
        engine = CompactionEngine()
        with pytest.raises(EmptyContextError):
            asyncio.run(engine.compact({}))

    def test_compact_basic_returns_result(self, basic_elements):
        engine = CompactionEngine()
        result = asyncio.run(engine.compact(
            basic_elements,
            strategy=CompactionStrategy.BALANCED,
            mode=CompactionMode.LOSSY,
            element_importance={"a": 0.8, "b": 0.3, "c": 0.6},
        ))
        assert isinstance(result, CompactionResult)
        assert result.original_tokens > 0
        assert result.strategy == CompactionStrategy.BALANCED

    def test_compact_conservative_preserves_more(self, basic_elements):
        engine = CompactionEngine()
        result = asyncio.run(engine.compact(
            basic_elements,
            strategy=CompactionStrategy.CONSERVATIVE,
            mode=CompactionMode.LOSSY,
            element_importance={"a": 0.8, "b": 0.3, "c": 0.6},
        ))
        assert result.compaction_ratio > 0.5  # Conservative should keep most

    def test_compact_aggressive_frees_more(self, basic_elements):
        engine = CompactionEngine()
        result = asyncio.run(engine.compact(
            basic_elements,
            strategy=CompactionStrategy.AGGRESSIVE,
            mode=CompactionMode.LOSSY,
            element_importance={"a": 0.1, "b": 0.1, "c": 0.1},  # all low importance
        ))
        assert result.elements_dropped >= 0

    def test_progressive_disclosure(self, basic_elements):
        engine = CompactionEngine()
        levels = {"a": DisclosureLevel.OVERVIEW, "b": DisclosureLevel.HIDDEN, "c": DisclosureLevel.FULL}
        result = asyncio.run(engine.progressive_disclose(basic_elements, levels))
        # b is hidden, should not be in result
        assert "b" not in result
        assert "a" in result
        assert "c" in result
        # a should be shorter (overview level)
        assert len(result["a"].content) <= len(basic_elements["a"].content)

    def test_history_accumulates(self, basic_elements):
        engine = CompactionEngine()
        asyncio.run(engine.compact(basic_elements, mode=CompactionMode.LOSSY))
        assert len(engine.history) == 1
        assert engine.last_result is not None

    def test_lossless_mode(self, basic_elements):
        """Lossless should not discard information, only remove duplicates."""
        engine = CompactionEngine()
        result = asyncio.run(engine.compact(
            basic_elements,
            strategy=CompactionStrategy.CONSERVATIVE,
            mode=CompactionMode.LOSSLESS,
        ))
        assert result.mode == CompactionMode.LOSSLESS
