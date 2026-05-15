"""SQLite-backed result cache for v3.12 WebSearch.

Why cache at all: an agent that re-asks "what's the latest on X" three
times in a turn pays for three identical SERP calls. The cache makes
each unique (provider, query, max_results, opts) tuple cost one HTTP
hop within its TTL.

Storage: SQLite at ``$LYRA_HOME/cache/web_search.db``. Single table,
hashed key, JSON-encoded payload, epoch-second expiry. SQLite (vs
pickle-on-disk) gives us atomic writes, concurrent-safe reads, and
``DELETE WHERE expires_at < now`` for cheap GC — three things a
home-rolled cache file always grows wrong.

TTL defaults to 1 hour. Time-bounded queries (``time_range="day"``)
sensibly want shorter TTLs; the caller passes ``ttl_seconds`` to
override per-call.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional


_DEFAULT_TTL_SEC = 3600  # 1 hour


def _cache_path() -> Path:
    """Resolve the cache DB path, honouring ``$LYRA_HOME``."""
    home = Path(os.environ.get("LYRA_HOME") or "~/.lyra").expanduser()
    return home / "cache" / "web_search.db"


@contextmanager
def _connect(path: Path) -> Iterator[sqlite3.Connection]:
    """Open + initialise the DB; commit on exit; close on cleanup.

    ``CREATE TABLE IF NOT EXISTS`` makes the first call idempotent so
    callers never have to do a separate "schema migration" step. The
    schema is intentionally tiny — adding columns is a separate
    breaking change.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS web_search_cache ("
            "key TEXT PRIMARY KEY, "
            "payload TEXT NOT NULL, "
            "expires_at INTEGER NOT NULL"
            ")"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expires "
            "ON web_search_cache (expires_at)"
        )
        yield conn
        conn.commit()
    finally:
        conn.close()


def _make_key(
    provider: str, query: str, max_results: int, opts: dict[str, Any]
) -> str:
    """Stable cache key — hash so it stays short regardless of opts size."""
    payload = json.dumps(
        {
            "provider": provider,
            "query": query.strip().lower(),
            "max_results": max_results,
            "opts": sorted(opts.items()),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_cached(
    provider: str,
    query: str,
    max_results: int,
    opts: dict[str, Any],
    *,
    path: Optional[Path] = None,
) -> Optional[list[dict[str, Any]]]:
    """Return the cached payload or None on miss/expiry."""
    cache_path = path or _cache_path()
    if not cache_path.is_file():
        return None
    key = _make_key(provider, query, max_results, opts)
    now = int(time.time())
    with _connect(cache_path) as conn:
        row = conn.execute(
            "SELECT payload FROM web_search_cache "
            "WHERE key = ? AND expires_at > ?",
            (key, now),
        ).fetchone()
    if row is None:
        return None
    try:
        return json.loads(row[0])
    except json.JSONDecodeError:
        # Cache row corrupted — treat as miss so the caller re-fetches.
        return None


def put_cached(
    provider: str,
    query: str,
    max_results: int,
    opts: dict[str, Any],
    payload: list[dict[str, Any]],
    *,
    ttl_seconds: int = _DEFAULT_TTL_SEC,
    path: Optional[Path] = None,
) -> None:
    """Store ``payload`` keyed by the call signature."""
    cache_path = path or _cache_path()
    key = _make_key(provider, query, max_results, opts)
    expires_at = int(time.time()) + max(int(ttl_seconds), 1)
    with _connect(cache_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO web_search_cache "
            "(key, payload, expires_at) VALUES (?, ?, ?)",
            (key, json.dumps(payload), expires_at),
        )


def purge_expired(*, path: Optional[Path] = None) -> int:
    """Delete every row whose ``expires_at`` is in the past.

    Returns the count removed. Cheap because of the
    ``idx_expires`` index. Callers run this opportunistically (e.g.
    on REPL startup) rather than on every read — keeps the hot path
    out of the GC business.
    """
    cache_path = path or _cache_path()
    if not cache_path.is_file():
        return 0
    now = int(time.time())
    with _connect(cache_path) as conn:
        cur = conn.execute(
            "DELETE FROM web_search_cache WHERE expires_at <= ?", (now,)
        )
        return cur.rowcount or 0


__all__ = ["get_cached", "purge_expired", "put_cached"]
