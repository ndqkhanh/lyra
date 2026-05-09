"""Phase D.6 — ``/search`` defaults to SQLite + FTS5.

Before this phase ``/search`` printed a "session store not wired"
diagnostic on every fresh REPL because no store was attached unless a
test or harness explicitly seeded one. v2.6.0 ships an automatic
SQLite + FTS5 store at ``<repo>/.lyra/sessions.sqlite`` and the slash
should Just Work with it — including over historical ``turns.jsonl``
files imported on first access.

These tests exercise the lazy attach + import path:

* Lazy seeding via :func:`_ensure_default_search_fn`.
* Live indexing via :meth:`_persist_chat_exchange` so a brand new
  exchange is searchable.
* Backfill from existing ``turns.jsonl`` files under
  ``sessions_root``.
* Slash dispatch through ``/search`` end-to-end.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_cli.interactive.session import (
    InteractiveSession,
    _cmd_search,
    _ensure_default_search_fn,
    _import_existing_turns_into_store,
    _index_exchange_in_store,
)


@pytest.fixture
def session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(repo_root=tmp_path, model="stub", mode="agent")


def test_ensure_default_search_fn_attaches_store(
    session: InteractiveSession,
) -> None:
    fn = _ensure_default_search_fn(session)
    assert fn is not None
    assert callable(session.search_fn)
    assert session._session_store is not None
    db = session.repo_root / ".lyra" / "sessions.sqlite"
    assert db.is_file()


def test_ensure_default_search_fn_is_idempotent(
    session: InteractiveSession,
) -> None:
    a = _ensure_default_search_fn(session)
    b = _ensure_default_search_fn(session)
    assert a is b


def test_index_exchange_makes_turn_searchable(
    session: InteractiveSession,
) -> None:
    _ensure_default_search_fn(session)
    _index_exchange_in_store(session, "what is the capital of France?", "Paris")
    hits = session.search_fn("capital France")
    assert any("capital" in (h.get("content") or "").lower() for h in hits)


def test_persist_chat_exchange_writes_through_to_store(
    session: InteractiveSession, tmp_path: Path
) -> None:
    session.sessions_root = tmp_path / "sessions"
    _ensure_default_search_fn(session)
    session._persist_chat_exchange("hello world", "hi there")
    hits = session.search_fn("world")
    assert any("hello" in (h.get("content") or "") for h in hits)


def test_search_command_returns_diagnostic_when_query_missing(
    session: InteractiveSession,
) -> None:
    out = _cmd_search(session, "")
    assert "usage" in out.output


def test_search_command_uses_default_store_when_none_attached(
    session: InteractiveSession,
) -> None:
    _ensure_default_search_fn(session)
    _index_exchange_in_store(session, "ping pong table", "yes really")
    result = _cmd_search(session, "pong")
    assert "pong" in result.output.lower()


def test_search_imports_historical_jsonl(tmp_path: Path) -> None:
    sessions_root = tmp_path / "sessions"
    historical = sessions_root / "abc-123"
    historical.mkdir(parents=True)
    log = historical / "turns.jsonl"
    # NB: writes a v2.x ``mode: build`` line on disk to verify the
    # _LEGACY_MODE_REMAP path runs at JSONL load time too.
    log.write_text(
        json.dumps({"line": "first", "mode": "build", "turn": 1,
                    "pending_task": None, "cost_usd": 0.0, "tokens_used": 0}) + "\n"
        + json.dumps({"kind": "chat", "turn": 1,
                       "user": "previously asked about peanuts",
                       "assistant": "yes peanuts are great"}) + "\n",
        encoding="utf-8",
    )

    session = InteractiveSession(
        repo_root=tmp_path, model="stub", mode="agent", sessions_root=sessions_root
    )
    fn = _ensure_default_search_fn(session)
    assert fn is not None

    hits = fn("peanuts")
    assert any("peanut" in (h.get("content") or "").lower() for h in hits)


def test_import_function_tolerates_missing_log(
    session: InteractiveSession, tmp_path: Path
) -> None:
    """A non-existent sessions_root directory must not raise."""
    session.sessions_root = tmp_path / "missing"
    _ensure_default_search_fn(session)
    store = session._session_store
    _import_existing_turns_into_store(session, store)
