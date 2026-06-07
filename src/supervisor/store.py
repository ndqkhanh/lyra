"""SQLite-backed persistence for supervisor session state."""

from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path
from typing import List, Optional

from src.supervisor.state import ProcessState, SessionInfo, SessionState

_CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id    TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    state         TEXT NOT NULL,
    process_state TEXT NOT NULL,
    working_dir   TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    last_active   TEXT NOT NULL,
    pr_url        TEXT
)
"""

_INSERT_SESSION = """
INSERT OR REPLACE INTO sessions
    (session_id, name, state, process_state, working_dir, created_at, last_active, pr_url)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

_SELECT_SESSION = "SELECT * FROM sessions WHERE session_id = ?"

_SELECT_ALL = "SELECT * FROM sessions ORDER BY created_at DESC"

_DELETE_SESSION = "DELETE FROM sessions WHERE session_id = ?"

_UPDATE_STATE = "UPDATE sessions SET state = ?, last_active = ? WHERE session_id = ?"

_UPDATE_LAST_ACTIVE = "UPDATE sessions SET last_active = ? WHERE session_id = ?"


class SessionStore:
    """Persistent store for session metadata backed by SQLite."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def init_db(self) -> None:
        """Ensure the sessions table exists."""
        self.connection.execute(_CREATE_SESSIONS_TABLE)
        self.connection.commit()

    def save_session(self, info: SessionInfo) -> None:
        """Insert or replace a session record."""
        self.connection.execute(
            _INSERT_SESSION,
            (
                info.session_id,
                info.name,
                info.state.value,
                info.process_state.value,
                info.working_dir,
                info.created_at.isoformat(),
                info.last_active.isoformat(),
                info.pr_url,
            ),
        )
        self.connection.commit()

    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Retrieve a single session by ID, or None."""
        row = self.connection.execute(_SELECT_SESSION, (session_id,)).fetchone()
        return self._row_to_info(row) if row else None

    def list_sessions(self) -> List[SessionInfo]:
        """Return all sessions ordered by creation time (newest first)."""
        rows = self.connection.execute(_SELECT_ALL).fetchall()
        return [self._row_to_info(r) for r in rows]

    def delete_session(self, session_id: str) -> None:
        """Remove a session record."""
        self.connection.execute(_DELETE_SESSION, (session_id,))
        self.connection.commit()

    def update_state(
        self, session_id: str, new_state: SessionState, now: datetime.datetime | None = None
    ) -> None:
        """Update the state and last_active timestamp."""
        now = now or datetime.datetime.now(tz=datetime.timezone.utc)
        self.connection.execute(_UPDATE_STATE, (new_state.value, now.isoformat(), session_id))
        self.connection.commit()

    def update_last_active(self, session_id: str, now: datetime.datetime | None = None) -> None:
        """Touch the last_active timestamp."""
        now = now or datetime.datetime.now(tz=datetime.timezone.utc)
        self.connection.execute(_UPDATE_LAST_ACTIVE, (now.isoformat(), session_id))
        self.connection.commit()

    # ------------------------------------------------------------------
    # Row mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_info(row: sqlite3.Row) -> SessionInfo:
        return SessionInfo(
            session_id=row["session_id"],
            name=row["name"],
            state=SessionState(row["state"]),
            process_state=ProcessState(row["process_state"]),
            working_dir=row["working_dir"],
            created_at=datetime.datetime.fromisoformat(row["created_at"]),
            last_active=datetime.datetime.fromisoformat(row["last_active"]),
            pr_url=row["pr_url"],
        )
