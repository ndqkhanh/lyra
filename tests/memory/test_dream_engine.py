"""Comprehensive tests for DreamEngine — idle-time background memory consolidation."""

import time
import uuid
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from lyra.memory.dream_engine import (
    DEFAULT_DREAM_INTERVAL_SECONDS,
    DEFAULT_IDLE_THRESHOLD_SECONDS,
    DEFAULT_MIN_IMPORTANCE,
    DEFAULT_OUTDATED_DAYS,
    DEFAULT_SESSION_DEPTH,
    DEFAULT_SIMILARITY_THRESHOLD,
    TARGET_API_REDUCTION,
    TARGET_LoCoMo_SCORE,
    TARGET_TASK_IMPROVEMENT,
    TARGET_TOKEN_REDUCTION,
    DreamAction,
    DreamBank,
    DreamEngine,
    DreamEntry,
    _content_hash,
    _detect_contradictions,
    _find_exact_duplicates,
    _is_outdated,
)
from lyra.memory.memory_store import Memory, MemoryType


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_long_term():
    """Create a mock LongTermMemory with a working MemoryStore."""
    ltm = MagicMock()
    ltm.store = MagicMock()
    ltm.store.get_all = MagicMock(return_value=[])
    ltm.store.delete = MagicMock(return_value=True)
    ltm.add = MagicMock()
    ltm.get = MagicMock(return_value=None)
    ltm.search_by_content = MagicMock(return_value=[])
    return ltm


@pytest.fixture
def engine(mock_long_term):
    """Create a DreamEngine with mocked dependencies."""
    eng = DreamEngine(
        long_term=mock_long_term,
        idle_threshold=0.01,
        dream_interval=0.01,
        session_depth=5,
        similarity_threshold=0.85,
        outdated_days=90,
        min_importance=0.3,
    )
    return eng


def _make_memory(
    content: str,
    memory_id: str | None = None,
    tags: list[str] | None = None,
    importance: float = 0.5,
    timestamp: float | None = None,
) -> Memory:
    return Memory(
        memory_id=memory_id or str(uuid.uuid4()),
        content=content,
        memory_type=MemoryType.SEMANTIC,
        timestamp=timestamp or time.time(),
        importance=importance,
        tags=tags or [],
        context={},
    )


# =============================================================================
# Tests: constants
# =============================================================================


class TestConstants:
    def test_defaults_are_reasonable(self):
        assert DEFAULT_IDLE_THRESHOLD_SECONDS == 300.0
        assert DEFAULT_DREAM_INTERVAL_SECONDS == 86400.0
        assert DEFAULT_SESSION_DEPTH == 50
        assert DEFAULT_SIMILARITY_THRESHOLD == 0.85
        assert DEFAULT_OUTDATED_DAYS == 90
        assert DEFAULT_MIN_IMPORTANCE == 0.3

    def test_performance_targets(self):
        assert TARGET_TASK_IMPROVEMENT == 6.0
        assert TARGET_TOKEN_REDUCTION == 105.0
        assert TARGET_API_REDUCTION == 309.0
        assert TARGET_LoCoMo_SCORE == 91.6


# =============================================================================
# Tests: data structures
# =============================================================================


class TestDreamAction:
    def test_values(self):
        assert DreamAction.MERGED.value == "merged"
        assert DreamAction.OUTDATED.value == "outdated"
        assert DreamAction.CONTRADICTION.value == "contradiction"
        assert DreamAction.PATTERN.value == "pattern"
        assert DreamAction.PRUNED.value == "pruned"
        assert DreamAction.SUMMARIZED.value == "summarized"

    def test_members(self):
        assert len(DreamAction) == 6


