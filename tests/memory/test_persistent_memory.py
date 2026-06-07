"""
Tests for persistent (SQLite-backed) memory components.

Covers:
  1. SQLiteStore CRUD (conversations + long_term)
  2. SQLiteShortTermMemory TTL and auto-pruning
  3. SQLiteLongTermMemory consolidation, deduplication, Ebbinghaus decay
  4. VectorSearcher retrieval quality (TF-IDF fallback)
"""

import math
import time
import uuid
from pathlib import Path

import numpy as np
import pytest

from src.memory.memory_store import (
    ConversationRecord,
    LongTermRecord,
    SQLiteStore,
)
from src.memory.short_term_memory import SQLiteShortTermMemory
from src.memory.long_term_memory import SQLiteLongTermMemory
from src.memory.vector_search import TfidfEncoder, VectorSearcher


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test_memory.db")


@pytest.fixture
async def store(db_path: str) -> SQLiteStore:
    s = SQLiteStore(db_path)
    await s.init_db()
    return s


@pytest.fixture
async def stm(db_path: str) -> SQLiteShortTermMemory:
    m = SQLiteShortTermMemory(
        db_path=db_path,
        session_id="test-session",
        ttl_hours=24,
        max_turns=50,
    )
    await m.init()
    return m


@pytest.fixture
async def ltm(db_path: str) -> SQLiteLongTermMemory:
    m = SQLiteLongTermMemory(db_path=db_path, half_life_hours=24.0, dedup_content=True)
    await m.init()
    return m


@pytest.fixture
def searcher() -> VectorSearcher:
    tfidf = TfidfEncoder(min_df=1)
    return VectorSearcher(encoder=tfidf)


# =============================================================================
# 1. SQLiteStore — CRUD
# =============================================================================


class TestSQLiteStoreCRUD:
    """Test basic create, read, update, delete operations on both tables."""

    async def test_conversation_crud(self, store: SQLiteStore):
        """Insert, fetch, count, and delete conversation records."""
        session = "crud-session"
        now = time.time()

        r1 = ConversationRecord(str(uuid.uuid4()), "user", "hello", now, session, 0.6)
        r2 = ConversationRecord(str(uuid.uuid4()), "agent", "hi there", now + 1, session, 0.4)
        await store.add_conversation(r1)
        await store.add_conversation(r2)

        assert await store.count_conversations(session) == 2
        assert await store.count_conversations() == 2

        fetched = await store.get_conversations(session, limit=10)
        assert len(fetched) == 2

        # Most recent first
        assert fetched[0].content == "hi there"
        assert fetched[1].content == "hello"

        await store.delete_conversations_by_session(session)
        assert await store.count_conversations(session) == 0

    async def test_long_term_crud(self, store: SQLiteStore):
        """Insert, fetch, update, and delete long-term records."""
        now = time.time()
        rid = str(uuid.uuid4())
        rec = LongTermRecord(
            id=rid,
            content="Important memory",
            memory_type="semantic",
            tags=["test", "important"],
            embedding=None,
            importance_score=0.9,
            created_at=now,
            last_accessed=now,
            access_count=0,
        )
        await store.add_long_term(rec)

        fetched = await store.get_long_term(rid)
        assert fetched is not None
        assert fetched.content == "Important memory"
        assert fetched.tags == ["test", "important"]

        await store.update_long_term_importance(rid, 0.95)
        fetched2 = await store.get_long_term(rid)
        assert fetched2.importance_score == pytest.approx(0.95)

        await store.update_long_term_access(rid)
        fetched3 = await store.get_long_term(rid)
        assert fetched3.access_count >= 1

        deleted = await store.delete_long_term(rid)
        assert deleted is True
        assert await store.get_long_term(rid) is None

    async def test_prune_conversations(self, store: SQLiteStore):
        """TTL-based pruning removes old entries."""
        session = "prune-session"
        now = time.time()
        old = ConversationRecord(str(uuid.uuid4()), "user", "old", now - 3600 * 48, session, 0.3)
        new = ConversationRecord(str(uuid.uuid4()), "user", "new", now, session, 0.7)
        await store.add_conversation(old)
        await store.add_conversation(new)

        removed = await store.prune_conversations(now - 3600 * 24)
        assert removed >= 1

        remaining = await store.get_conversations(session, limit=10)
        assert all(r.content == "new" for r in remaining)

    async def test_keyword_search_lt(self, store: SQLiteStore):
        """SQL LIKE search across long-term content."""
        now = time.time()
        recs = [
            LongTermRecord(str(uuid.uuid4()), "the cat sat on the mat", "semantic", [],
                           None, 0.5, now, now, 0),
            LongTermRecord(str(uuid.uuid4()), "dogs love to play fetch", "episodic", [],
                           None, 0.6, now + 1, now + 1, 0),
        ]
        for r in recs:
            await store.add_long_term(r)

        results = await store.search_long_term_keyword("cat")
        assert len(results) == 1
        assert "cat" in results[0].content

        results2 = await store.search_long_term_keyword("love")
        assert len(results2) == 1
        assert "love" in results2[0].content

    async def test_get_important_long_term(self, store: SQLiteStore):
        """Filter by minimum importance."""
        now = time.time()
        low = LongTermRecord(str(uuid.uuid4()), "low importance", "semantic", [],
                             None, 0.3, now, now, 0)
        high = LongTermRecord(str(uuid.uuid4()), "high importance", "semantic", [],
                              None, 0.9, now + 1, now + 1, 0)
        await store.add_long_term(low)
        await store.add_long_term(high)

        important = await store.get_important_long_term(min_importance=0.7)
        assert len(important) == 1
        assert important[0].content == "high importance"


