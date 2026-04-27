"""SQLite + FTS5 session store — hermes-agent pattern.

Schema (one file, ``state.db``):

- ``sessions(id TEXT PRIMARY KEY, created_at REAL, model TEXT, mode TEXT)``
- ``messages(id INTEGER PRIMARY KEY AUTOINCREMENT,
           session_id TEXT,
           role TEXT, content TEXT,
           tool_calls TEXT, created_at REAL)``
- ``messages_fts USING fts5(content, content=messages, content_rowid=id)``
  with triggers that keep FTS in sync with inserts/updates/deletes.

The store is deliberately schema-stable: ``PRAGMA user_version = 1`` is
the migration watermark, bumped only on breaking schema changes.

Operations:

- :meth:`start_session` — ``INSERT OR REPLACE`` (idempotent; the agent
  loop may re-enter a session by id).
- :meth:`append_message` — record one turn step.
- :meth:`list_sessions` — reverse-chronological for the REPL picker.
- :meth:`search_messages` — FTS5 ``MATCH`` with bm25 ranking.

``tool_calls`` is JSON-encoded when provided to avoid a second table
while still being round-trippable.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

__all__ = ["SessionStore"]

_USER_VERSION = 1


@dataclass
class _Row:
    """Convenience view of a messages row."""

    id: int
    session_id: str
    role: str
    content: str
    tool_calls: list[dict]
    created_at: float


class SessionStore:
    """SQLite-backed session + message store with FTS5 recall."""

    def __init__(self, *, db_path: Path | str) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._con = sqlite3.connect(
            str(self._path),
            check_same_thread=False,
            isolation_level=None,  # autocommit; simpler with WAL
        )
        self._con.execute("PRAGMA journal_mode = WAL")
        self._con.execute("PRAGMA foreign_keys = ON")
        self._bootstrap_schema()

    # --- schema ------------------------------------------------------ #

    def _bootstrap_schema(self) -> None:
        cur = self._con
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                model TEXT,
                mode TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_calls TEXT,
                created_at REAL NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
            USING fts5(content, content='messages', content_rowid='id', tokenize='porter')
            """
        )
        # Triggers keep FTS in sync. Using the external-content-table
        # pattern means we must manually mirror changes via INSERT /
        # DELETE statements in the triggers.
        cur.execute(
            """
            CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
                INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
            END
            """
        )
        cur.execute(
            """
            CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
                INSERT INTO messages_fts(messages_fts, rowid, content)
                VALUES ('delete', old.id, old.content);
            END
            """
        )
        cur.execute(
            """
            CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
                INSERT INTO messages_fts(messages_fts, rowid, content)
                VALUES ('delete', old.id, old.content);
                INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
            END
            """
        )
        cur.execute(f"PRAGMA user_version = {_USER_VERSION}")

    # --- write API --------------------------------------------------- #

    def start_session(
        self,
        session_id: str,
        *,
        model: str = "unknown",
        mode: str = "agent",
        **_: Any,
    ) -> None:
        with self._lock:
            self._con.execute(
                """
                INSERT INTO sessions(id, created_at, model, mode)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    model = excluded.model,
                    mode = excluded.mode
                """,
                (session_id, time.time(), model, mode),
            )

    def append_message(
        self,
        session_id: str,
        *,
        role: str,
        content: str,
        tool_calls: Optional[Iterable[dict]] = None,
        **_: Any,
    ) -> int:
        payload = json.dumps(list(tool_calls)) if tool_calls else None
        with self._lock:
            cur = self._con.execute(
                """
                INSERT INTO messages(session_id, role, content, tool_calls, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, role, content, payload, time.time()),
            )
            return int(cur.lastrowid or 0)

    # --- read API ---------------------------------------------------- #

    def list_sessions(self) -> list[dict]:
        rows = self._con.execute(
            "SELECT id, created_at, model, mode FROM sessions ORDER BY created_at DESC"
        ).fetchall()
        return [
            {"id": r[0], "created_at": r[1], "model": r[2], "mode": r[3]} for r in rows
        ]

    def get_session_messages(self, session_id: str) -> list[dict]:
        rows = self._con.execute(
            """
            SELECT id, session_id, role, content, tool_calls, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def search_messages(self, query: str, *, k: int = 10) -> list[dict]:
        """FTS5 match with bm25 ranking. Returns empty list on no-match.

        The query string is passed through ``sanitize_fts_query`` so
        plain natural-language phrases work without the caller having
        to know FTS5 syntax. Exceptions from FTS5 (malformed query) are
        swallowed and surfaced as an empty hit list — the agent should
        not crash because the user typed a punctuation char.
        """
        q = _sanitize_fts_query(query)
        if not q:
            return []
        try:
            rows = self._con.execute(
                """
                SELECT m.id, m.session_id, m.role, m.content,
                       bm25(messages_fts) AS score
                FROM messages_fts
                JOIN messages m ON m.id = messages_fts.rowid
                WHERE messages_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (q, int(k)),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [
            {
                "id": r[0],
                "session_id": r[1],
                "role": r[2],
                "content": r[3],
                "score": float(r[4]) if r[4] is not None else 0.0,
            }
            for r in rows
        ]

    # --- helpers ----------------------------------------------------- #

    @staticmethod
    def _row_to_dict(r: tuple) -> dict:
        tool_calls: list[dict] = []
        if r[4]:
            try:
                parsed = json.loads(r[4])
                if isinstance(parsed, list):
                    tool_calls = parsed
            except json.JSONDecodeError:
                tool_calls = []
        return {
            "id": r[0],
            "session_id": r[1],
            "role": r[2],
            "content": r[3],
            "tool_calls": tool_calls,
            "created_at": r[5],
        }

    # --- lifecycle --------------------------------------------------- #

    def close(self) -> None:
        with self._lock:
            try:
                self._con.close()
            except sqlite3.ProgrammingError:
                pass

    def __enter__(self) -> "SessionStore":  # pragma: no cover - trivial
        return self

    def __exit__(self, *_: Any) -> None:  # pragma: no cover - trivial
        self.close()


_FTS_SPECIAL = set('"()')


def _sanitize_fts_query(query: str) -> str:
    """Escape/strip FTS5 punctuation so plain queries work unaltered.

    - Trim whitespace.
    - Double-quote each term that contains an FTS5 special char so the
      whole phrase becomes a safe literal. Bare words stay bare.
    - Return empty string if nothing actionable remains.
    """
    if not query:
        return ""
    parts: list[str] = []
    for raw in query.split():
        term = raw.strip()
        if not term:
            continue
        if any(ch in _FTS_SPECIAL for ch in term):
            term = '"' + term.replace('"', '""') + '"'
        parts.append(term)
    return " ".join(parts)