class TestDreamEntry:
    def test_default_importance(self):
        entry = DreamEntry(
            entry_id="e1",
            action=DreamAction.MERGED,
            description="test",
            source_memory_ids=["m1"],
        )
        assert entry.importance == 0.5
        assert entry.confidence == 1.0

    def test_with_summary(self):
        entry = DreamEntry(
            entry_id="e2",
            action=DreamAction.PATTERN,
            description="pattern found",
            source_memory_ids=["m1", "m2"],
            created_summary="summary text",
            importance=0.8,
            confidence=0.7,
        )
        assert entry.created_summary == "summary text"
        assert entry.importance == 0.8

    def test_metadata_defaults_to_empty_dict(self):
        entry = DreamEntry(
            entry_id="e3",
            action=DreamAction.PRUNED,
            description="pruned",
            source_memory_ids=["m1"],
        )
        assert entry.metadata == {}


class TestDreamBank:
    def test_minimal_bank(self):
        bank = DreamBank(bank_id="b1", timestamp=100.0, entries=[])
        assert bank.bank_id == "b1"
        assert bank.memory_bank_size == 0
        assert bank.session_sources == 0
        assert bank.metadata == {}

    def test_with_entries(self):
        entries = [
            DreamEntry(entry_id="e1", action=DreamAction.MERGED, description="d1", source_memory_ids=["m1"]),
        ]
        bank = DreamBank(bank_id="b2", timestamp=200.0, entries=entries, memory_bank_size=500, session_sources=10)
        assert len(bank.entries) == 1
        assert bank.memory_bank_size == 500
        assert bank.session_sources == 10

    def test_bank_metadata(self):
        bank = DreamBank(
            bank_id="b3", timestamp=300.0, entries=[], metadata={"cycle": 1},
        )
        assert bank.metadata["cycle"] == 1


# =============================================================================
# Tests: utility functions
# =============================================================================


class TestContentHash:
    def test_consistent_hash(self):
        h1 = _content_hash("hello world")
        h2 = _content_hash("hello world")
        assert h1 == h2

    def test_different_content(self):
        h1 = _content_hash("hello")
        h2 = _content_hash("world")
        assert h1 != h2

    def test_empty_string(self):
        h = _content_hash("")
        assert isinstance(h, str)
        assert len(h) == 32  # MD5 hex digest


class TestFindExactDuplicates:
    def test_no_duplicates(self):
        m1 = _make_memory("alpha", memory_id="a1")
        m2 = _make_memory("beta", memory_id="a2")
        groups = _find_exact_duplicates([m1, m2])
        assert len(groups) == 2  # Each content gets its own group
        for g in groups.values():
            assert len(g) == 1

    def test_exact_duplicates(self):
        m1 = _make_memory("same content", memory_id="d1")
        m2 = _make_memory("same content", memory_id="d2")
        m3 = _make_memory("different", memory_id="d3")
        groups = _find_exact_duplicates([m1, m2, m3])
        dup_key = _content_hash("same content")
        assert dup_key in groups
        assert len(groups[dup_key]) == 2

    def test_empty_list(self):
        assert _find_exact_duplicates([]) == {}

    def test_single_memory(self):
        m = _make_memory("only one")
        groups = _find_exact_duplicates([m])
        assert len(groups) == 1
        assert len(list(groups.values())[0]) == 1