# =============================================================================
# 2. SQLiteShortTermMemory — TTL and auto-pruning
# =============================================================================


class TestSQLiteShortTermMemory:
    """Session-scoped TTL, auto-prune, and working memory."""

    async def test_add_and_retrieve(self, stm: SQLiteShortTermMemory):
        """Turns can be written and read back in order."""
        await stm.add_turn("user", "first message")
        await stm.add_turn("agent", "response")
        await stm.add_turn("user", "follow-up")

        recent = await stm.get_recent(limit=5)
        assert len(recent) == 3
        assert recent[0].role == "user"
        assert recent[0].content == "first message"
        assert recent[-1].content == "follow-up"

    async def test_context_formatting(self, stm: SQLiteShortTermMemory):
        """get_context returns formatted string."""
        await stm.add_turn("user", "hello")
        await stm.add_turn("agent", "world")
        ctx = await stm.get_context(max_turns=2)
        assert "user: hello" in ctx
        assert "agent: world" in ctx

    async def test_session_isolation(self, db_path: str):
        """Different sessions do not see each other's turns."""
        stm1 = SQLiteShortTermMemory(db_path, "session-a", ttl_hours=24, max_turns=50)
        stm2 = SQLiteShortTermMemory(db_path, "session-b", ttl_hours=24, max_turns=50)
        await stm1.init()
        await stm2.init()

        await stm1.add_turn("user", "session-a turn")
        await stm2.add_turn("user", "session-b turn")

        a_turns = await stm1.get_recent(limit=10)
        b_turns = await stm2.get_recent(limit=10)

        assert len(a_turns) == 1
        assert len(b_turns) == 1
        assert a_turns[0].content == "session-a turn"
        assert b_turns[0].content == "session-b turn"

    async def test_prune_expired(self, stm: SQLiteShortTermMemory):
        """Entries beyond TTL are removed by prune_expired()."""
        # Insert an entry that appears to be 48 hours old by tweaking the DB
        old_id = str(uuid.uuid4())
        old_ts = time.time() - 3600 * 48
        record = ConversationRecord(old_id, "user", "old turn", old_ts, stm.session_id, 0.3)
        await stm.db.add_conversation(record)

        pruned = await stm.prune_expired()
        assert pruned >= 1

        recent = await stm.get_recent(limit=10)
        assert all(r.content != "old turn" for r in recent)

    async def test_clear_session(self, stm: SQLiteShortTermMemory):
        """Clear removes all turns for the session."""
        await stm.add_turn("user", "message")
        assert len(await stm.get_recent(limit=10)) == 1
        await stm.clear()
        assert len(await stm.get_recent(limit=10)) == 0

    async def test_working_memory(self, stm: SQLiteShortTermMemory):
        """Working memory is in-memory and isolated from TTL."""
        stm.set_working_memory("last_command", "/help")
        assert stm.get_working_memory("last_command") == "/help"
        stm.clear_working_memory()
        assert stm.get_working_memory("last_command") is None

    async def test_high_importance_turns(self, stm: SQLiteShortTermMemory):
        """Filtering by importance works."""
        await stm.add_turn("user", "short", importance_score=0.5)
        await stm.add_turn("user", "very important long message " * 20, importance_score=0.9)
        important = await stm.get_high_importance_turns(min_importance=0.6)
        assert len(important) == 1

    async def test_statistics(self, stm: SQLiteShortTermMemory):
        """Statistics contain expected keys."""
        await stm.add_turn("user", "hello")
        stats = await stm.get_statistics()
        assert stats["session_id"] == "test-session"
        assert stats["total_turns"] == 1
        assert stats["ttl_hours"] == 24
        assert stats["max_turns"] == 50

    async def test_add_turn_returns_conversation_turn(self, stm: SQLiteShortTermMemory):
        """add_turn returns a ConversationTurn with metadata."""
        turn = await stm.add_turn("user", "hello world")
        assert turn.role == "user"
        assert turn.content == "hello world"
        assert turn.metadata.get("importance_score") is not None
        assert turn.metadata.get("text_id") is not None

    async def test_auto_prune_on_max_turns(self, tmp_path: Path):
        """When turn count exceeds max_turns, the oldest excess is pruned."""
        db = str(tmp_path / "prune_test.db")
        stm = SQLiteShortTermMemory(db, "session-1", ttl_hours=240, max_turns=5)
        await stm.init()

        for i in range(10):
            await stm.add_turn("user", f"turn {i}")

        recent = await stm.get_recent(limit=100)
        # Should have at most max_turns entries
        assert len(recent) <= 5


