"""L312-7 — SQLite checkpoint store for the autopilot supervisor.

Anchor: ``docs/308-autonomy-loop-synthesis.md`` layer 7.

One row per loop. Schema is intentionally narrow — the autopilot owns
the *meta* of running loops (state, contract, last-iteration pointer);
loop-specific scratch (PRD, progress.txt, directive archive) lives in
the loop's own ``run_dir``.

States:
- ``running`` — actively driven by the supervisor.
- ``pending_resume`` — supervisor died with this loop in flight; needs
  *explicit* ``lyra autopilot resume <id>`` to continue. Auto-replay
  is forbidden by L312-7's bright-line.
- ``completed`` — terminal contract state observed; no further work.
- ``terminated`` — user-cancelled.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterator, Optional


__all__ = ["LoopRecord", "LoopStore"]


_SCHEMA = """
CREATE TABLE IF NOT EXISTS loops (
    id           TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,           -- 'ralph' | 'loop' | 'cron'
    state        TEXT NOT NULL,           -- 'running' | 'pending_resume' | 'completed' | 'terminated'
    run_dir      TEXT NOT NULL,
    created_at   REAL NOT NULL,
    updated_at   REAL NOT NULL,
    cum_usd      REAL NOT NULL DEFAULT 0,
    iter_count   INTEGER NOT NULL DEFAULT 0,
    contract_state TEXT NOT NULL DEFAULT 'pending',
    terminal_cause TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_loops_state ON loops(state);
"""


@dataclass
class LoopRecord:
    id: str
    kind: str = "loop"
    state: str = "running"
    run_dir: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    cum_usd: float = 0.0
    iter_count: int = 0
    contract_state: str = "pending"
    terminal_cause: Optional[str] = None
    payload_json: str = "{}"

    def payload(self) -> dict:
        try:
            return json.loads(self.payload_json or "{}")
        except json.JSONDecodeError:
            return {}


class LoopStore:
    """Append-only-ish SQLite store with WAL mode.

    Crash recovery: any row in ``state='running'`` whose ``updated_at``
    is older than ``stale_running_s`` (default 5 min) is moved to
    ``pending_resume`` on startup. Resume is explicit — the autopilot
    never silently re-fires a loop.
    """

    def __init__(self, *, db_path: Path | str, stale_running_s: float = 300.0) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.stale_running_s = float(stale_running_s)
        with self._conn() as cx:
            cx.execute("PRAGMA journal_mode=WAL")
            for stmt in _SCHEMA.strip().split(";"):
                if stmt.strip():
                    cx.execute(stmt)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        cx = sqlite3.connect(self.db_path)
        try:
            cx.row_factory = sqlite3.Row
            yield cx
            cx.commit()
        finally:
            cx.close()

    # ---- public API ------------------------------------------------- #

    def upsert(self, record: LoopRecord) -> None:
        record.updated_at = time.time()
        with self._conn() as cx:
            cx.execute(
                """INSERT INTO loops (id, kind, state, run_dir, created_at,
                                       updated_at, cum_usd, iter_count,
                                       contract_state, terminal_cause, payload_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     kind=excluded.kind, state=excluded.state,
                     run_dir=excluded.run_dir, updated_at=excluded.updated_at,
                     cum_usd=excluded.cum_usd, iter_count=excluded.iter_count,
                     contract_state=excluded.contract_state,
                     terminal_cause=excluded.terminal_cause,
                     payload_json=excluded.payload_json
                """,
                (record.id, record.kind, record.state, record.run_dir,
                 record.created_at, record.updated_at, record.cum_usd,
                 record.iter_count, record.contract_state,
                 record.terminal_cause, record.payload_json),
            )

    def get(self, loop_id: str) -> Optional[LoopRecord]:
        with self._conn() as cx:
            row = cx.execute("SELECT * FROM loops WHERE id=?", (loop_id,)).fetchone()
        return _row_to_record(row) if row else None

    def list_state(self, *states: str) -> list[LoopRecord]:
        if not states:
            with self._conn() as cx:
                rows = cx.execute("SELECT * FROM loops").fetchall()
            return [_row_to_record(r) for r in rows]
        placeholders = ",".join("?" for _ in states)
        with self._conn() as cx:
            rows = cx.execute(
                f"SELECT * FROM loops WHERE state IN ({placeholders})", states,
            ).fetchall()
        return [_row_to_record(r) for r in rows]

    def reconcile_on_startup(self) -> list[str]:
        """Move stale ``running`` rows to ``pending_resume`` and return their ids.

        Called once at autopilot start. Crash-recovery surface — never
        silently re-fires; surfaces the row for explicit resume.
        """
        cutoff = time.time() - self.stale_running_s
        with self._conn() as cx:
            stale = cx.execute(
                "SELECT id FROM loops WHERE state='running' AND updated_at < ?",
                (cutoff,),
            ).fetchall()
            ids = [row["id"] for row in stale]
            if ids:
                placeholders = ",".join("?" for _ in ids)
                cx.execute(
                    f"UPDATE loops SET state='pending_resume', updated_at=? "
                    f"WHERE id IN ({placeholders})",
                    [time.time(), *ids],
                )
        return ids

    def transition(self, loop_id: str, *, state: str,
                   terminal_cause: Optional[str] = None) -> None:
        with self._conn() as cx:
            cx.execute(
                "UPDATE loops SET state=?, terminal_cause=?, updated_at=? WHERE id=?",
                (state, terminal_cause, time.time(), loop_id),
            )


def _row_to_record(row: sqlite3.Row) -> LoopRecord:
    return LoopRecord(
        id=row["id"], kind=row["kind"], state=row["state"], run_dir=row["run_dir"],
        created_at=row["created_at"], updated_at=row["updated_at"],
        cum_usd=row["cum_usd"], iter_count=row["iter_count"],
        contract_state=row["contract_state"], terminal_cause=row["terminal_cause"],
        payload_json=row["payload_json"],
    )
