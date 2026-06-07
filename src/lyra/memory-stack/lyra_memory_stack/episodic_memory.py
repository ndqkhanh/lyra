"""L1 Episodic Memory — session events, decisions, traces (SQLite+FTS5).

Stores discrete events with full-text search and temporal querying.
Each event is timestamped and taggable for efficient retrieval.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class EpisodicEvent:
    """A recorded event in episodic memory.

    Attributes:
        event_id: Unique identifier.
        session_id: The session this event belongs to.
        event_type: Category of event (e.g., "decision", "tool_call", "error").
        content: Event description or data.
        tags: Tuple of searchable tags.
        timestamp: Unix timestamp of the event.
    """

    event_id: int
    session_id: str
    event_type: str
    content: str
    tags: tuple[str, ...]
    timestamp: float


class EpisodicMemory:
    """L1 episodic memory backed by SQLite with FTS5 full-text search.

    Stores session events, decisions, and traces with temporal + semantic
    retrieval capabilities.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '',
                timestamp REAL NOT NULL
            )"""
        )
        self._conn.execute(
            """CREATE VIRTUAL TABLE IF NOT EXISTS events_fts
            USING fts5(session_id, event_type, content, tags)"""
        )
        self._conn.commit()

    async def record_event(
        self,
        session_id: str,
        event_type: str,
        content: str,
        tags: tuple[str, ...] = (),
    ) -> int:
        """Record a new episodic event.

        Args:
            session_id: The session identifier.
            event_type: Category of the event.
            content: Event content.
            tags: Searchable tags.

        Returns:
            The auto-generated event_id.
        """
        now = time.time()
        tags_str = ",".join(tags)
        cursor = self._conn.execute(
            "INSERT INTO events(session_id, event_type, content, tags, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, event_type, content, tags_str, now),
        )
        event_id = cursor.lastrowid or 0
        self._conn.execute(
            "INSERT INTO events_fts(rowid, session_id, event_type, content, tags) "
            "VALUES (?, ?, ?, ?, ?)",
            (event_id, session_id, event_type, content, tags_str),
        )
        self._conn.commit()
        return event_id

    async def search(
        self,
        query: str,
        session_id: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
    ) -> tuple[EpisodicEvent, ...]:
        """Full-text search across episodic events.

        Args:
            query: The search query.
            session_id: Optional session filter.
            event_type: Optional event type filter.
            limit: Maximum results to return.

        Returns:
            Matching EpisodicEvent entries.
        """
        sql = (
            "SELECT e.id, e.session_id, e.event_type, e.content, e.tags, e.timestamp "
            "FROM events e JOIN events_fts f ON e.id = f.rowid "
            "WHERE events_fts MATCH ?"
        )
        params: list = [query]

        if session_id:
            sql += " AND e.session_id = ?"
            params.append(session_id)
        if event_type:
            sql += " AND e.event_type = ?"
            params.append(event_type)

        sql += " ORDER BY e.timestamp DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(sql, params).fetchall()
        return tuple(
            EpisodicEvent(
                event_id=r[0],
                session_id=r[1],
                event_type=r[2],
                content=r[3],
                tags=tuple(r[4].split(",")) if r[4] else (),
                timestamp=r[5],
            )
            for r in rows
        )

    async def get_by_session(
        self, session_id: str, limit: int = 100
    ) -> tuple[EpisodicEvent, ...]:
        """Get all events for a specific session.

        Args:
            session_id: The session to query.
            limit: Maximum results.

        Returns:
            Events in chronological order.
        """
        rows = self._conn.execute(
            "SELECT id, session_id, event_type, content, tags, timestamp "
            "FROM events WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return tuple(
            EpisodicEvent(
                event_id=r[0],
                session_id=r[1],
                event_type=r[2],
                content=r[3],
                tags=tuple(r[4].split(",")) if r[4] else (),
                timestamp=r[5],
            )
            for r in rows
        )

    async def get_recent(
        self, limit: int = 20
    ) -> tuple[EpisodicEvent, ...]:
        """Get the most recent events across all sessions."""
        rows = self._conn.execute(
            "SELECT id, session_id, event_type, content, tags, timestamp "
            "FROM events ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return tuple(
            EpisodicEvent(
                event_id=r[0],
                session_id=r[1],
                event_type=r[2],
                content=r[3],
                tags=tuple(r[4].split(",")) if r[4] else (),
                timestamp=r[5],
            )
            for r in rows
        )

    async def count(self) -> int:
        """Return the total number of stored events."""
        row = self._conn.execute("SELECT COUNT(*) FROM events").fetchone()
        return row[0] if row else 0