class TestDetectContradictions:
    def test_with_contradiction_checker(self):
        checker = MagicMock(return_value=0.9)
        m1 = _make_memory("A is true", memory_id="c1", tags=["topic"])
        m2 = _make_memory("A is false", memory_id="c2", tags=["topic"])
        result = _detect_contradictions([m1, m2], contradiction_checker=checker)
        assert len(result) == 1
        assert result[0][2] > 0.7

    def test_checker_below_threshold(self):
        checker = MagicMock(return_value=0.5)
        m1 = _make_memory("A is true", memory_id="c3", tags=["topic"])
        m2 = _make_memory("A is false", memory_id="c4", tags=["topic"])
        result = _detect_contradictions([m1, m2], contradiction_checker=checker)
        assert len(result) == 0

    def test_fallback_keyword_contradiction_with_negation(self):
        m1 = _make_memory("The system is active", memory_id="c5", tags=["system"])
        m2 = _make_memory("The system is not responding", memory_id="c6", tags=["system"])
        result = _detect_contradictions([m1, m2])
        # Should detect contradiction via negation markers on same tag
        assert len(result) >= 1

    def test_fallback_no_contradiction(self):
        m1 = _make_memory("Apples are fruits", memory_id="c7", tags=["fruit"])
        m2 = _make_memory("Cars need fuel", memory_id="c8", tags=["vehicle"])
        result = _detect_contradictions([m1, m2])
        assert len(result) == 0

    def test_empty_list(self):
        result = _detect_contradictions([])
        assert result == []

    def test_single_memory_no_contradiction(self):
        m = _make_memory("Just one", memory_id="c9", tags=["tag"])
        result = _detect_contradictions([m])
        assert result == []


class TestIsOutdated:
    def test_recent_memory(self):
        m = _make_memory("recent", timestamp=time.time())
        assert not _is_outdated(m, max_age_days=90)

    def test_old_memory(self):
        m = _make_memory("old", timestamp=time.time() - 100 * 86400)
        assert _is_outdated(m, max_age_days=90)

    def test_boundary(self):
        # Exactly at threshold
        m = _make_memory("boundary", timestamp=time.time() - 90 * 86400)
        # Age >= threshold means outdated
        assert _is_outdated(m, max_age_days=90)

    def test_zero_max_age(self):
        m = _make_memory("any", timestamp=time.time())
        assert _is_outdated(m, max_age_days=0)


# =============================================================================
# Tests: DreamEngine
# =============================================================================


class TestDreamEngineInit:
    def test_default_initialization(self, mock_long_term):
        eng = DreamEngine(long_term=mock_long_term)
        assert eng.idle_threshold == DEFAULT_IDLE_THRESHOLD_SECONDS
        assert eng.dream_interval == DEFAULT_DREAM_INTERVAL_SECONDS
        assert eng.session_depth == DEFAULT_SESSION_DEPTH
        assert eng.similarity_threshold == DEFAULT_SIMILARITY_THRESHOLD
        assert eng.outdated_days == DEFAULT_OUTDATED_DAYS
        assert eng.min_importance == DEFAULT_MIN_IMPORTANCE
        assert eng._dream_count == 0
        assert eng._dream_history == []
        assert eng._applied_bank is None

    def test_custom_parameters(self, mock_long_term):
        eng = DreamEngine(
            long_term=mock_long_term,
            idle_threshold=10.0,
            dream_interval=100.0,
            session_depth=20,
            min_importance=0.5,
        )
        assert eng.idle_threshold == 10.0
        assert eng.dream_interval == 100.0
        assert eng.session_depth == 20
        assert eng.min_importance == 0.5

    def test_with_contradiction_checker(self, mock_long_term):
        checker = MagicMock()
        eng = DreamEngine(long_term=mock_long_term, contradiction_checker=checker)
        assert eng.contradiction_checker is checker


