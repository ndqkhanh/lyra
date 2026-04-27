"""Phase 0 — RED for the SQLite + FTS5 session store.

Contract (plan Phase 4):

- ``SessionStore`` lives at ``lyra_core.sessions.store``.
- Constructor: ``SessionStore(db_path: Path)`` — opens or creates the
  SQLite DB with WAL mode and creates tables ``sessions``, ``messages``,
  and an FTS5 virtual table ``messages_fts`` synced by triggers.
- ``start_session(session_id, *, model, mode)`` inserts a row.
- ``append_message(session_id, role, content, tool_calls=None)`` inserts
  a row; the FTS trigger makes ``content`` searchable.
- ``list_sessions()`` returns sessions in reverse chronological order.
- ``search_messages(query, k=10)`` uses FTS5 match and returns rows
  with ``session_id``, ``role``, ``content``, ``score``. Empty result
  for no match.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


def _import_store():
    try:
        from lyra_core.sessions.store import SessionStore
    except ModuleNotFoundError as exc:
        pytest.fail(f"lyra_core.sessions.store.SessionStore must exist ({exc})")
    return SessionStore


def _db(tmp_path: Path) -> Path:
    return tmp_path / ".lyra" / "state.db"


def test_constructor_creates_tables_and_fts(tmp_path: Path) -> None:
    SessionStore = _import_store()
    db = _db(tmp_path)
    SessionStore(db_path=db)
    assert db.is_file()
    # Inspect schema.
    con = sqlite3.connect(db)
    try:
        rows = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        ).fetchall()}
    finally:
        con.close()
    for required in ("sessions", "messages", "messages_fts"):
        assert required in rows, f"{required} must be part of the schema; got {rows}"


def test_start_session_and_append_message_persists(tmp_path: Path) -> None:
    SessionStore = _import_store()
    store = SessionStore(db_path=_db(tmp_path))

    store.start_session("s1", model="claude-opus-4.5", mode="plan")
    store.append_message("s1", role="user", content="hi there")
    store.append_message("s1", role="assistant", content="hello world")

    sessions = store.list_sessions()
    assert any(s["id"] == "s1" for s in sessions)


def test_search_messages_uses_fts5(tmp_path: Path) -> None:
    SessionStore = _import_store()
    store = SessionStore(db_path=_db(tmp_path))

    store.start_session("s1", model="m", mode="plan")
    store.append_message("s1", role="user", content="please refactor the auth service")
    store.append_message("s1", role="assistant", content="let's start with tokens and sessions")
    store.start_session("s2", model="m", mode="plan")
    store.append_message("s2", role="user", content="add dark mode toggle")

    hits = store.search_messages("refactor auth")
    assert hits, "FTS match for a relevant phrase must return at least one hit"
    assert hits[0]["session_id"] == "s1"

    # Unrelated query finds nothing.
    assert store.search_messages("quantum entanglement") == []


def test_list_sessions_is_reverse_chronological(tmp_path: Path) -> None:
    SessionStore = _import_store()
    store = SessionStore(db_path=_db(tmp_path))
    for idx in ("a", "b", "c"):
        store.start_session(idx, model="m", mode="plan")
    ids = [s["id"] for s in store.list_sessions()]
    assert ids[:3] == ["c", "b", "a"]


def test_fts_trigger_syncs_updates(tmp_path: Path) -> None:
    """When a row is inserted into messages, it must become searchable in FTS
    without manual index rebuilds."""
    SessionStore = _import_store()
    store = SessionStore(db_path=_db(tmp_path))
    store.start_session("s1", model="m", mode="plan")
    store.append_message("s1", role="user", content="pinecone vector search")
    assert store.search_messages("pinecone"), "FTS5 trigger must index inserts immediately"
