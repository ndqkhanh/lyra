"""
Session persistence — SessionManager for save/restore of agent sessions to SQLite.
Auto-saves on step boundary.
"""

import json
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class SessionStatus(Enum):
    """Lifecycle status of a persisted session."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class SessionRecord:
    """Full record of a persisted session."""

    session_id: str
    created_at: datetime
    updated_at: datetime
    status: SessionStatus = SessionStatus.ACTIVE
    agent_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    steps: list[dict[str, Any]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dict."""
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "agent_id": self.agent_id,
            "metadata": self.metadata,
            "steps": self.steps,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionRecord":
        """Create from a dict (e.g. loaded from DB or JSON)."""
        return cls(
            session_id=data["session_id"],
            status=SessionStatus(data.get("status", "active")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            agent_id=data.get("agent_id", ""),
            metadata=data.get("metadata", {}),
            steps=data.get("steps", []),
            context=data.get("context", {}),
        )


class SessionManager:
    """
    SQLite-backed session persistence manager.

    Handles saving and restoring agent sessions. Auto-saves session state
    on every step boundary so no progress is lost on crash.
    """

    def __init__(self, db_path: str | Path = "lyra_sessions.db") -> None:
        """
        Initialize the session manager.

        Args:
            db_path: Filesystem path to the SQLite database file.
        """
        self._db_path = Path(db_path)
        self._lock = threading.Lock()
        self._cache: dict[str, SessionRecord] = {}
        self._conn: sqlite3.Connection | None = None
        self._initialize_db()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _initialize_db(self) -> None:
        """Create the database and tables if they do not exist."""
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                status       TEXT NOT NULL DEFAULT 'active',
                created_at   TEXT NOT NULL,
                updated_at   TEXT NOT NULL,
                agent_id     TEXT NOT NULL DEFAULT '',
                metadata     TEXT NOT NULL DEFAULT '{}',
                context      TEXT NOT NULL DEFAULT '{}'
            )
        """)

        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS session_steps (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL REFERENCES sessions(session_id),
                step_index  INTEGER NOT NULL,
                step_data   TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                UNIQUE(session_id, step_index)
            )
        """)

        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_session(
        self,
        session_id: str,
        agent_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> SessionRecord:
        """
        Create a new session record.

        Args:
            session_id: Unique session identifier.
            agent_id: Optional agent identifier.
            metadata: Optional metadata dict.

        Returns:
            The newly created SessionRecord.
        """
        now = datetime.now(timezone.utc)
        record = SessionRecord(
            session_id=session_id,
            status=SessionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            agent_id=agent_id,
            metadata=metadata or {},
        )

        with self._lock:
            self._conn.execute(
                """INSERT INTO sessions (session_id, status, created_at, updated_at,
                   agent_id, metadata, context)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.session_id,
                    record.status.value,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                    record.agent_id,
                    json.dumps(record.metadata),
                    json.dumps(record.context),
                ),
            )
            self._conn.commit()
            self._cache[session_id] = record

        return record

    def get_session(self, session_id: str) -> SessionRecord | None:
        """
        Retrieve a session record by ID.

        Args:
            session_id: The session identifier.

        Returns:
            The SessionRecord if found, else None.
        """
        # Check cache first
        cached = self._cache.get(session_id)
        if cached is not None:
            return cached

        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

        if row is None:
            return None

        # Load steps
        steps = self._load_steps(session_id)

        record = SessionRecord(
            session_id=row["session_id"],
            status=SessionStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            agent_id=row["agent_id"],
            metadata=json.loads(row["metadata"]),
            steps=steps,
            context=json.loads(row["context"]),
        )
        self._cache[session_id] = record
        return record

    def update_session(
        self,
        session_id: str,
        *,
        status: SessionStatus | None = None,
        metadata: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        agent_id: str | None = None,
    ) -> SessionRecord | None:
        """
        Update fields on an existing session.

        Args:
            session_id: The session identifier.
            status: New status (or None to leave unchanged).
            metadata: New metadata dict (merged with existing).
            context: New context dict (merged with existing).
            agent_id: New agent identifier.

        Returns:
            The updated SessionRecord, or None if not found.
        """
        record = self.get_session(session_id)
        if record is None:
            return None

        now = datetime.now(timezone.utc)
        record.updated_at = now

        if status is not None:
            record.status = status
        if metadata is not None:
            record.metadata.update(metadata)
        if context is not None:
            record.context.update(context)
        if agent_id is not None:
            record.agent_id = agent_id

        with self._lock:
            self._conn.execute(
                """UPDATE sessions SET status=?, updated_at=?, agent_id=?,
                   metadata=?, context=? WHERE session_id=?""",
                (
                    record.status.value,
                    record.updated_at.isoformat(),
                    record.agent_id,
                    json.dumps(record.metadata),
                    json.dumps(record.context),
                    session_id,
                ),
            )
            self._conn.commit()

        self._cache[session_id] = record
        return record

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and its steps from the database.

        Args:
            session_id: The session identifier.

        Returns:
            True if deleted, False if not found.
        """
        with self._lock:
            # Delete steps first to satisfy foreign key constraint
            self._conn.execute(
                "DELETE FROM session_steps WHERE session_id = ?",
                (session_id,),
            )
            cursor = self._conn.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            self._conn.commit()
            deleted = cursor.rowcount > 0

        self._cache.pop(session_id, None)
        return deleted

    # ------------------------------------------------------------------
    # Step management
    # ------------------------------------------------------------------

    def append_step(
        self,
        session_id: str,
        step_data: dict[str, Any],
    ) -> bool:
        """
        Append a step to a session (auto-save on step boundary).

        Args:
            session_id: The session identifier.
            step_data: The step data dict.

        Returns:
            True if the step was appended.
        """
        record = self.get_session(session_id)
        if record is None:
            return False

        now = datetime.now(timezone.utc)
        record.updated_at = now
        step_index = len(record.steps)
        record.steps.append(step_data)

        with self._lock:
            self._conn.execute(
                """INSERT OR IGNORE INTO session_steps
                   (session_id, step_index, step_data, created_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    session_id,
                    step_index,
                    json.dumps(step_data),
                    now.isoformat(),
                ),
            )
            self._conn.execute(
                "UPDATE sessions SET updated_at=? WHERE session_id=?",
                (now.isoformat(), session_id),
            )
            self._conn.commit()

        return True

    def get_steps(self, session_id: str) -> list[dict[str, Any]]:
        """
        Get all steps for a session.

        Args:
            session_id: The session identifier.

        Returns:
            List of step data dicts.
        """
        record = self.get_session(session_id)
        if record is None:
            return []
        return record.steps

    def list_sessions(
        self,
        status: SessionStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SessionRecord]:
        """
        List sessions, optionally filtered by status.

        Args:
            status: Optional status filter.
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            List of SessionRecord objects.
        """
        with self._lock:
            if status is not None:
                rows = self._conn.execute(
                    """SELECT * FROM sessions WHERE status = ?
                       ORDER BY updated_at DESC LIMIT ? OFFSET ?""",
                    (status.value, limit, offset),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    """SELECT * FROM sessions
                       ORDER BY updated_at DESC LIMIT ? OFFSET ?""",
                    (limit, offset),
                ).fetchall()

        records = []
        for row in rows:
            steps = self._load_steps(row["session_id"])
            records.append(
                SessionRecord(
                    session_id=row["session_id"],
                    status=SessionStatus(row["status"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    agent_id=row["agent_id"],
                    metadata=json.loads(row["metadata"]),
                    steps=steps,
                    context=json.loads(row["context"]),
                )
            )

        return records

    def count_sessions(self, status: SessionStatus | None = None) -> int:
        """
        Count sessions, optionally filtered by status.

        Args:
            status: Optional status filter.

        Returns:
            Count of matching sessions.
        """
        with self._lock:
            if status is not None:
                row = self._conn.execute(
                    "SELECT COUNT(*) as cnt FROM sessions WHERE status = ?",
                    (status.value,),
                ).fetchone()
            else:
                row = self._conn.execute(
                    "SELECT COUNT(*) as cnt FROM sessions",
                ).fetchone()
        return row["cnt"] if row else 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_steps(self, session_id: str) -> list[dict[str, Any]]:
        """Load all steps for a session from the database."""
        rows = self._conn.execute(
            "SELECT step_data FROM session_steps WHERE session_id = ? ORDER BY step_index",
            (session_id,),
        ).fetchall()
        return [json.loads(r["step_data"]) for r in rows]