class TestIdleDetection:
    def test_record_activity_resets_idle(self, engine):
        with patch("time.time", return_value=100.0):
            engine.record_activity()
            assert engine._last_active_time == 100.0

    def test_is_idle_when_idle(self, engine):
        engine.idle_threshold = 0.0
        with patch("time.time", return_value=100.0):
            engine._last_active_time = 50.0  # 50s gap > 0.0
            assert engine.is_idle()

    def test_is_idle_when_active(self, engine):
        engine.idle_threshold = 60.0
        with patch("time.time", return_value=100.0):
            engine._last_active_time = 95.0  # 5s < 60s
            assert not engine.is_idle()

    def test_should_dream_not_idle(self, engine):
        engine.idle_threshold = 60.0
        with patch("time.time", return_value=100.0):
            engine._last_active_time = 95.0
            assert not engine.should_dream()

    def test_should_dream_recently_dreamed(self, engine):
        engine.idle_threshold = 0.0
        engine.dream_interval = 100.0
        engine._dream_count = 1
        with patch("time.time", return_value=100.0):
            engine._last_active_time = 50.0
            engine._last_dream_time = 99.0  # only 1s ago
            # Need enough memories
            engine.long_term.store.get_all.return_value = [
                _make_memory("m1"),
                _make_memory("m2"),
                _make_memory("m3"),
                _make_memory("m4"),
                _make_memory("m5"),
                _make_memory("m6"),
            ]
            assert not engine.should_dream()

    def test_should_dream_not_enough_memories(self, engine):
        engine.idle_threshold = 0.0
        engine.dream_interval = 0.0
        engine._last_active_time = 50.0
        engine.long_term.store.get_all.return_value = [
            _make_memory("m1"),
            _make_memory("m2"),
        ]  # only 2, need >5
        with patch("time.time", return_value=100.0):
            assert not engine.should_dream()

    def test_should_dream_all_conditions_met(self, engine):
        engine.idle_threshold = 0.0
        engine.dream_interval = 0.0
        engine._last_active_time = 50.0
        engine.long_term.store.get_all.return_value = [
            _make_memory("m1"),
            _make_memory("m2"),
            _make_memory("m3"),
            _make_memory("m4"),
            _make_memory("m5"),
            _make_memory("m6"),
        ]
        with patch("time.time", return_value=100.0):
            assert engine.should_dream()


class TestDreamCycle:
    def test_dream_returns_dreambank(self, engine):
        engine.long_term.store.get_all.return_value = []
        with patch("time.time", return_value=500.0):
            bank = engine.dream()
        assert isinstance(bank, DreamBank)
        assert bank.bank_id is not None
        assert bank.timestamp == 500.0

    def test_dream_dedup_exact_duplicates(self, engine):
        m1 = _make_memory("duplicate text", memory_id="dup1", importance=0.5)
        m2 = _make_memory("duplicate text", memory_id="dup2", importance=0.7)
        engine.long_term.store.get_all.return_value = [m1, m2]
        with patch("time.time", return_value=500.0):
            bank = engine.dream()
        merged = [e for e in bank.entries if e.action == DreamAction.MERGED]
        assert len(merged) == 1
        assert "duplicate" in merged[0].description

    def test_dream_prunes_outdated_memories(self, engine):
        old = _make_memory(
            "old fact", memory_id="old1", importance=0.5,
            timestamp=time.time() - 100 * 86400,
        )
        engine.long_term.store.get_all.return_value = [old]
        with patch("time.time", return_value=time.time()):
            bank = engine.dream()
        pruned = [e for e in bank.entries if e.action == DreamAction.PRUNED]
        assert len(pruned) >= 1

    def test_dream_prunes_low_importance(self, engine):
        low = _make_memory("trivia", memory_id="low1", importance=0.1)
        engine.long_term.store.get_all.return_value = [low]
        with patch("time.time", return_value=time.time()):
            bank = engine.dream()
        pruned = [e for e in bank.entries if e.action == DreamAction.PRUNED]
        assert len(pruned) >= 1

    def test_dream_discovers_patterns(self, engine):
        memories = [
            _make_memory("memory about X", memory_id="p1", tags=["topic_a"], importance=0.6),
            _make_memory("also about X", memory_id="p2", tags=["topic_a"], importance=0.7),
            _make_memory("more about X", memory_id="p3", tags=["topic_a"], importance=0.8),
        ]
        engine.long_term.store.get_all.return_value = memories
        with patch("time.time", return_value=time.time()):
            bank = engine.dream()
        patterns = [e for e in bank.entries if e.action == DreamAction.PATTERN]
        assert len(patterns) >= 1

    def test_dream_increments_count(self, engine):
        engine.long_term.store.get_all.return_value = []
        with patch("time.time", return_value=500.0):
            engine.dream()
        assert engine._dream_count == 1

    def test_dream_appends_to_history(self, engine):
        engine.long_term.store.get_all.return_value = []
        with patch("time.time", return_value=500.0):
            engine.dream()
        assert len(engine._dream_history) == 1

    def test_dream_resolves_contradictions(self, engine):
        m1 = _make_memory("system is active", memory_id="con1", tags=["system"], importance=0.8)
        m2 = _make_memory("system is not responding", memory_id="con2", tags=["system"], importance=0.6)
        engine.long_term.store.get_all.return_value = [m1, m2]
        with patch("time.time", return_value=time.time()):
            bank = engine.dream()
        contradictions = [e for e in bank.entries if e.action == DreamAction.CONTRADICTION]
        assert len(contradictions) >= 1

    def test_dream_idempotent_no_writes(self, engine):
        """dream() should only read, never write."""
        engine.long_term.store.get_all.return_value = []
        engine.dream()
        engine.long_term.add.assert_not_called()
        engine.long_term.store.delete.assert_not_called()

    def test_dream_with_external_contradiction_checker(self, mock_long_term):
        checker = MagicMock(side_effect=lambda a, b: 0.9 if "active" in a else 0.0)
        eng = DreamEngine(
            long_term=mock_long_term,
            idle_threshold=0.01,
            dream_interval=0.01,
            contradiction_checker=checker,
        )
        m1 = _make_memory("system is active", memory_id="ext1", tags=["sys"])
        m2 = _make_memory("system is inactive", memory_id="ext2", tags=["sys"])
        eng.long_term.store.get_all.return_value = [m1, m2]
        with patch("time.time", return_value=time.time()):
            bank = eng.dream()
        contradictions = [e for e in bank.entries if e.action == DreamAction.CONTRADICTION]
        assert len(contradictions) >= 1
        checker.assert_called()