# =============================================================================
# 3. SQLiteLongTermMemory — Dedup, decay, consolidation
# =============================================================================


class TestSQLiteLongTermMemory:
    """Deduplication, Ebbinghaus decay, and cross-session persistence."""

    async def test_add_and_fetch(self, ltm: SQLiteLongTermMemory):
        """Basic add/get round-trip."""
        rec = await ltm.add_memory("test memory", "semantic", ["test"], 0.8)
        assert rec.content == "test memory"

        fetched = await ltm.get_memory(rec.id)
        assert fetched is not None
        assert fetched.content == "test memory"

    async def test_dedup_boosts_importance(self, ltm: SQLiteLongTermMemory):
        """Adding same content twice boosts importance instead of duplicating."""
        rec1 = await ltm.add_memory("dedup content", "semantic", ["test"], 0.5)
        rec2 = await ltm.add_memory("dedup content", "semantic", ["test"], 0.5)

        # Same record returned, importance boosted
        assert rec1.id == rec2.id
        assert rec2.importance_score >= 0.5

        # Only one record in the database
        count = await ltm.count()
        assert count == 1

    async def test_dedup_without_flag(self, db_path: str):
        """When dedup is off, identical content creates two records."""
        ltm = SQLiteLongTermMemory(db_path, half_life_hours=24.0, dedup_content=False)
        await ltm.init()

        r1 = await ltm.add_memory("same content", "semantic", [], 0.5)
        r2 = await ltm.add_memory("same content", "semantic", [], 0.5)

        assert r1.id != r2.id
        assert await ltm.count() == 2

    async def test_recent_and_all(self, ltm: SQLiteLongTermMemory):
        """get_recent and get_all return expected order."""
        await ltm.add_memory("oldest", "semantic", [], 0.3)
        await ltm.add_memory("middle", "semantic", [], 0.5)
        await ltm.add_memory("newest", "semantic", [], 0.7)

        recent = await ltm.get_recent(limit=2)
        assert len(recent) == 2
        # Most recent first
        assert recent[0].content == "newest"

        all_recs = await ltm.get_all()
        assert len(all_recs) == 3

    async def test_ebbinghaus_decay(self, ltm: SQLiteLongTermMemory):
        """Decay reduces importance over time."""
        await ltm.add_memory("decay target", "semantic", [], 0.9)
        all_recs = await ltm.get_all()
        mem_id = all_recs[0].id

        # Simulate 1 hour of elapsed time
        now = time.time()
        past_time = now - 3600  # 1 hour ago
        await ltm.db.update_long_term_access(mem_id)
        await ltm.db.update_long_term_importance(mem_id, 0.9)

        # Apply decay with the birth time being the creation time
        # We need to manually set last_accessed to something in the past
        # Let's create a record with a past last_accessed
        import uuid as _uuid
        rid = str(_uuid.uuid4())
        rec = LongTermRecord(
            id=rid,
            content="decay item",
            memory_type="semantic",
            tags=[],
            embedding=None,
            importance_score=0.9,
            created_at=now,
            last_accessed=now - 7200,  # 2 hours ago
            access_count=0,
        )
        await ltm.db.add_long_term(rec)

        await ltm.apply_deterministic_decay(half_life_hours=24.0, current_time=now)

        fetched = await ltm.get_memory(rid)
        expected = 0.9 * math.exp(-2.0 / 24.0)
        assert fetched.importance_score == pytest.approx(expected, rel=1e-3)

    async def test_important_filter(self, ltm: SQLiteLongTermMemory):
        """get_important returns only high-importance records."""
        await ltm.add_memory("low", "semantic", [], 0.3)
        await ltm.add_memory("high", "semantic", [], 0.9)

        important = await ltm.get_important(min_importance=0.7)
        assert len(important) == 1
        assert important[0].content == "high"

    async def test_keyword_search(self, ltm: SQLiteLongTermMemory):
        """Keyword search via LIKE works."""
        await ltm.add_memory("the quick brown fox", "semantic", [], 0.5)
        results = await ltm.search_by_keyword("fox")
        assert len(results) == 1
        assert "fox" in results[0].content

    async def test_clear_all(self, ltm: SQLiteLongTermMemory):
        """clear_all removes all records."""
        await ltm.add_memory("memory 1", "semantic", [], 0.5)
        await ltm.add_memory("memory 2", "semantic", [], 0.6)
        assert await ltm.count() == 2

        await ltm.clear_all()
        assert await ltm.count() == 0

    async def test_statistics(self, ltm: SQLiteLongTermMemory):
        """Statistics include aggregate info."""
        await ltm.add_memory("m1", "semantic", [], 0.8)
        await ltm.add_memory("m2", "episodic", [], 0.3)

        stats = await ltm.get_statistics()
        assert stats["total_memories"] == 2
        assert stats["dedup_enabled"] is True
        assert stats["average_importance"] >= 0.0

    async def test_cross_session_persistence(self, ltm: SQLiteLongTermMemory):
        """Memory survives across LTM instance lifetimes (same DB)."""
        await ltm.add_memory("persistent data", "semantic", [], 0.9)
        count1 = await ltm.count()

        # Re-open LTM with same DB
        ltm2 = SQLiteLongTermMemory(ltm.db.db_path, half_life_hours=24.0)
        await ltm2.init()
        count2 = await ltm2.count()
        assert count2 == count1

        recs = await ltm2.get_all()
        contents = [r.content for r in recs]
        assert "persistent data" in contents


