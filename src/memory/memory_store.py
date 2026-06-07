"""
Memory Store - Core storage for agent memories.

Supports both in-memory (dict) and SQLite-backed persistence.
"""

import json
import math
import pickle
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import aiosqlite


class MemoryType(Enum):
    """Types of memories."""
    EPISODIC = "episodic"      # Specific events and experiences
    SEMANTIC = "semantic"      # General knowledge and facts
    PROCEDURAL = "procedural"  # How to perform tasks


@dataclass
class Memory:
    """
    A single memory entry.

    Attributes:
        memory_id: Unique identifier
        content: Memory content
        memory_type: Type of memory
        timestamp: When memory was created
        importance: Importance score (0.0 - 1.0)
        tags: Associated tags
        context: Additional context
        access_count: Number of times accessed
        last_accessed: Last access timestamp
    """
    memory_id: str
    content: str
    memory_type: MemoryType
    timestamp: float
    importance: float = 0.5
    tags: list[str] = None
    context: dict[str, Any] = None
    access_count: int = 0
    last_accessed: float = 0.0

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.context is None:
            self.context = {}
        if self.last_accessed == 0.0:
            self.last_accessed = self.timestamp

    def to_dict(self) -> dict:
        """Convert memory to dictionary."""
        data = asdict(self)
        data["memory_type"] = self.memory_type.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Memory":
        """Create memory from dictionary."""
        data = data.copy()
        data["memory_type"] = MemoryType(data["memory_type"])
        return cls(**data)

    def access(self):
        """Record memory access."""
        self.access_count += 1
        self.last_accessed = time.time()

    def decay_importance(self, decay_rate: float = 0.01):
        """
        Decay importance over time.

        Args:
            decay_rate: Rate of decay per day
        """
        days_since_access = (time.time() - self.last_accessed) / 86400
        decay = decay_rate * days_since_access
        self.importance = max(0.0, self.importance - decay)

    def ebbinghaus_decay(self, half_life_hours: float = 24.0):
        """
        Apply Ebbinghaus forgetting curve decay.

        The forgetting curve: R = e^(-t/s)
        where R is retention, t is elapsed time, s is memory strength.

        Args:
            half_life_hours: Hours after which importance is halved.
        """
        elapsed_hours = (time.time() - self.last_accessed) / 3600
        decay_factor = math.exp(-elapsed_hours / half_life_hours)
        self.importance = max(0.0, self.importance * decay_factor)