class TestApplyDream:
    def test_apply_merged(self, engine):
        bank = DreamBank(
            bank_id="b1",
            timestamp=time.time(),
            entries=[
                DreamEntry(
                    entry_id="e1",
                    action=DreamAction.MERGED,
                    description="merged 2 duplicates",
                    source_memory_ids=["m1", "m2"],
                    created_summary="merged summary",
                    importance=0.6,
                    timestamp=time.time(),
                    confidence=0.95,
                    metadata={"group_size": 2},
                ),
            ],
        )
        engine.apply_dream(bank)
        engine.long_term.add.assert_called_once()
        engine.long_term.store.delete.assert_called_once_with("m2")

    def test_apply_contradiction(self, engine):
        engine.long_term.get.return_value = _make_memory(
            "truth", memory_id="sel1", importance=0.7,
        )
        bank = DreamBank(
            bank_id="b2",
            timestamp=time.time(),
            entries=[
                DreamEntry(
                    entry_id="e2",
                    action=DreamAction.CONTRADICTION,
                    description="contradiction resolved",
                    source_memory_ids=["mem_a", "mem_b"],
                    timestamp=time.time(),
                    confidence=0.85,
                    metadata={
                        "selected_id": "sel1",
                        "suppressed_id": "sup1",
                    },
                ),
            ],
        )
        engine.apply_dream(bank)
        engine.long_term.store.delete.assert_called_once_with("sup1")

    def test_apply_pruned(self, engine):
        bank = DreamBank(
            bank_id="b3",
            timestamp=time.time(),
            entries=[
                DreamEntry(
                    entry_id="e3",
                    action=DreamAction.PRUNED,
                    description="pruned old memory",
                    source_memory_ids=["old1"],
                    timestamp=time.time(),
                    confidence=0.9,
                ),
            ],
        )
        engine.apply_dream(bank)
        engine.long_term.store.delete.assert_called_once_with("old1")

    def test_apply_pattern(self, engine):
        bank = DreamBank(
            bank_id="b4",
            timestamp=time.time(),
            entries=[
                DreamEntry(
                    entry_id="e4",
                    action=DreamAction.PATTERN,
                    description="cross-session pattern detected",
                    source_memory_ids=["s1", "s2", "s3"],
                    created_summary="pattern summary",
                    importance=0.75,
                    timestamp=time.time(),
                    confidence=0.7,
                    metadata={"pattern_memory_count": 3},
                ),
            ],
        )
        engine.apply_dream(bank)
        engine.long_term.add.assert_called_once()

    def test_apply_returns_same_bank_with_metadata(self, engine):
        bank = DreamBank(
            bank_id="b5", timestamp=time.time(), entries=[],
        )
        result = engine.apply_dream(bank)
        assert result.metadata.get("applied_count") == 0

    def test_apply_sets_applied_bank(self, engine):
        bank = DreamBank(
            bank_id="b6", timestamp=time.time(), entries=[],
        )
        engine.apply_dream(bank)
        assert engine._applied_bank is bank


