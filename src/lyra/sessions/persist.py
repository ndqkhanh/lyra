"""
Session persistence — SessionManager for save/restore of agent sessions to SQLite.
Auto-saves on step boundary.

This module provides the core persistence layer for Lyra sessions.  Sessions
are stored in a local SQLite database with full CRUD, step-level granularity,
and checkpoint support.

Enhancements in v9.0
--------------------
- Orthogonal state dimensions: session properties stored independently
  (agent state, context, metadata, tags) so they can be read/modified
  without loading the full session.
- Session tags: label sessions with arbitrary key-value pairs for
  search, filtering, and organisation.
- Session export/import: share sessions across machines or back them up
  as portable JSON files.
"""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# Orthogonal state dimensions
# ---------------------------------------------------------------------------


@dataclass
class OrthogonalState:
    """Independent dimensions of session state.

    Each dimension can be read and written without loading the full
    session record or steps.  This allows the CLI and dashboard to
    display rich session information efficiently.

    Attributes:
        agent_state: The agent's internal state (conversation context,
            model config, tool registry snapshot, etc.).
        progress: Progress indicators (% complete, current phase,
            subtasks remaining).
        economics: Cost and token usage (total cost, token counts,
            model used).
        runtime: Runtime data (elapsed, active tool, last heartbeat).
        custom: Arbitrary custom dimensions stored as key-value pairs.
    """

    agent_state: dict[str, Any] = field(default_factory=dict)
    progress: dict[str, Any] = field(default_factory=dict)
    economics: dict[str, Any] = field(default_factory=dict)
    runtime: dict[str, Any] = field(default_factory=dict)
    custom: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize all dimensions to a single dict."""
        return {
            "agent_state": self.agent_state,
            "progress": self.progress,
            "economics": self.economics,
            "runtime": self.runtime,
            "custom": self.custom,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OrthogonalState":
        """Deserialize from a dict (missing keys default to empty)."""
        return cls(
            agent_state=data.get("agent_state", {}),
            progress=data.get("progress", {}),
            economics=data.get("economics", {}),
            runtime=data.get("runtime", {}),
            custom=data.get("custom", {}),
        )


# ---------------------------------------------------------------------------
# Session tags
# ---------------------------------------------------------------------------


@dataclass
class SessionTag:
    """A key-value tag attached to a session for search and filtering.

    Attributes:
        session_id: The session this tag belongs to.
        key: Tag key (e.g. ``"project"``, ``"model"``, ``"priority"``).
        value: Tag value (e.g. ``"lyra-core"``, ``"claude-opus-4"``, ``"high"``).
    """

    session_id: str
    key: str
    value: str

    def to_dict(self) -> dict[str, str]:
        return {"session_id": self.session_id, "key": self.key, "value": self.value}


# ---------------------------------------------------------------------------
# Session record
# ---------------------------------------------------------------------------


@dataclass
class SessionRecord:
    """Full record of a persisted session.

    Attributes:
        session_id: Unique session identifier.
        created_at: UTC datetime of creation.
        updated_at: UTC datetime of last update.
        status: Current lifecycle status.
        agent_id: Identifier of the agent that owns this session.
        metadata: Arbitrary metadata dict.
        steps: Ordered list of step data dicts.
        context: Session context dict (conversation history, etc.).
        tags: List of key-value tags attached to this session.
        orthogonal: Independent state dimensions (v9.0).
    """

    session_id: str
    created_at: datetime
    updated_at: datetime
    status: SessionStatus = SessionStatus.ACTIVE
    agent_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    steps: list[dict[str, Any]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    tags: list[SessionTag] = field(default_factory=list)
    orthogonal: OrthogonalState = field(default_factory=OrthogonalState)

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
            "tags": [t.to_dict() for t in self.tags],
            "orthogonal": self.orthogonal.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionRecord":
        """Create from a dict (e.g. loaded from DB or JSON)."""
        tags = []
        for t in data.get("tags", []):
            if isinstance(t, dict):
                tags.append(SessionTag(
                    session_id=data["session_id"],
                    key=t.get("key", ""),
                    value=t.get("value", ""),
                ))

        return cls(
            session_id=data["session_id"],
            status=SessionStatus(data.get("status", "active")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            agent_id=data.get("agent_id", ""),
            metadata=data.get("metadata", {}),
            steps=data.get("steps", []),
            context=data.get("context", {}),
            tags=tags,
            orthogonal=OrthogonalState.from_dict(data.get("orthogonal", {})),
        )


# ---------------------------------------------------------------------------
# Session manager
# ---------------------------------------------------------------------------


class SessionManager:
    """
    SQLite-backed session persistence manager.

    Handles saving and restoring agent sessions. Auto-saves session state
    on every step boundary so no progress is lost on crash.

    v9.0 additions:
    - Orthogonal state dimensions stored in separate columns for efficient
      partial reads/writes.
    - Tags table for searchable key-value labels.
    - Export/import as portable JSON.
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
                context      TEXT NOT NULL DEFAULT '{}',
                -- v9.0: orthogonal state dimensions stored as JSON columns
                agent_state  TEXT NOT NULL DEFAULT '{}',
                progress     TEXT NOT NULL DEFAULT '{}',
                economics    TEXT NOT NULL DEFAULT '{}',
                runtime      TEXT NOT NULL DEFAULT '{}',
                custom_state TEXT NOT NULL DEFAULT '{}'
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

        # v9.0: tags table for searchable key-value labels
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS session_tags (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL REFERENCES sessions(session_id),
                key         TEXT NOT NULL,
                value       TEXT NOT NULL,
                UNIQUE(session_id, key)
            )
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tags_session
            ON session_tags(session_id)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tags_key
            ON session_tags(key, value)
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
        orthogonal: OrthogonalState | None = None,
    ) -> SessionRecord:
        """
        Create a new session record.

        Args:
            session_id: Unique session identifier.
            agent_id: Optional agent identifier.
            metadata: Optional metadata dict.
            orthogonal: Optional initial orthogonal state.

        Returns:
            The newly created SessionRecord.
        """
        now = datetime.now(timezone.utc)
        orth = orthogonal or OrthogonalState()
        record = SessionRecord(
            session_id=session_id,
            status=SessionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            agent_id=agent_id,
            metadata=metadata or {},
            orthogonal=orth,
        )

        with self._lock:
            self._conn.execute(
                """INSERT INTO sessions (session_id, status, created_at, updated_at,
                   agent_id, metadata, context,
                   agent_state, progress, economics, runtime, custom_state)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.session_id,
                    record.status.value,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                    record.agent_id,
                    json.dumps(record.metadata),
                    json.dumps(record.context),
                    json.dumps(orth.agent_state),
                    json.dumps(orth.progress),
                    json.dumps(orth.economics),
                    json.dumps(orth.runtime),
                    json.dumps(orth.custom),
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

        # Load tags
        tags = self._load_tags(session_id)

        record = SessionRecord(
            session_id=row["session_id"],
            status=SessionStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            agent_id=row["agent_id"],
            metadata=json.loads(row["metadata"]),
            steps=steps,
            context=json.loads(row["context"]),
            tags=tags,
            orthogonal=OrthogonalState(
                agent_state=json.loads(row["agent_state"]),
                progress=json.loads(row["progress"]),
                economics=json.loads(row["economics"]),
                runtime=json.loads(row["runtime"]),
                custom=json.loads(row["custom_state"]),
            ),
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
        orthogonal: OrthogonalState | None = None,
    ) -> SessionRecord | None:
        """
        Update fields on an existing session.

        Args:
            session_id: The session identifier.
            status: New status (or None to leave unchanged).
            metadata: New metadata dict (merged with existing).
            context: New context dict (merged with existing).
            agent_id: New agent identifier.
            orthogonal: New orthogonal state (merged dimension-by-dimension).

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
        if orthogonal is not None:
            # Merge per-dimension
            if orthogonal.agent_state:
                record.orthogonal.agent_state.update(orthogonal.agent_state)
            if orthogonal.progress:
                record.orthogonal.progress.update(orthogonal.progress)
            if orthogonal.economics:
                record.orthogonal.economics.update(orthogonal.economics)
            if orthogonal.runtime:
                record.orthogonal.runtime.update(orthogonal.runtime)
            if orthogonal.custom:
                record.orthogonal.custom.update(orthogonal.custom)

        with self._lock:
            self._conn.execute(
                """UPDATE sessions SET status=?, updated_at=?, agent_id=?,
                   metadata=?, context=?,
                   agent_state=?, progress=?, economics=?, runtime=?, custom_state=?
                   WHERE session_id=?""",
                (
                    record.status.value,
                    record.updated_at.isoformat(),
                    record.agent_id,
                    json.dumps(record.metadata),
                    json.dumps(record.context),
                    json.dumps(record.orthogonal.agent_state),
                    json.dumps(record.orthogonal.progress),
                    json.dumps(record.orthogonal.economics),
                    json.dumps(record.orthogonal.runtime),
                    json.dumps(record.orthogonal.custom),
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
            # Delete dependent records first
            self._conn.execute(
                "DELETE FROM session_tags WHERE session_id = ?",
                (session_id,),
            )
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
    # Orthogonal state management (v9.0)
    # ------------------------------------------------------------------

    def get_orthogonal_state(self, session_id: str) -> OrthogonalState | None:
        """Read orthogonal state dimensions without loading the full session.

        Args:
            session_id: The session identifier.

        Returns:
            OrthogonalState, or None if the session does not exist.
        """
        with self._lock:
            row = self._conn.execute(
                """SELECT agent_state, progress, economics, runtime, custom_state
                   FROM sessions WHERE session_id = ?""",
                (session_id,),
            ).fetchone()

        if row is None:
            return None

        return OrthogonalState(
            agent_state=json.loads(row["agent_state"]),
            progress=json.loads(row["progress"]),
            economics=json.loads(row["economics"]),
            runtime=json.loads(row["runtime"]),
            custom=json.loads(row["custom_state"]),
        )

    def update_progress(self, session_id: str, **progress: Any) -> bool:
        """Update the progress dimension only (efficient partial write).

        Args:
            session_id: The session identifier.
            **progress: Progress key-value pairs.

        Returns:
            True if updated.
        """
        orth = self.get_orthogonal_state(session_id)
        if orth is None:
            return False
        orth.progress.update(progress)
        self.update_session(session_id, orthogonal=orth)
        return True

    def update_economics(self, session_id: str, **economics: Any) -> bool:
        """Update the economics dimension only (efficient partial write)."""
        orth = self.get_orthogonal_state(session_id)
        if orth is None:
            return False
        orth.economics.update(economics)
        self.update_session(session_id, orthogonal=orth)
        return True

    def update_runtime(self, session_id: str, **runtime: Any) -> bool:
        """Update the runtime dimension only (efficient partial write)."""
        orth = self.get_orthogonal_state(session_id)
        if orth is None:
            return False
        orth.runtime.update(runtime)
        self.update_session(session_id, orthogonal=orth)
        return True

    # ------------------------------------------------------------------
    # Tag management (v9.0)
    # ------------------------------------------------------------------

    def set_tag(self, session_id: str, key: str, value: str) -> bool:
        """Set a tag on a session (upsert).

        Args:
            session_id: The session identifier.
            key: Tag key.
            value: Tag value.

        Returns:
            True if the session exists.
        """
        record = self.get_session(session_id)
        if record is None:
            return False

        with self._lock:
            self._conn.execute(
                """INSERT OR REPLACE INTO session_tags (session_id, key, value)
                   VALUES (?, ?, ?)""",
                (session_id, key, value),
            )
            self._conn.commit()

        # Update in-memory cache
        existing_tag = next((t for t in record.tags if t.key == key), None)
        if existing_tag:
            existing_tag.value = value
        else:
            record.tags.append(SessionTag(session_id=session_id, key=key, value=value))

        return True

    def get_tag(self, session_id: str, key: str) -> str | None:
        """Get a single tag value.

        Args:
            session_id: The session identifier.
            key: Tag key.

        Returns:
            Tag value, or None if not found.
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM session_tags WHERE session_id=? AND key=?",
                (session_id, key),
            ).fetchone()
        return row["value"] if row else None

    def get_all_tags(self, session_id: str) -> dict[str, str]:
        """Get all tags for a session as a key-value dict.

        Args:
            session_id: The session identifier.

        Returns:
            Dict of ``{key: value}``.
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT key, value FROM session_tags WHERE session_id=?",
                (session_id,),
            ).fetchall()
        return {r["key"]: r["value"] for r in rows}

    def delete_tag(self, session_id: str, key: str) -> bool:
        """Delete a tag from a session.

        Args:
            session_id: The session identifier.
            key: Tag key to remove.

        Returns:
            True if the tag existed.
        """
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM session_tags WHERE session_id=? AND key=?",
                (session_id, key),
            )
            self._conn.commit()
            deleted = cursor.rowcount > 0

        # Update cache
        record = self._cache.get(session_id)
        if record:
            record.tags = [t for t in record.tags if t.key != key]

        return deleted

    def find_by_tag(self, key: str, value: str) -> list[SessionRecord]:
        """Find all sessions with a specific tag key-value pair.

        Args:
            key: Tag key.
            value: Tag value.

        Returns:
            List of matching SessionRecord objects.
        """
        with self._lock:
            rows = self._conn.execute(
                """SELECT session_id FROM session_tags
                   WHERE key=? AND value=?
                   ORDER BY session_id""",
                (key, value),
            ).fetchall()

        return [r for sid in (row["session_id"] for row in rows)
                if (r := self.get_session(sid)) is not None]

    # ------------------------------------------------------------------
    # Export / Import (v9.0)
    # ------------------------------------------------------------------

    def export_session(self, session_id: str) -> dict[str, Any] | None:
        """Export a session as a portable JSON-serializable dict.

        The export includes:
        - All session metadata and context
        - All steps
        - All tags
        - Orthogonal state dimensions
        - Schema version for forward compatibility

        Args:
            session_id: The session to export.

        Returns:
            Export dict, or None if not found.
        """
        record = self.get_session(session_id)
        if record is None:
            return None

        export: dict[str, Any] = {
            "lyra_session_export": True,
            "schema_version": 1,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "session": record.to_dict(),
        }
        return export

    def import_session(self, export_data: dict[str, Any]) -> SessionRecord | None:
        """Import a session from an export dict (from :meth:`export_session`).

        Args:
            export_data: The export dict.

        Returns:
            The imported SessionRecord, or None if the session already exists
            or the data is invalid.
        """
        if not export_data.get("lyra_session_export"):
            raise ValueError("Not a valid Lyra session export")

        session_data = export_data.get("session", {})
        session_id = session_data.get("session_id", "")
        if not session_id:
            raise ValueError("Export data missing session_id")

        existing = self.get_session(session_id)
        if existing is not None:
            logger = __import__("structlog").get_logger(__name__)
            logger.warning("import skipped: session already exists", session_id=session_id)
            return None

        record = SessionRecord.from_dict(session_data)
        self.create_session(
            session_id=record.session_id,
            agent_id=record.agent_id,
            metadata=record.metadata,
            orthogonal=record.orthogonal,
        )
        for step in record.steps:
            self.append_step(record.session_id, step)
        self.update_session(record.session_id, status=record.status, context=record.context)
        for tag in record.tags:
            self.set_tag(record.session_id, tag.key, tag.value)

        return record

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
            tags = self._load_tags(row["session_id"])
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
                    tags=tags,
                    orthogonal=OrthogonalState(
                        agent_state=json.loads(row["agent_state"]),
                        progress=json.loads(row["progress"]),
                        economics=json.loads(row["economics"]),
                        runtime=json.loads(row["runtime"]),
                        custom=json.loads(row["custom_state"]),
                    ),
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

    def _load_tags(self, session_id: str) -> list[SessionTag]:
        """Load all tags for a session from the database."""
        rows = self._conn.execute(
            "SELECT key, value FROM session_tags WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        return [
            SessionTag(session_id=session_id, key=r["key"], value=r["value"])
            for r in rows
        ]
