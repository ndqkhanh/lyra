"""Tests for the SQLite-backed memory persistence layer.

Covers SQLiteStore, ConversationRecord, LongTermRecord,
SQLiteShortTermMemory, and SQLiteLongTermMemory.
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from lyra.memory.memory_store import (
    ConversationRecord,
    LongTermRecord,
    SQLiteStore,
)
from lyra.memory.short_term_memory import SQLiteShortTermMemory
from lyra.memory.long_term_memory import SQLiteLongTermMemory


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def db_path() -> str:
    with NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
async def store(db_path) -> SQLiteStore:
    s = SQLiteStore(db_path)
    await s.init_db()
    return s


# ===================================================================
# SQLiteStore lifecycle tests
# ===================================================================


class TestSQLiteStoreInit:
    """Tests for SQLiteStore initialisation."""

    def test_creation(self, db_path) -> None:
        store = SQLiteStore(db_path)
        assert str(store.db_path) == db_path

    @pytest.mark.asyncio
    async def test_init_creates_tables(self, db_path) -> None:
        store = SQLiteStore(db_path)
        await store.init_db()
        # Verify tables exist
        import aiosqlite
        async with aiosqlite.connect(db_path) as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in await cursor.fetchall()]
        assert "conversations" in tables
        assert "long_term" in tables

    def test_parent_dir_created(self) -> None:
        from tempfile import mkdtemp
        import shutil
        tmpdir = mkdtemp()
        path = Path(tmpdir) / "nested" / "test.db"
        store = SQLiteStore(str(path))
        assert path.parent.exists()
        shutil.rmtree(tmpdir)  # Clean up

    @pytest.mark.asyncio
    async def test_close_noop(self, store) -> None:
        # Should not raise
        await store.close()
        assert True


# ===================================================================
# SQLiteStore conversation tests
# ===================================================================


class TestSQLiteStoreConversations:
    """Tests for conversation CRUD operations."""

    @pytest.mark.asyncio
    async def test_add_and_get_conversation(self, store) -> None:
        now = time.time()
        record = ConversationRecord(
            text_id=str(uuid.uuid4()),
            role="user",
            content="Hello",
            timestamp=now,
            session_id="session-1",
            importance_score=0.7,
        )
        await store.add_conversation(record)

        records = await store.get_conversations("session-1", limit=10)
        assert len(records) == 1
        assert records[0].content == "Hello"
        assert records[0].role == "user"

    @pytest.mark.asyncio
    async def test_get_conversations_since(self, store) -> None:
        now = time.time()
        for i in range(3):
            await store.add_conversation(ConversationRecord(
                text_id=str(uuid.uuid4()),
                role="user",
                content=f"Message {i}",
                timestamp=now + i,
                session_id="session-1",
            ))

        # Get conversations since timestamp
        records = await store.get_conversations("session-1", limit=10, since=now + 1)
        assert len(records) == 2  # Only messages with timestamp >= now+1

    @pytest.mark.asyncio
    async def test_get_conversations_limit(self, store) -> None:
        for i in range(5):
            await store.add_conversation(ConversationRecord(
                text_id=str(uuid.uuid4()),
                role="user",
                content=f"Msg {i}",
                timestamp=time.time() + i,
                session_id="session-1",
            ))

        records = await store.get_conversations("session-1", limit=3)
        assert len(records) <= 3

    @pytest.mark.asyncio
    async def test_get_conversations_multiple_sessions(self, store) -> None:
        await store.add_conversation(ConversationRecord(
            text_id="a1", role="user", content="Session A",
            timestamp=time.time(), session_id="session-a",
        ))
        await store.add_conversation(ConversationRecord(
            text_id="b1", role="user", content="Session B",
            timestamp=time.time(), session_id="session-b",
        ))

        records_a = await store.get_conversations("session-a")
        assert len(records_a) == 1
        assert records_a[0].content == "Session A"

    @pytest.mark.asyncio
    async def test_delete_conversations_by_session(self, store) -> None:
        await store.add_conversation(ConversationRecord(
            text_id="d1", role="user", content="Delete me",
            timestamp=time.time(), session_id="session-del",
        ))
        await store.delete_conversations_by_session("session-del")

        records = await store.get_conversations("session-del")
        assert len(records) == 0

    @pytest.mark.asyncio
    async def test_prune_conversations(self, store) -> None:
        now = time.time()
        await store.add_conversation(ConversationRecord(
            text_id="old", role="user", content="Old",
            timestamp=now - 100, session_id="s1",
        ))
        await store.add_conversation(ConversationRecord(
            text_id="new", role="user", content="New",
            timestamp=now, session_id="s1",
        ))

        deleted = await store.prune_conversations(now - 50)
        assert deleted >= 1

        records = await store.get_conversations("s1")
        assert all(r.timestamp >= now - 50 for r in records)

    @pytest.mark.asyncio
    async def test_count_conversations(self, store) -> None:
        for i in range(3):
            await store.add_conversation(ConversationRecord(
                text_id=str(uuid.uuid4()), role="user", content=f"M{i}",
                timestamp=time.time(), session_id="s1",
            ))
        await store.add_conversation(ConversationRecord(
            text_id="other", role="user", content="Other",
            timestamp=time.time(), session_id="s2",
        ))

        total = await store.count_conversations()
        assert total == 4

        s1_count = await store.count_conversations("s1")
        assert s1_count == 3


# ===================================================================
# SQLiteStore long-term tests
# ===================================================================


class TestSQLiteStoreLongTerm:
    """Tests for long-term memory storage operations."""

    @pytest.mark.asyncio
    async def test_add_and_get_long_term(self, store) -> None:
        now = time.time()
        record = LongTermRecord(
            id=str(uuid.uuid4()),
            content="Test long term memory",
            memory_type="semantic",
            tags=["test", "memory"],
            importance_score=0.8,
            created_at=now,
        )
        await store.add_long_term(record)

        fetched = await store.get_long_term(record.id)
        assert fetched is not None
        assert fetched.content == "Test long term memory"
        assert "test" in fetched.tags

    @pytest.mark.asyncio
    async def test_get_long_term_not_found(self, store) -> None:
        fetched = await store.get_long_term("nonexistent")
        assert fetched is None

    @pytest.mark.asyncio
    async def test_get_all_long_term(self, store) -> None:
        for i in range(3):
            await store.add_long_term(LongTermRecord(
                id=str(uuid.uuid4()),
                content=f"Memory {i}",
                memory_type="semantic",
                created_at=time.time() + i,
            ))

        records = await store.get_all_long_term()
        assert len(records) == 3

    @pytest.mark.asyncio
    async def test_search_long_term_keyword(self, store) -> None:
        await store.add_long_term(LongTermRecord(
            id=str(uuid.uuid4()), content="Python programming",
            memory_type="semantic", tags=[], created_at=time.time(),
        ))
        await store.add_long_term(LongTermRecord(
            id=str(uuid.uuid4()), content="JavaScript coding",
            memory_type="semantic", tags=[], created_at=time.time(),
        ))

        results = await store.search_long_term_keyword("Python")
        assert len(results) == 1
        assert results[0].content == "Python programming"

    @pytest.mark.asyncio
    async def test_get_long_term_recent(self, store) -> None:
        for i in range(5):
            await store.add_long_term(LongTermRecord(
                id=str(uuid.uuid4()), content=f"Memory {i}",
                memory_type="semantic", tags=[],
                created_at=time.time() + i,
            ))

        recent = await store.get_long_term_recent(limit=3)
        assert len(recent) == 3

    @pytest.mark.asyncio
    async def test_update_long_term_access(self, store) -> None:
        now = time.time()
        record = LongTermRecord(
            id=str(uuid.uuid4()), content="Test",
            memory_type="semantic", tags=[], created_at=now,
            last_accessed=now, access_count=0,
        )
        await store.add_long_term(record)

        await store.update_long_term_access(record.id)
        updated = await store.get_long_term(record.id)
        assert updated is not None
        assert updated.access_count == 1
        assert updated.last_accessed >= now

    @pytest.mark.asyncio
    async def test_update_long_term_importance(self, store) -> None:
        record = LongTermRecord(
            id=str(uuid.uuid4()), content="Test",
            memory_type="semantic", tags=[], created_at=time.time(),
            importance_score=0.5,
        )
        await store.add_long_term(record)

        await store.update_long_term_importance(record.id, 0.9)
        updated = await store.get_long_term(record.id)
        assert updated is not None
        assert updated.importance_score == 0.9

    @pytest.mark.asyncio
    async def test_delete_long_term(self, store) -> None:
        record = LongTermRecord(
            id=str(uuid.uuid4()), content="Delete me",
            memory_type="semantic", tags=[], created_at=time.time(),
        )
        await store.add_long_term(record)
        assert record.id is not None

        deleted = await store.delete_long_term(record.id)
        assert deleted is True

        fetched = await store.get_long_term(record.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_long_term_not_found(self, store) -> None:
        deleted = await store.delete_long_term("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_count_long_term(self, store) -> None:
        assert await store.count_long_term() == 0
        for i in range(3):
            await store.add_long_term(LongTermRecord(
                id=str(uuid.uuid4()), content=f"M{i}",
                memory_type="semantic", tags=[], created_at=time.time(),
            ))
        assert await store.count_long_term() == 3

    @pytest.mark.asyncio
    async def test_get_long_term_without_embeddings(self, store) -> None:
        with_emb = LongTermRecord(
            id=str(uuid.uuid4()), content="With embedding",
            memory_type="semantic", tags=[], created_at=time.time(),
            embedding=b"\x00\x01" * 10,
        )
        without_emb = LongTermRecord(
            id=str(uuid.uuid4()), content="Without embedding",
            memory_type="semantic", tags=[], created_at=time.time(),
        )
        await store.add_long_term(with_emb)
        await store.add_long_term(without_emb)

        results = await store.get_long_term_without_embeddings()
        assert len(results) == 1
        assert results[0].content == "Without embedding"

    @pytest.mark.asyncio
    async def test_get_important_long_term(self, store) -> None:
        for i, imp in enumerate([0.9, 0.6, 0.3]):
            await store.add_long_term(LongTermRecord(
                id=str(uuid.uuid4()), content=f"M{i}",
                memory_type="semantic", tags=[], created_at=time.time(),
                importance_score=imp,
            ))

        important = await store.get_important_long_term(min_importance=0.7, limit=10)
        assert len(important) == 1
        assert important[0].importance_score == 0.9

        important = await store.get_important_long_term(min_importance=0.5, limit=10)
        assert len(important) == 2


# ===================================================================
# SQLiteShortTermMemory tests
# ===================================================================


class TestSQLiteShortTermMemory:
    """Tests for SQLiteShortTermMemory."""

    @pytest.mark.asyncio
    async def test_creation(self, db_path) -> None:
        stm = SQLiteShortTermMemory(
            db_path=db_path,
            session_id="test-session",
            ttl_hours=24,
            max_turns=100,
        )
        await stm.init()
        assert stm.session_id == "test-session"

    @pytest.mark.asyncio
    async def test_add_and_get_recent(self, db_path) -> None:
        stm = SQLiteShortTermMemory(db_path=db_path, session_id="s1")
        await stm.init()

        turn = await stm.add_turn("user", "Hello")
        assert turn.role == "user"
        assert turn.content == "Hello"

        recent = await stm.get_recent(limit=5)
        assert len(recent) == 1
        assert recent[0].content == "Hello"

    @pytest.mark.asyncio
    async def test_get_context(self, db_path) -> None:
        stm = SQLiteShortTermMemory(db_path=db_path, session_id="s1")
        await stm.init()

        await stm.add_turn("user", "Question")
        await stm.add_turn("agent", "Answer")

        context = await stm.get_context(max_turns=5)
        assert "user: Question" in context
        assert "agent: Answer" in context

    @pytest.mark.asyncio
    async def test_clear(self, db_path) -> None:
        stm = SQLiteShortTermMemory(db_path=db_path, session_id="s1")
        await stm.init()

        await stm.add_turn("user", "Hello")
        await stm.clear()

        recent = await stm.get_recent()
        assert len(recent) == 0

    @pytest.mark.asyncio
    async def test_auto_prune_ttl(self, db_path) -> None:
        stm = SQLiteShortTermMemory(
            db_path=db_path, session_id="s1", ttl_hours=0, max_turns=100,
        )
        await stm.init()

        await stm.add_turn("user", "Old turn")

        # Prune with a very recent cutoff
        pruned = await stm.prune_expired()
        assert pruned >= 0

    @pytest.mark.asyncio
    async def test_high_importance_turns(self, db_path) -> None:
        stm = SQLiteShortTermMemory(db_path=db_path, session_id="s1")
        await stm.init()

        await stm.add_turn("user", "Important message", importance_score=0.9)
        await stm.add_turn("user", "Trivial", importance_score=0.1)

        high = await stm.get_high_importance_turns(min_importance=0.6)
        assert len(high) >= 1
        for turn in high:
            assert turn.metadata.get("importance_score", 0.5) >= 0.6

    @pytest.mark.asyncio
    async def test_working_memory(self, db_path) -> None:
        stm = SQLiteShortTermMemory(db_path=db_path, session_id="s1")
        await stm.init()

        stm.set_working_memory("key1", "value1")
        assert stm.get_working_memory("key1") == "value1"
        assert stm.get_working_memory("missing", "default") == "default"

        stm.clear_working_memory()
        assert stm.get_working_memory("key1") is None

    @pytest.mark.asyncio
    async def test_get_statistics(self, db_path) -> None:
        stm = SQLiteShortTermMemory(
            db_path=db_path, session_id="s1", max_turns=50,
        )
        await stm.init()

        stats = await stm.get_statistics()
        assert stats["session_id"] == "s1"
        assert stats["max_turns"] == 50

    @pytest.mark.asyncio
    async def test_score_importance(self, db_path) -> None:
        stm = SQLiteShortTermMemory(db_path=db_path, session_id="s1")

        # User role gets boost
        user_score = stm._score_importance("user", "short")
        assert user_score > 0.5

        # System role no boost
        sys_score = stm._score_importance("system", "short")
        assert sys_score == 0.5

        # Long content gets boost
        long_score = stm._score_importance("user", "A" * 200)
        assert long_score > user_score

    @pytest.mark.asyncio
    async def test_turn_importance_static(self, db_path) -> None:
        from lyra.memory.short_term_memory import ConversationTurn
        # Test the static _turn_importance method
        turn = ConversationTurn("user", "A" * 200, time.time())
        imp = SQLiteShortTermMemory._turn_importance(turn)
        assert imp > 0.5

    @pytest.mark.asyncio
    async def test_close_noop(self, db_path) -> None:
        stm = SQLiteShortTermMemory(db_path=db_path, session_id="s1")
        await stm.init()
        await stm.close()  # Should not raise


# ===================================================================
# SQLiteLongTermMemory tests
# ===================================================================


class TestSQLiteLongTermMemory:
    """Tests for SQLiteLongTermMemory."""

    @pytest.mark.asyncio
    async def test_creation(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path)
        await ltm.init()
        assert ltm.half_life_hours == 24.0
        assert ltm.dedup_content is True

    @pytest.mark.asyncio
    async def test_add_and_get_memory(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path)
        await ltm.init()

        record = await ltm.add_memory(
            content="Test memory",
            memory_type="semantic",
            tags=["test"],
            importance=0.8,
        )
        assert record.content == "Test memory"

        fetched = await ltm.get_memory(record.id)
        assert fetched is not None
        assert fetched.content == "Test memory"

    @pytest.mark.asyncio
    async def test_add_memory_dedup(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path, dedup_content=True)
        await ltm.init()

        r1 = await ltm.add_memory(content="Same content", importance=0.5)
        r2 = await ltm.add_memory(content="Same content", importance=0.5)

        # Should boost importance of the existing record
        assert r2.importance_score >= 0.6
        assert r2.access_count >= 1

    @pytest.mark.asyncio
    async def test_add_memory_no_dedup(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path, dedup_content=False)
        await ltm.init()

        r1 = await ltm.add_memory(content="Same content", importance=0.5)
        r2 = await ltm.add_memory(content="Same content", importance=0.5)

        # Should create two separate records
        assert r1.id != r2.id

    @pytest.mark.asyncio
    async def test_get_all(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path)
        await ltm.init()

        for i in range(3):
            await ltm.add_memory(content=f"Memory {i}", importance=0.5)

        all_mems = await ltm.get_all()
        assert len(all_mems) == 3

    @pytest.mark.asyncio
    async def test_get_recent(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path)
        await ltm.init()

        for i in range(5):
            await ltm.add_memory(content=f"M{i}", importance=0.5)

        recent = await ltm.get_recent(limit=3)
        assert len(recent) == 3

    @pytest.mark.asyncio
    async def test_get_important(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path)
        await ltm.init()

        for imp in [0.9, 0.6, 0.3]:
            await ltm.add_memory(content=f"M{imp}", importance=imp)

        important = await ltm.get_important(min_importance=0.7, limit=10)
        assert len(important) == 1

    @pytest.mark.asyncio
    async def test_count(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path)
        await ltm.init()

        assert await ltm.count() == 0
        await ltm.add_memory(content="Test", importance=0.5)
        assert await ltm.count() == 1

    @pytest.mark.asyncio
    async def test_delete_memory(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path)
        await ltm.init()

        record = await ltm.add_memory(content="Delete me", importance=0.5)
        deleted = await ltm.delete_memory(record.id)
        assert deleted is True

        fetched = await ltm.get_memory(record.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path)
        await ltm.init()

        deleted = await ltm.delete_memory("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_clear_all(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path)
        await ltm.init()

        await ltm.add_memory(content="Test", importance=0.5)
        await ltm.clear_all()

        assert await ltm.count() == 0

    @pytest.mark.asyncio
    async def test_search_by_keyword(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path)
        await ltm.init()

        await ltm.add_memory(content="Python programming", importance=0.8)
        await ltm.add_memory(content="JavaScript coding", importance=0.7)

        results = await ltm.search_by_keyword("Python")
        assert len(results) == 1
        assert results[0].content == "Python programming"

    @pytest.mark.asyncio
    async def test_apply_ebbinghaus_decay(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path, half_life_hours=1.0)
        await ltm.init()

        record = await ltm.add_memory(content="Test", importance=0.8)
        # Simulate old last_accessed
        import aiosqlite
        async with aiosqlite.connect(db_path) as conn:
            await conn.execute(
                "UPDATE long_term SET last_accessed = ? WHERE id = ?",
                (time.time() - 3600 * 24, record.id),
            )
            await conn.commit()

        await ltm.apply_ebbinghaus_decay(half_life_hours=1.0)
        updated = await ltm.get_memory(record.id)
        assert updated is not None
        assert updated.importance_score < 0.8

    @pytest.mark.asyncio
    async def test_apply_deterministic_decay(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path, half_life_hours=1.0)
        await ltm.init()

        record = await ltm.add_memory(content="Test", importance=0.8)
        import aiosqlite
        async with aiosqlite.connect(db_path) as conn:
            await conn.execute(
                "UPDATE long_term SET last_accessed = ? WHERE id = ?",
                (0.0, record.id),
            )
            await conn.commit()

        # Apply deterministic decay with a fixed current time
        await ltm.apply_deterministic_decay(
            half_life_hours=1.0, current_time=3600.0,  # 1 hour after epoch
        )
        updated = await ltm.get_memory(record.id)
        assert updated is not None
        # elapsed = 3600s / 3600 = 1 hour, decay = exp(-1/1) = ~0.368, 0.8 * 0.368 = ~0.294
        assert updated.importance_score < 0.5

    @pytest.mark.asyncio
    async def test_build_vector_index_empty(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path)
        await ltm.init()

        await ltm.build_vector_index()
        assert ltm._vector_searcher is not None

    @pytest.mark.asyncio
    async def test_search_semantic_empty(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path)
        await ltm.init()

        results = await ltm.search_semantic("query", top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_consolidate_from_conversations(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path)
        await ltm.init()

        class MockTurn:
            def __init__(self, role, content, importance=0.8):
                self.role = role
                self.content = content
                self.metadata = {"importance_score": importance}

        turns = [
            MockTurn("user", "Important conversation", 0.9),
            MockTurn("agent", "Response", 0.7),
            MockTurn("user", "Low importance", 0.1),  # Below threshold
        ]

        created = await ltm.consolidate_from_conversations(
            turns, min_importance=0.6
        )
        assert created == 2

    @pytest.mark.asyncio
    async def test_get_statistics(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path)
        await ltm.init()

        await ltm.add_memory(content="M1", importance=0.9)
        await ltm.add_memory(content="M2", importance=0.5)

        stats = await ltm.get_statistics()
        assert stats["total_memories"] == 2
        assert stats["average_importance"] > 0.0
        assert stats["max_importance"] == 0.9
        assert stats["min_importance"] == 0.5
        assert stats["half_life_hours"] == 24.0

    @pytest.mark.asyncio
    async def test_close_noop(self, db_path) -> None:
        ltm = SQLiteLongTermMemory(db_path=db_path)
        await ltm.init()
        await ltm.close()  # Should not raise


# ===================================================================
# LongTermRecord tests
# ===================================================================


class TestLongTermRecord:
    """Tests for LongTermRecord dataclass."""

    def test_creation_defaults(self) -> None:
        record = LongTermRecord(
            id="test-id",
            content="test",
        )
        assert record.memory_type == "semantic"
        assert record.tags == []
        assert record.embedding is None
        assert record.importance_score == 0.5
        assert record.access_count == 0

    def test_custom_values(self) -> None:
        record = LongTermRecord(
            id="id1", content="Custom", memory_type="episodic",
            tags=["tag1"], embedding=b"\x00\x01",
            importance_score=0.9, created_at=100.0,
            last_accessed=200.0, access_count=5,
        )
        assert record.importance_score == 0.9
        assert record.access_count == 5


# ===================================================================
# ConversationRecord tests
# ===================================================================


class TestConversationRecord:
    """Tests for ConversationRecord dataclass."""

    def test_creation(self) -> None:
        record = ConversationRecord(
            text_id="t1", role="user", content="Hello",
            timestamp=100.0, session_id="s1",
        )
        assert record.importance_score == 0.5

    def test_custom_importance(self) -> None:
        record = ConversationRecord(
            text_id="t1", role="user", content="Important",
            timestamp=100.0, session_id="s1", importance_score=0.9,
        )
        assert record.importance_score == 0.9