class TestRevertDream:
    def test_revert_no_applied_bank(self, engine):
        result = engine.revert_dream()
        assert result.bank_id == "revert-none"
        assert "error" in result.metadata

    def test_revert_with_bank(self, engine):
        entry = DreamEntry(
            entry_id="rev1",
            action=DreamAction.MERGED,
            description="merged stuff",
            source_memory_ids=["s1", "s2"],
            created_summary="merged summary",
            importance=0.5,
            timestamp=time.time(),
        )
        bank = DreamBank(
            bank_id="br1",
            timestamp=time.time(),
            entries=[entry],
        )
        engine._applied_bank = bank
        result = engine.revert_dream()
        assert result.bank_id == "br1"

    def test_revert_with_pattern_searches_store(self, engine):
        entry = DreamEntry(
            entry_id="rp1",
            action=DreamAction.PATTERN,
            description="pattern",
            source_memory_ids=["p1", "p2", "p3"],
            created_summary="pattern summary",
            importance=0.7,
            timestamp=time.time(),
        )
        bank = DreamBank(
            bank_id="br2",
            timestamp=time.time(),
            entries=[entry],
        )
        engine._applied_bank = bank
        engine.revert_dream()
        engine.long_term.search_by_content.assert_called_once()

    def test_revert_clears_applied_bank(self, engine):
        bank = DreamBank(
            bank_id="br3", timestamp=time.time(), entries=[],
        )
        engine._applied_bank = bank
        engine.revert_dream()
        assert engine._applied_bank is None


class TestPatternDiscovery:
    def test_discover_patterns_requires_min_group(self, engine):
        memories = [
            _make_memory("m1", tags=["tag_x"], importance=0.5),
            _make_memory("m2", tags=["tag_x"], importance=0.6),
            # Only 2 memories with tag_x, min_group_size=3
        ]
        patterns = engine._discover_patterns(memories, min_group_size=3)
        assert len(patterns) == 0

    def test_discover_patterns_finds_group(self, engine):
        memories = [
            _make_memory("m1", tags=["tag_y"], importance=0.5, memory_id="pa1"),
            _make_memory("m2", tags=["tag_y"], importance=0.6, memory_id="pa2"),
            _make_memory("m3", tags=["tag_y"], importance=0.7, memory_id="pa3"),
        ]
        patterns = engine._discover_patterns(memories, min_group_size=3)
        assert len(patterns) >= 1
        desc, group, imp = patterns[0]
        assert "tag_y" in desc
        assert len(group) == 3
        assert imp == pytest.approx(0.6)

    def test_discover_patterns_skips_dream_tags(self, engine):
        memories = [
            _make_memory("m1", tags=["dream"], importance=0.5),
            _make_memory("m2", tags=["dream"], importance=0.6),
            _make_memory("m3", tags=["dream"], importance=0.7),
        ]
        patterns = engine._discover_patterns(memories, min_group_size=3)
        assert len(patterns) == 0

    def test_discover_patterns_empty_memories(self, engine):
        patterns = engine._discover_patterns([])
        assert patterns == []


