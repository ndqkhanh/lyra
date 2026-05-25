"""L1 Episodic Memory — Session events stored in SQLite+FTS5.

Stores episodic events with full-text search, time-range queries,
agent-filtered queries, and symbolic compression of tool logs.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lyra_memory_stack.exceptions import MemoryNotFoundError


@dataclass(frozen=True)
class EpisodeEvent:
    """A single episodic event captured during a session."""

    event_id: str
    agent_id: str
    event_type: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    session_id: str = ""


@dataclass(frozen=True)
class SearchResult:
    """A search result from the episodic memory store."""

    event: EpisodeEvent
    rank: float  # relevance score
    snippet: str = ""


class EpisodicMemory:
    """SQLite+FTS5-backed episodic memory store.

    Events are stored with a structured schema including id, timestamp,
    agent_id, event_type, content, and metadata (JSON). Supports FTS5
    full-text search over event content and time-range queries.
    """

    _db_path: Path
    _conn: sqlite3.Connection

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._db_path = Path(db_path) if db_path != ":memory:" else Path(":memory:")
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize the database schema with FTS5 virtual table."""
        cur = self._conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS episodes (
                event_id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                agent_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                session_id TEXT DEFAULT ''
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
                content, event_type,
                content='episodes', content_rowid='rowid'
            );
            CREATE INDEX IF NOT EXISTS idx_episodes_timestamp ON episodes(timestamp);
            CREATE INDEX IF NOT EXISTS idx_episodes_agent ON episodes(agent_id);
            CREATE INDEX IF NOT EXISTS idx_episodes_type ON episodes(event_type);
            CREATE INDEX IF NOT EXISTS idx_episodes_session ON episodes(session_id);
        """)
        self._conn.commit()

    def store(self, event: EpisodeEvent) -> None:
        """Store an episodic event."""
        cur = self._conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO episodes
               (event_id, timestamp, agent_id, event_type, content, metadata, session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                event.event_id,
                event.timestamp,
                event.agent_id,
                event.event_type,
                event.content,
                json.dumps(event.metadata),
                event.session_id,
            ),
        )
        # Sync FTS index
        cur.execute(
            """INSERT INTO episodes_fts(rowid, content, event_type)
               VALUES (last_insert_rowid(), ?, ?)""",
            (event.content, event.event_type),
        )
        self._conn.commit()

    def retrieve(self, event_id: str) -> EpisodeEvent:
        """Retrieve an event by ID. Raises MemoryNotFoundError if missing."""
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM episodes WHERE event_id = ?", (event_id,))
        row = cur.fetchone()
        if row is None:
            raise MemoryNotFoundError(event_id, "episodic")
        return self._row_to_event(row)

    def delete(self, event_id: str) -> bool:
        """Delete an event by ID. Returns True if deleted."""
        cur = self._conn.cursor()
        cur.execute("SELECT rowid FROM episodes WHERE event_id = ?", (event_id,))
        row = cur.fetchone()
        if row is None:
            return False
        old_rowid = row["rowid"]
        cur.execute("DELETE FROM episodes WHERE event_id = ?", (event_id,))
        cur.execute("DELETE FROM episodes_fts WHERE rowid = ?", (old_rowid,))
        self._conn.commit()
        return True

    def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Full-text search over episode content using FTS5."""
        cur = self._conn.cursor()
        try:
            cur.execute(
                """SELECT episodes.*, rank
                   FROM episodes_fts
                   JOIN episodes ON episodes.rowid = episodes_fts.rowid
                   WHERE episodes_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (query, limit),
            )
        except sqlite3.OperationalError:
            # Fallback to LIKE search if FTS5 fails
            return self._search_like(query, limit)

        results: list[SearchResult] = []
        for row in cur.fetchall():
            event = self._row_to_event(row)
            results.append(SearchResult(
                event=event,
                rank=row["rank"] if "rank" in row.keys() else 0.0,
                snippet=self._make_snippet(event.content, query),
            ))
        return results

    def _search_like(self, query: str, limit: int = 20) -> list[SearchResult]:
        """Fallback LIKE-based search."""
        cur = self._conn.cursor()
        like_pattern = f"%{query}%"
        cur.execute(
            """SELECT * FROM episodes
               WHERE content LIKE ? OR event_type LIKE ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (like_pattern, like_pattern, limit),
        )
        results: list[SearchResult] = []
        for row in cur.fetchall():
            event = self._row_to_event(row)
            results.append(SearchResult(
                event=event,
                rank=0.5,
                snippet=self._make_snippet(event.content, query),
            ))
        return results

    def query_by_time_range(
        self,
        start_time: float,
        end_time: float,
        limit: int = 100,
    ) -> list[EpisodeEvent]:
        """Query events within a time range."""
        cur = self._conn.cursor()
        cur.execute(
            """SELECT * FROM episodes
               WHERE timestamp >= ? AND timestamp <= ?
               ORDER BY timestamp ASC
               LIMIT ?""",
            (start_time, end_time, limit),
        )
        return [self._row_to_event(row) for row in cur.fetchall()]

    def query_by_agent(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> list[EpisodeEvent]:
        """Query events for a specific agent."""
        cur = self._conn.cursor()
        cur.execute(
            """SELECT * FROM episodes
               WHERE agent_id = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (agent_id, limit),
        )
        return [self._row_to_event(row) for row in cur.fetchall()]

    def query_by_type(
        self,
        event_type: str,
        limit: int = 100,
    ) -> list[EpisodeEvent]:
        """Query events by type."""
        cur = self._conn.cursor()
        cur.execute(
            """SELECT * FROM episodes
               WHERE event_type = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (event_type, limit),
        )
        return [self._row_to_event(row) for row in cur.fetchall()]

    def query_by_session(self, session_id: str) -> list[EpisodeEvent]:
        """Query all events for a given session."""
        cur = self._conn.cursor()
        cur.execute(
            """SELECT * FROM episodes
               WHERE session_id = ?
               ORDER BY timestamp ASC""",
            (session_id,),
        )
        return [self._row_to_event(row) for row in cur.fetchall()]

    def count(self) -> int:
        """Total number of events stored."""
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM episodes")
        row = cur.fetchone()
        return row["cnt"] if row else 0

    def clear(self) -> None:
        """Clear all episodes and rebuild FTS index."""
        cur = self._conn.cursor()
        cur.execute("DELETE FROM episodes")
        cur.execute("DELETE FROM episodes_fts")
        self._conn.commit()

    @property
    def db_path(self) -> str:
        return str(self._db_path)

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> EpisodeEvent:
        """Convert a SQLite row to an EpisodeEvent."""
        metadata: dict[str, Any] = {}
        raw_meta = row["metadata"]
        if raw_meta:
            try:
                metadata = json.loads(raw_meta)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        return EpisodeEvent(
            event_id=row["event_id"],
            timestamp=row["timestamp"],
            agent_id=row["agent_id"],
            event_type=row["event_type"],
            content=row["content"],
            metadata=metadata,
            session_id=row["session_id"],
        )

    @staticmethod
    def _make_snippet(content: str, query: str) -> str:
        """Extract a snippet around the matching query text."""
        idx = content.lower().find(query.lower())
        if idx == -1:
            return content[:100]
        start = max(0, idx - 40)
        end = min(len(content), idx + len(query) + 60)
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        return snippet