# =============================================================================
# 4. VectorSearcher — retrieval quality
# =============================================================================


class TestVectorSearcher:
    """Cosine similarity search with TF-IDF fallback."""

    def test_empty_index_returns_empty(self, searcher: VectorSearcher):
        """Searching an empty index returns empty list."""
        assert searcher.search("anything", top_k=5) == []

    def test_index_and_search(self, searcher: VectorSearcher):
        """Basic indexing and retrieval."""
        docs = [
            "the cat sat on the mat",
            "dogs love to play fetch",
            "the bird flew over the fence",
        ]
        searcher.index(docs)
        assert searcher.count == 3

        results = searcher.search("feline cat", top_k=2)
        assert len(results) >= 1
        # The cat document should rank higher
        top_text, top_score = results[0]
        assert "cat" in top_text or "mat" in top_text
        assert top_score > 0.0

    def test_top_k_limits(self, searcher: VectorSearcher):
        """top_k parameter is respected."""
        docs = [f"document number {i}" for i in range(20)]
        searcher.index(docs)

        results = searcher.search("document", top_k=5)
        assert len(results) <= 5

    def test_min_score_filter(self, searcher: VectorSearcher):
        """min_score filters low-scoring results."""
        docs = ["alpha beta gamma", "delta epsilon zeta", "eta theta iota"]
        searcher.index(docs)

        results = searcher.search("alpha beta", top_k=3, min_score=0.5)
        for _text, score in results:
            assert score >= 0.5

    def test_reindex_replaces_old_data(self, searcher: VectorSearcher):
        """Calling index() again replaces the old index."""
        searcher.index(["old data"])
        assert searcher.count == 1

        searcher.index(["new data", "more new data"])
        assert searcher.count == 2
        assert searcher.search("new")[0][0] == "new data"

    def test_batch_search_returns_indices(self, searcher: VectorSearcher):
        """batch_search includes the internal index position."""
        docs = ["first", "second", "third"]
        searcher.index(docs)
        results = searcher.batch_search("third", top_k=1)
        assert len(results) == 1
        assert results[0][0] == "third"
        assert results[0][2] == 2  # index 2

    def test_get_vector(self, searcher: VectorSearcher):
        """get_vector returns a valid numpy array."""
        docs = ["hello world"]
        searcher.index(docs)
        vec = searcher.get_vector(0)
        assert isinstance(vec, np.ndarray)
        assert vec.ndim == 1

    def test_save_and_load(self, searcher: VectorSearcher, tmp_path: Path):
        """Serialize and deserialize preserves data."""
        docs = ["persist this", "and this"]
        searcher.index(docs)

        p = str(tmp_path / "searcher.pkl")
        searcher.save(p)

        loaded = VectorSearcher.load(p)
        assert loaded.count == 2
        results = loaded.search("persist", top_k=1)
        assert "persist" in results[0][0]

    def test_tfidf_without_fit(self):
        """TfidfEncoder raises if index() hasn't been called."""
        encoder = TfidfEncoder()
        with pytest.raises(ValueError, match="has not been fit"):
            encoder.encode(["text"])