class TestLightConsolidate:
    def test_light_consolidate_merges_duplicates(self, engine):
        m1 = _make_memory("same text", memory_id="l1", importance=0.5)
        m2 = _make_memory("same text", memory_id="l2", importance=0.7)
        bank = engine.light_consolidate([m1, m2])
        merged = [e for e in bank.entries if e.action == DreamAction.MERGED]
        assert len(merged) == 1

    def test_light_consolidate_skips_outdated_check(self, engine):
        old = _make_memory(
            "old", memory_id="l3", importance=0.5,
            timestamp=time.time() - 200 * 86400,
        )
        bank = engine.light_consolidate([old])
        pruned = [e for e in bank.entries if e.action == DreamAction.PRUNED]
        # light_consolidate only prunes low importance, not outdated
        if old.importance >= engine.min_importance:
            assert len(pruned) == 0

    def test_light_consolidate_prunes_low_importance(self, engine):
        low = _make_memory("low", memory_id="l4", importance=0.1)
        bank = engine.light_consolidate([low])
        pruned = [e for e in bank.entries if e.action == DreamAction.PRUNED]
        assert len(pruned) == 1

    def test_light_consolidate_metadata(self, engine):
        m = _make_memory("single", memory_id="l5", importance=0.5)
        bank = engine.light_consolidate([m])
        assert bank.metadata.get("light_consolidation") is True
        assert bank.metadata.get("token_reduction_factor") == TARGET_TOKEN_REDUCTION
        assert bank.metadata.get("api_reduction_factor") == TARGET_API_REDUCTION

    def test_light_consolidate_empty(self, engine):
        bank = engine.light_consolidate([])
        assert len(bank.entries) == 0


class TestGetMemories:
    def test_get_memories_from_store(self, engine):
        m1 = _make_memory("m1", memory_id="gm1")
        engine.long_term.store.get_all.return_value = [m1]
        result = engine._get_memories()
        assert len(result) == 1
        assert result[0].content == "m1"

    def test_get_memories_falls_back_to_get_all(self, mock_long_term):
        eng = DreamEngine(long_term=mock_long_term)
        # Remove store attribute
        del eng.long_term.store
        eng.long_term.get_all = MagicMock(return_value=["mem1", "mem2"])
        result = eng._get_memories()
        assert result == ["mem1", "mem2"]

    def test_get_memories_empty(self, engine):
        engine.long_term.store.get_all.return_value = []
        assert engine._get_memories() == []


class TestHistoryAndStats:
    def test_get_dream_history(self, engine):
        engine.long_term.store.get_all.return_value = []
        with patch("time.time", return_value=500.0):
            bank = engine.dream()
        history = engine.get_dream_history()
        assert len(history) == 1
        assert history[0].bank_id == bank.bank_id

    def test_get_statistics_returns_dict(self, engine):
        stats = engine.get_statistics()
        assert isinstance(stats, dict)
        assert "dream_count" in stats
        assert "last_dream_time" in stats
        assert "total_consolidation_entries" in stats
        assert "performance_targets" in stats
        assert stats["performance_targets"]["task_improvement_x"] == TARGET_TASK_IMPROVEMENT

    def test_get_statistics_after_dream(self, engine):
        engine.long_term.store.get_all.return_value = []
        with patch("time.time", return_value=500.0):
            engine.dream()
        stats = engine.get_statistics()
        assert stats["dream_count"] == 1

    def test_get_statistics_empty_history(self, engine):
        stats = engine.get_statistics()
        assert stats["dream_count"] == 0
        assert stats["recent_bank_entries"] == 0
