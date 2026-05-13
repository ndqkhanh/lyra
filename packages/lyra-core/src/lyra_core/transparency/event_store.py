"""Local SQLite event store for transparency hook events."""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

from .models import HookEvent


_DEFAULT_DB = Path.home() / ".lyra" / "transparency.db"


class EventStore:
    """Append-only local SQLite store for all hook events. Zero network calls."""

    def __init__(self, db_path: Path = _DEFAULT_DB) -> None:
        self._path = db_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._path))

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hook_events (
                    event_id    TEXT PRIMARY KEY,
                    session_id  TEXT NOT NULL,
                    hook_type   TEXT NOT NULL,
                    tool_name   TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    received_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_session ON hook_events(session_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_received ON hook_events(received_at)"
            )

    def append(self, event: HookEvent) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO hook_events VALUES (?,?,?,?,?,?)",
                (
                    event.event_id,
                    event.session_id,
                    event.hook_type,
                    event.tool_name,
                    event.payload_json,
                    event.received_at,
                ),
            )

    def tail(self, n: int = 50, *, session_id: Optional[str] = None) -> list[HookEvent]:
        sql = "SELECT event_id, session_id, hook_type, tool_name, payload_json, received_at FROM hook_events"
        params: list = []
        if session_id:
            sql += " WHERE session_id = ?"
            params.append(session_id)
        sql += " ORDER BY received_at DESC LIMIT ?"
        params.append(n)
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [HookEvent(*row) for row in reversed(rows)]

    def since(self, ts: float, *, session_id: Optional[str] = None) -> list[HookEvent]:
        sql = "SELECT event_id, session_id, hook_type, tool_name, payload_json, received_at FROM hook_events WHERE received_at > ?"
        params: list = [ts]
        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
        sql += " ORDER BY received_at ASC"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [HookEvent(*row) for row in rows]

    def active_sessions(self) -> list[str]:
        """Return session IDs with an event in the last 300 seconds."""
        cutoff = time.time() - 300
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT session_id FROM hook_events WHERE received_at > ?",
                (cutoff,),
            ).fetchall()
        return [r[0] for r in rows]


def make_event(
    hook_type: str,
    *,
    session_id: str,
    tool_name: str = "",
    payload: dict | None = None,
) -> HookEvent:
    """Factory — generates a fresh event_id and timestamps it now."""
    return HookEvent(
        event_id=str(uuid.uuid4()),
        session_id=session_id,
        hook_type=hook_type,
        tool_name=tool_name,
        payload_json=json.dumps(payload or {}),
        received_at=time.time(),
    )