# =============================================================================
# 5. Integration: STM -> LTM consolidation
# =============================================================================


class TestConsolidationIntegration:
    """End-to-end: STM turns promoted to LTM."""

    async def test_stm_to_ltm_promotion(self, stm: SQLiteShortTermMemory, ltm: SQLiteLongTermMemory):
        """High-importance STM turns become LTM records."""
        await stm.add_turn("user", "This is an important discovery about AI safety", importance_score=0.9)
        await stm.add_turn("user", "hello", importance_score=0.3)

        important_turns = await stm.get_high_importance_turns(min_importance=0.6)
        assert len(important_turns) == 1

        count = await ltm.consolidate_from_conversations(important_turns, min_importance=0.5)
        assert count == 1

        ltm_recs = await ltm.get_all()
        assert len(ltm_recs) == 1
        # Content should include role prefix
        assert "user: This is an important discovery about AI safety" in ltm_recs[0].content

    async def test_promotion_skips_low_importance(self, stm: SQLiteShortTermMemory, ltm: SQLiteLongTermMemory):
        """Low-importance turns are not promoted."""
        await stm.add_turn("user", "ok", importance_score=0.2)
        await stm.add_turn("user", "fine", importance_score=0.3)

        important = await stm.get_high_importance_turns(min_importance=0.5)
        assert len(important) == 0

        count = await ltm.consolidate_from_conversations(
            important, min_importance=0.5
        )
        assert count == 0
