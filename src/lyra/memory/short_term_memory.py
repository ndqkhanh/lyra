"""
Short-Term Memory — recent conversation context.

Provides two implementations:

* ``ShortTermMemory`` — original in-memory deque-based store.
* ``SQLiteShortTermMemory`` — SQLite-backed store with session-scoped TTL
  and automatic pruning of expired entries.
"""

import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Any

from lyra.memory.memory_store import ConversationRecord, MemoryStore, MemoryType, SQLiteStore


# =============================================================================
# Shared data types
# =============================================================================


@dataclass
class ConversationTurn:
    """
    A single conversation turn.

    Attributes:
        role: Speaker role (user, agent, system)
        content: Turn content
        timestamp: When turn occurred
        metadata: Additional metadata
    """
    role: str
    content: str
    timestamp: float
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# =============================================================================
# In-memory ShortTermMemory (original)
# =============================================================================


class ShortTermMemory:
    """
    Short-term memory for recent context (in-memory deque).

    Responsibilities:
    - Store recent conversation turns
    - Maintain fixed-size buffer
    - Provide quick access to recent context
    - Consolidate to long-term memory
    """

    def __init__(
        self,
        capacity: int = 10,
        consolidation_threshold: int = 5,
    ):
        """
        Initialize short-term memory.

        Args:
            capacity: Maximum number of turns to keep
            consolidation_threshold: When to trigger consolidation
        """
        self.capacity = capacity
        self.consolidation_threshold = consolidation_threshold
        self.turns: deque = deque(maxlen=capacity)
        self.working_memory: dict[str, Any] = {}

    def add_turn(
        self,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationTurn:
        """Add a conversation turn."""
        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=metadata or {},
        )
        self.turns.append(turn)
        return turn

    def get_recent(self, limit: int | None = None) -> list[ConversationTurn]:
        """Get recent turns."""
        if limit is None:
            return list(self.turns)
        return list(self.turns)[-limit:]

    def get_context(self, max_turns: int | None = None) -> str:
        """Get conversation context as string."""
        turns = self.get_recent(max_turns)
        lines = [f"{turn.role}: {turn.content}" for turn in turns]
        return "\n".join(lines)

    def get_by_role(self, role: str) -> list[ConversationTurn]:
        """Get turns by role."""
        return [turn for turn in self.turns if turn.role == role]

    def set_working_memory(self, key: str, value: Any):
        """Set working memory value."""
        self.working_memory[key] = value

    def get_working_memory(self, key: str, default: Any = None) -> Any:
        """Get working memory value."""
        return self.working_memory.get(key, default)

    def clear_working_memory(self):
        """Clear working memory."""
        self.working_memory.clear()

    def should_consolidate(self) -> bool:
        """Check if consolidation should occur."""
        return len(self.turns) >= self.consolidation_threshold

    def prepare_for_consolidation(self) -> list[ConversationTurn]:
        """Get turns ready for consolidation (oldest half)."""
        consolidate_count = len(self.turns) // 2
        return list(self.turns)[:consolidate_count]

    def consolidate_to_long_term(
        self,
        long_term_store: MemoryStore,
        importance_threshold: float = 0.5,
    ) -> int:
        """Consolidate turns to long-term memory."""
        if not self.should_consolidate():
            return 0
        turns_to_consolidate = self.prepare_for_consolidation()
        consolidated = 0
        for turn in turns_to_consolidate:
            importance = self._calculate_importance(turn)
            if importance >= importance_threshold:
                long_term_store.add(
                    content=f"{turn.role}: {turn.content}",
                    memory_type=MemoryType.EPISODIC,
                    importance=importance,
                    tags=[turn.role, "conversation"],
                    context={"timestamp": turn.timestamp, "metadata": turn.metadata},
                )
                consolidated += 1
        return consolidated

    def _calculate_importance(self, turn: ConversationTurn) -> float:
        """Calculate importance of a turn (0.0 - 1.0)."""
        importance = 0.5
        if turn.role == "user":
            importance += 0.2
        content_length = len(turn.content)
        if content_length > 100:
            importance += 0.1
        if content_length > 500:
            importance += 0.1
        if turn.metadata.get("important"):
            importance += 0.2
        return min(1.0, importance)

    def clear(self):
        """Clear all turns."""
        self.turns.clear()
        self.working_memory.clear()

    def get_statistics(self) -> dict:
        """Get short-term memory statistics."""
        if not self.turns:
            return {"total_turns": 0, "capacity": self.capacity, "utilization": 0.0, "by_role": {}}
        by_role = {}
        for turn in self.turns:
            by_role[turn.role] = by_role.get(turn.role, 0) + 1
        return {
            "total_turns": len(self.turns),
            "capacity": self.capacity,
            "utilization": len(self.turns) / self.capacity if self.capacity else 0.0,
            "by_role": by_role,
            "working_memory_keys": len(self.working_memory),
            "should_consolidate": self.should_consolidate(),
        }


# =============================================================================
# SQLite-backed ShortTermMemory
# =============================================================================


