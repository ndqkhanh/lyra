"""L38-2 — Persistent skill telemetry with exponential time decay.

The default ``SkillRegistry`` keeps ``success_count`` and ``miss_count``
as plain in-memory ints. That works for one process but loses every
signal across restarts and never decays — a skill that succeeded ten
times in 2025 but hasn't been picked since dominates the ranking
forever.

Argus's design (LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md §L38-2) replaces
the ints with an event ledger: every success / miss is appended with
a UTC timestamp, and the *decayed* success rate is computed at read
time as

    rate = sum(weight(t) * indicator) / sum(weight(t))
    weight(t) = 0.5 ** ((now - t).days / half_life_days)

so a recent success counts more than an old one and the score drifts
toward neutral when the skill goes unused.

The ledger lives in its own SQLite table so:

* the registry's CRUD path stays purely structural,
* dropping a skill from the registry doesn't immediately wipe its
  history (useful when a skill is re-registered after a failed
  experiment), and
* the bus / arena / router can each write to the same ledger without
  fighting over a shared dataclass.

This module ships the store + a ``DecayedRate`` helper. Wiring into
``SkillRegistry`` is opt-in via the ``telemetry_store`` constructor
argument — existing callers stay 100 % compatible.
"""
from __future__ import annotations

import math
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal


__all__ = [
    "DecayedRate",
    "SkillTelemetryStore",
    "TelemetryEvent",
]


EventKind = Literal["success", "miss"]


@dataclass(frozen=True)
class TelemetryEvent:
    """One row in the ledger."""

    skill_id: str
    kind: EventKind
    ts_unix: float

    @property
    def is_success(self) -> bool:
        return self.kind == "success"


@dataclass(frozen=True)
class DecayedRate:
    """Decayed-rate readout for a skill at a given evaluation time."""

    skill_id: str
    success_weight: float
    total_weight: float
    n_events: int

    @property
    def rate(self) -> float:
        if self.total_weight <= 0.0:
            return 0.0
        return self.success_weight / self.total_weight

    @property
    def is_cold(self) -> bool:
        return self.n_events == 0


class SkillTelemetryStore:
    """SQLite-backed event ledger for skill success / miss signals.

    The store is *append-only* in the success path; ``prune`` is a
    separate maintenance call so accidental cancellation never wipes
    history. Concurrency: every operation opens / commits on the
    shared connection — fine for the single-process REPL surface
    where this currently lives. A multi-writer story is L38-9 work
    (chaos-partitioned worktree replicas) and not in scope here.
    """

    _SCHEMA = (
        "CREATE TABLE IF NOT EXISTS skill_telemetry ("
        "  skill_id TEXT NOT NULL,"
        "  kind     TEXT NOT NULL CHECK (kind IN ('success','miss')),"
        "  ts_unix  REAL NOT NULL"
        ")",
        "CREATE INDEX IF NOT EXISTS skill_telemetry_skill_idx "
        "ON skill_telemetry(skill_id, ts_unix)",
    )

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        for stmt in self._SCHEMA:
            self._conn.execute(stmt)
        self._conn.commit()

    # ---------------------------------------------------------- writes

    def record(self, skill_id: str, kind: EventKind, *, ts_unix: float | None = None) -> None:
        if kind not in ("success", "miss"):
            raise ValueError(f"telemetry kind must be 'success' or 'miss', got {kind!r}")
        when = float(ts_unix) if ts_unix is not None else time.time()
        self._conn.execute(
            "INSERT INTO skill_telemetry(skill_id, kind, ts_unix) VALUES (?, ?, ?)",
            (skill_id, kind, when),
        )
        self._conn.commit()

    def record_success(self, skill_id: str, *, ts_unix: float | None = None) -> None:
        self.record(skill_id, "success", ts_unix=ts_unix)

    def record_miss(self, skill_id: str, *, ts_unix: float | None = None) -> None:
        self.record(skill_id, "miss", ts_unix=ts_unix)

    # ---------------------------------------------------------- reads

    def events(self, skill_id: str) -> list[TelemetryEvent]:
        rows = self._conn.execute(
            "SELECT skill_id, kind, ts_unix FROM skill_telemetry "
            "WHERE skill_id = ? ORDER BY ts_unix ASC",
            (skill_id,),
        ).fetchall()
        return [
            TelemetryEvent(skill_id=r["skill_id"], kind=r["kind"], ts_unix=r["ts_unix"])
            for r in rows
        ]

    def counts(self, skill_id: str) -> tuple[int, int]:
        """Raw lifetime ``(success_count, miss_count)`` for the skill.

        Used by ``SkillRegistry`` to restore the in-memory ints on
        startup so downstream callers that haven't migrated to the
        decayed-rate API still see the right ranking.
        """
        row = self._conn.execute(
            "SELECT "
            "  SUM(CASE WHEN kind='success' THEN 1 ELSE 0 END) AS s, "
            "  SUM(CASE WHEN kind='miss'    THEN 1 ELSE 0 END) AS m  "
            "FROM skill_telemetry WHERE skill_id = ?",
            (skill_id,),
        ).fetchone()
        if row is None:
            return (0, 0)
        return (int(row["s"] or 0), int(row["m"] or 0))

    def decayed_rate(
        self,
        skill_id: str,
        *,
        half_life_days: float = 14.0,
        now_unix: float | None = None,
    ) -> DecayedRate:
        """Decayed success rate using the half-life weight model.

        ``half_life_days = 14`` is the Argus default — recent enough
        to track regressions, slow enough that a single bad day
        doesn't bury a previously-strong skill.
        """
        if half_life_days <= 0:
            raise ValueError("half_life_days must be > 0")
        now = float(now_unix) if now_unix is not None else time.time()
        events = self.events(skill_id)
        if not events:
            return DecayedRate(skill_id=skill_id, success_weight=0.0, total_weight=0.0, n_events=0)
        ln_half = math.log(0.5)
        seconds_per_day = 86400.0
        total_w = 0.0
        succ_w = 0.0
        for ev in events:
            age_days = max(0.0, (now - ev.ts_unix) / seconds_per_day)
            w = math.exp(ln_half * (age_days / half_life_days))
            total_w += w
            if ev.is_success:
                succ_w += w
        return DecayedRate(
            skill_id=skill_id,
            success_weight=succ_w,
            total_weight=total_w,
            n_events=len(events),
        )

    # --------------------------------------------------- maintenance

    def all_skill_ids(self) -> set[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT skill_id FROM skill_telemetry"
        ).fetchall()
        return {r["skill_id"] for r in rows}

    def prune_before(self, *, ts_unix: float) -> int:
        """Drop events older than ``ts_unix``. Returns rows deleted."""
        cur = self._conn.execute(
            "DELETE FROM skill_telemetry WHERE ts_unix < ?",
            (float(ts_unix),),
        )
        self._conn.commit()
        return int(cur.rowcount or 0)

    def close(self) -> None:
        self._conn.close()