class MemoryStore:
    """
    Core storage for memories.

    Responsibilities:
    - Store and retrieve memories
    - Manage memory lifecycle
    - Persist memories to disk
    - Apply importance decay
    """

    def __init__(self, storage_path: str | None = None):
        """
        Initialize memory store.

        Args:
            storage_path: Path to persist memories (optional)
        """
        self.memories: dict[str, Memory] = {}
        self.storage_path = storage_path

        if storage_path:
            self.load()

    def add(
        self,
        content: str,
        memory_type: MemoryType,
        importance: float = 0.5,
        tags: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> Memory:
        """
        Add a new memory.

        Args:
            content: Memory content
            memory_type: Type of memory
            importance: Importance score (0.0 - 1.0)
            tags: Associated tags
            context: Additional context

        Returns:
            Created memory
        """
        memory = Memory(
            memory_id=str(uuid.uuid4()),
            content=content,
            memory_type=memory_type,
            timestamp=time.time(),
            importance=importance,
            tags=tags or [],
            context=context or {},
        )

        self.memories[memory.memory_id] = memory
        return memory

    def get(self, memory_id: str) -> Memory | None:
        """
        Get a memory by ID.

        Args:
            memory_id: Memory identifier

        Returns:
            Memory if found, None otherwise
        """
        memory = self.memories.get(memory_id)
        if memory:
            memory.access()
        return memory

    def update(self, memory_id: str, **kwargs) -> bool:
        """
        Update a memory.

        Args:
            memory_id: Memory identifier
            **kwargs: Fields to update

        Returns:
            True if updated, False if not found
        """
        memory = self.memories.get(memory_id)
        if not memory:
            return False

        for key, value in kwargs.items():
            if hasattr(memory, key):
                setattr(memory, key, value)

        return True

    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory.

        Args:
            memory_id: Memory identifier

        Returns:
            True if deleted, False if not found
        """
        if memory_id in self.memories:
            del self.memories[memory_id]
            return True
        return False

    def get_all(self) -> list[Memory]:
        """
        Get all memories.

        Returns:
            List of all memories
        """
        return list(self.memories.values())

    def get_by_type(self, memory_type: MemoryType) -> list[Memory]:
        """
        Get memories by type.

        Args:
            memory_type: Type to filter by

        Returns:
            List of memories of specified type
        """
        return [
            m for m in self.memories.values()
            if m.memory_type == memory_type
        ]

    def get_by_tags(self, tags: list[str], match_all: bool = False) -> list[Memory]:
        """
        Get memories by tags.

        Args:
            tags: Tags to search for
            match_all: If True, memory must have all tags

        Returns:
            List of matching memories
        """
        if match_all:
            return [
                m for m in self.memories.values()
                if all(tag in m.tags for tag in tags)
            ]
        else:
            return [
                m for m in self.memories.values()
                if any(tag in m.tags for tag in tags)
            ]

    def get_recent(self, limit: int = 10) -> list[Memory]:
        """
        Get most recent memories.

        Args:
            limit: Maximum number to return

        Returns:
            List of recent memories
        """
        sorted_memories = sorted(
            self.memories.values(),
            key=lambda m: m.timestamp,
            reverse=True
        )
        return sorted_memories[:limit]

    def get_important(self, threshold: float = 0.7, limit: int = 10) -> list[Memory]:
        """
        Get most important memories.

        Args:
            threshold: Minimum importance score
            limit: Maximum number to return

        Returns:
            List of important memories
        """
        important = [
            m for m in self.memories.values()
            if m.importance >= threshold
        ]
        sorted_important = sorted(
            important,
            key=lambda m: m.importance,
            reverse=True
        )
        return sorted_important[:limit]

    def apply_decay(self, decay_rate: float = 0.01):
        """
        Apply importance decay to all memories.

        Args:
            decay_rate: Rate of decay per day
        """
        for memory in self.memories.values():
            memory.decay_importance(decay_rate)

    def apply_ebbinghaus_decay(self, half_life_hours: float = 24.0):
        """
        Apply Ebbinghaus forgetting curve decay to all memories.

        Args:
            half_life_hours: Hours after which importance is halved.
        """
        for memory in self.memories.values():
            memory.ebbinghaus_decay(half_life_hours)

    def prune(self, min_importance: float = 0.1):
        """
        Remove memories below importance threshold.

        Args:
            min_importance: Minimum importance to keep

        Returns:
            Number of memories pruned
        """
        to_remove = [
            mid for mid, m in self.memories.items()
            if m.importance < min_importance
        ]

        for mid in to_remove:
            del self.memories[mid]

        return len(to_remove)

    def save(self):
        """Save memories to disk."""
        if not self.storage_path:
            return

        path = Path(self.storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "memories": [m.to_dict() for m in self.memories.values()]
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self):
        """Load memories from disk."""
        if not self.storage_path:
            return

        path = Path(self.storage_path)
        if not path.exists():
            return

        with open(path) as f:
            data = json.load(f)

        self.memories = {}
        for mem_data in data.get("memories", []):
            memory = Memory.from_dict(mem_data)
            self.memories[memory.memory_id] = memory

    def clear(self):
        """Clear all memories."""
        self.memories.clear()

    def get_statistics(self) -> dict:
        """
        Get memory statistics.

        Returns:
            Statistics dictionary
        """
        if not self.memories:
            return {
                "total_memories": 0,
                "by_type": {},
                "average_importance": 0.0,
                "total_accesses": 0,
            }

        by_type = {}
        for memory in self.memories.values():
            mtype = memory.memory_type.value
            by_type[mtype] = by_type.get(mtype, 0) + 1

        total_importance = sum(m.importance for m in self.memories.values())
        total_accesses = sum(m.access_count for m in self.memories.values())

        return {
            "total_memories": len(self.memories),
            "by_type": by_type,
            "average_importance": total_importance / len(self.memories),
            "total_accesses": total_accesses,
            "average_accesses": total_accesses / len(self.memories),
        }


# =============================================================================
# SQLite-backed persistence layer
# =============================================================================

CONVERSATIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    text_id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp REAL NOT NULL,
    session_id TEXT NOT NULL,
    importance_score REAL DEFAULT 0.5
);
CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conv_ts ON conversations(timestamp);
"""

LONG_TERM_SCHEMA = """
CREATE TABLE IF NOT EXISTS long_term (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    memory_type TEXT DEFAULT 'semantic',
    tags TEXT DEFAULT '[]',
    embedding BLOB,
    importance_score REAL DEFAULT 0.5,
    created_at REAL NOT NULL,
    last_accessed REAL DEFAULT 0.0,
    access_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_lt_created ON long_term(created_at);
CREATE INDEX IF NOT EXISTS idx_lt_accessed ON long_term(last_accessed);
CREATE INDEX IF NOT EXISTS idx_lt_importance ON long_term(importance_score);
"""


@dataclass
class ConversationRecord:
    """A conversation turn stored in the SQLite conversations table."""
    text_id: str
    role: str
    content: str
    timestamp: float
    session_id: str
    importance_score: float = 0.5


@dataclass
class LongTermRecord:
    """A long-term memory entry stored in the SQLite long_term table."""
    id: str
    content: str
    memory_type: str = "semantic"
    tags: list[str] = field(default_factory=list)
    embedding: bytes | None = None
    importance_score: float = 0.5
    created_at: float = 0.0
    last_accessed: float = 0.0
    access_count: int = 0


class SQLiteStore:
    """
    SQLite-backed persistent store for agent memory.

    Manages two tables:
      - ``conversations`` — short-term / conversation turn storage (STM)
      - ``long_term``     — consolidated long-term memories (LTM) with optional
                            embedding blobs for semantic search.

    Thread-safe via aiosqlite (each operation opens its own connection).
    """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        """Create tables and indexes if they do not exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("BEGIN;")
            await db.executescript(CONVERSATIONS_SCHEMA)
            await db.executescript(LONG_TERM_SCHEMA)
            await db.commit()

    async def close(self):
        """No-op for aiosqlite (connections are managed by ``async with``)."""
        pass

    # ------------------------------------------------------------------
    # Conversations (STM)
    # ------------------------------------------------------------------

    async def add_conversation(self, record: ConversationRecord):
        """Insert or replace a conversation turn."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO conversations
                   (text_id, role, content, timestamp, session_id, importance_score)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (record.text_id, record.role, record.content,
                 record.timestamp, record.session_id, record.importance_score),
            )
            await db.commit()

    async def get_conversations(
        self,
        session_id: str,
        limit: int = 50,
        since: float | None = None,
    ) -> list[ConversationRecord]:
        """Return the most recent conversation turns for *session_id*."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if since is not None:
                cursor = await db.execute(
                    """SELECT text_id, role, content, timestamp, session_id,
                              importance_score
                       FROM conversations
                       WHERE session_id = ? AND timestamp >= ?
                       ORDER BY timestamp DESC LIMIT ?""",
                    (session_id, since, limit),
                )
            else:
                cursor = await db.execute(
                    """SELECT text_id, role, content, timestamp, session_id,
                              importance_score
                       FROM conversations
                       WHERE session_id = ?
                       ORDER BY timestamp DESC LIMIT ?""",
                    (session_id, limit),
                )
            rows = await cursor.fetchall()
            return [_conv_from_row(r) for r in rows]

    async def delete_conversations_by_session(self, session_id: str):
        """Delete all conversation turns for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM conversations WHERE session_id = ?", (session_id,),
            )
            await db.commit()

    async def prune_conversations(self, before_timestamp: float) -> int:
        """Delete conversation turns older than *before_timestamp*.

        Returns the number of rows deleted.
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM conversations WHERE timestamp < ?", (before_timestamp,),
            )
            await db.commit()
            return cursor.rowcount

    async def count_conversations(self, session_id: str | None = None) -> int:
        """Return the number of conversation rows (optionally filtered by session)."""
        async with aiosqlite.connect(self.db_path) as db:
            if session_id:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM conversations WHERE session_id = ?",
                    (session_id,),
                )
            else:
                cursor = await db.execute("SELECT COUNT(*) FROM conversations")
            row = await cursor.fetchone()
            return row[0] if row else 0

    # ------------------------------------------------------------------
    # Long-term table
    # ------------------------------------------------------------------

    async def add_long_term(self, record: LongTermRecord):
        """Insert or replace a long-term memory."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO long_term
                   (id, content, memory_type, tags, embedding,
                    importance_score, created_at, last_accessed, access_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (record.id, record.content, record.memory_type,
                 json.dumps(record.tags), record.embedding,
                 record.importance_score, record.created_at,
                 record.last_accessed, record.access_count),
            )
            await db.commit()

    async def get_long_term(self, id: str) -> LongTermRecord | None:
        """Fetch a single long-term memory by ID, or return ``None``."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, content, memory_type, tags, embedding,
                          importance_score, created_at, last_accessed, access_count
                   FROM long_term WHERE id = ?""",
                (id,),
            )
            row = await cursor.fetchone()
            return _lt_from_row(row) if row else None

    async def get_all_long_term(self) -> list[LongTermRecord]:
        """Return all long-term memories, newest-first."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, content, memory_type, tags, embedding,
                          importance_score, created_at, last_accessed, access_count
                   FROM long_term ORDER BY created_at DESC""",
            )
            rows = await cursor.fetchall()
            return [_lt_from_row(r) for r in rows]

    async def search_long_term_keyword(self, query: str) -> list[LongTermRecord]:
        """SQL ``LIKE`` search across *content*."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, content, memory_type, tags, embedding,
                          importance_score, created_at, last_accessed, access_count
                   FROM long_term WHERE content LIKE ?""",
                (f"%{query}%",),
            )
            rows = await cursor.fetchall()
            return [_lt_from_row(r) for r in rows]

    async def get_long_term_recent(self, limit: int = 10) -> list[LongTermRecord]:
        """Return the *limit* most recent long-term memories."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, content, memory_type, tags, embedding,
                          importance_score, created_at, last_accessed, access_count
                   FROM long_term ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [_lt_from_row(r) for r in rows]

    async def update_long_term_access(self, id: str):
        """Bump access_count and last_accessed for *id*."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE long_term SET last_accessed = ?, access_count = access_count + 1 WHERE id = ?",
                (time.time(), id),
            )
            await db.commit()

    async def update_long_term_importance(self, id: str, importance: float):
        """Update the importance_score of a single record."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE long_term SET importance_score = ? WHERE id = ?",
                (importance, id),
            )
            await db.commit()

    async def delete_long_term(self, id: str) -> bool:
        """Delete a long-term memory by ID. Returns ``True`` if a row was removed."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM long_term WHERE id = ?", (id,),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def count_long_term(self) -> int:
        """Return the total number of long-term memories."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM long_term")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_long_term_without_embeddings(self) -> list[LongTermRecord]:
        """Return LTM records whose embedding column is ``NULL``."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, content, memory_type, tags, embedding,
                          importance_score, created_at, last_accessed, access_count
                   FROM long_term WHERE embedding IS NULL""",
            )
            rows = await cursor.fetchall()
            return [_lt_from_row(r) for r in rows]

    async def get_important_long_term(self, min_importance: float = 0.7, limit: int = 20) -> list[LongTermRecord]:
        """Return LTM records with importance_score >= *min_importance*, sorted descending."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, content, memory_type, tags, embedding,
                          importance_score, created_at, last_accessed, access_count
                   FROM long_term WHERE importance_score >= ?
                   ORDER BY importance_score DESC LIMIT ?""",
                (min_importance, limit),
            )
            rows = await cursor.fetchall()
            return [_lt_from_row(r) for r in rows]


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _conv_from_row(row: aiosqlite.Row) -> ConversationRecord:
    return ConversationRecord(
        text_id=row["text_id"],
        role=row["role"],
        content=row["content"],
        timestamp=row["timestamp"],
        session_id=row["session_id"],
        importance_score=row["importance_score"],
    )


def _lt_from_row(row: aiosqlite.Row) -> LongTermRecord:
    return LongTermRecord(
        id=row["id"],
        content=row["content"],
        memory_type=row["memory_type"],
        tags=json.loads(row["tags"]) if row["tags"] else [],
        embedding=row["embedding"],
        importance_score=row["importance_score"],
        created_at=row["created_at"],
        last_accessed=row["last_accessed"],
        access_count=row["access_count"],
    )