class SQLiteShortTermMemory:
    """
    SQLite-backed short-term memory with session-scoped TTL.

    Conversation turns are persisted in the ``conversations`` table and
    automatically pruned after the configured TTL (default 24 hours).

    Parameters:
        db_path: Path to the SQLite database file.
        session_id: Logical session identifier.
        ttl_hours: TTL in hours; entries older than this are pruned.
        max_turns: Soft cap — only this many most-recent turns are kept
                   (older excess is pruned on each ``add_turn`` / ``prune``).
        importance_threshold: Minimum importance for automatic consolidation.
    """

    def __init__(
        self,
        db_path: str,
        session_id: str,
        ttl_hours: int = 24,
        max_turns: int = 100,
        importance_threshold: float = 0.5,
    ):
        self.db = SQLiteStore(db_path)
        self.session_id = session_id
        self.ttl_hours = ttl_hours
        self.max_turns = max_turns
        self.importance_threshold = importance_threshold
        self.working_memory: dict[str, Any] = {}

    async def init(self):
        """Ensure SQLite tables exist."""
        await self.db.init_db()

    async def close(self):
        """No-op; connections are short-lived in SQLiteStore."""
        pass

    # ------------------------------------------------------------------
    # Turn management
    # ------------------------------------------------------------------

    async def add_turn(
        self,
        role: str,
        content: str,
        importance_score: float | None = None,
    ) -> ConversationTurn:
        """Persist a conversation turn and auto-prune stale entries."""
        if importance_score is None:
            importance_score = self._score_importance(role, content)

        record = ConversationRecord(
            text_id=str(uuid.uuid4()),
            role=role,
            content=content,
            timestamp=time.time(),
            session_id=self.session_id,
            importance_score=importance_score,
        )
        await self.db.add_conversation(record)
        await self._auto_prune()

        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=record.timestamp,
            metadata={"text_id": record.text_id, "importance_score": importance_score},
        )
        return turn

    async def get_recent(self, limit: int = 10) -> list[ConversationTurn]:
        """Return the most recent conversation turns."""
        records = await self.db.get_conversations(
            session_id=self.session_id, limit=limit,
        )
        return [self._record_to_turn(r) for r in reversed(records)]

    async def get_context(self, max_turns: int = 10) -> str:
        """Return formatted context string from recent turns."""
        turns = await self.get_recent(limit=max_turns)
        return "\n".join(f"{t.role}: {t.content}" for t in turns)

    async def clear(self):
        """Delete all turns for this session from SQLite."""
        await self.db.delete_conversations_by_session(self.session_id)

    # ------------------------------------------------------------------
    # TTL & pruning
    # ------------------------------------------------------------------

    async def _auto_prune(self):
        """Prune expired (by TTL) turns and cap to ``max_turns``."""
        cutoff = time.time() - (self.ttl_hours * 3600)

        # 1. Remove entries older than TTL
        await self.db.prune_conversations(cutoff)

        # 2. Keep only the most recent max_turns — delete older excess per session
        records = await self.db.get_conversations(
            session_id=self.session_id, limit=self.max_turns * 2,
        )
        if len(records) > self.max_turns:
            # Find the timestamp of the max_turns-th (from the youngest side)
            # records are returned newest-first, so the *last* element is oldest
            excess_threshold = records[self.max_turns - 1].timestamp
            # Delete turns older than the threshold
            await self.db.prune_conversations(excess_threshold)

    async def prune_expired(self) -> int:
        """Explicitly prune entries beyond TTL. Returns row count removed."""
        cutoff = time.time() - (self.ttl_hours * 3600)
        return await self.db.prune_conversations(cutoff)

    # ------------------------------------------------------------------
    # Consolidation helpers
    # ------------------------------------------------------------------

    async def get_high_importance_turns(
        self,
        min_importance: float = 0.6,
        limit: int = 20,
    ) -> list[ConversationTurn]:
        """Return turns whose importance_score is at least *min_importance*."""
        records = await self.db.get_conversations(
            session_id=self.session_id, limit=limit,
        )
        result = []
        for r in records:
            if r.importance_score >= min_importance:
                result.append(self._record_to_turn(r))
        return result

    def _score_importance(self, role: str, content: str) -> float:
        """Heuristic importance score for a turn."""
        score = 0.5
        if role == "user":
            score += 0.2
        length = len(content)
        if length > 100:
            score += 0.1
        if length > 500:
            score += 0.1
        return min(1.0, score)

    # ------------------------------------------------------------------
    # Working memory (still in-memory)
    # ------------------------------------------------------------------

    def set_working_memory(self, key: str, value: Any):
        self.working_memory[key] = value

    def get_working_memory(self, key: str, default: Any = None) -> Any:
        return self.working_memory.get(key, default)

    def clear_working_memory(self):
        self.working_memory.clear()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    async def get_statistics(self) -> dict:
        """Get STM statistics from the SQLite backend."""
        count = await self.db.count_conversations(self.session_id)
        return {
            "session_id": self.session_id,
            "total_turns": count,
            "max_turns": self.max_turns,
            "ttl_hours": self.ttl_hours,
            "working_memory_keys": len(self.working_memory),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _record_to_turn(r: ConversationRecord) -> ConversationTurn:
        return ConversationTurn(
            role=r.role,
            content=r.content,
            timestamp=r.timestamp,
            metadata={"text_id": r.text_id, "importance_score": r.importance_score},
        )

    @staticmethod
    def _turn_importance(turn: ConversationTurn) -> float:
        """Retrieve stored importance from turn metadata, or use heuristic."""
        imp = turn.metadata.get("importance_score")
        if imp is not None:
            return imp
        score = 0.5
        if turn.role == "user":
            score += 0.2
        if len(turn.content) > 100:
            score += 0.1
        if len(turn.content) > 500:
            score += 0.1
        return min(1.0, score)
