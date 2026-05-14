"""Agent Execution Record (AER) — Phase A of the Lyra 322-326 evolution plan.

Every Lyra turn emits an AER that captures *why* the agent chose an
action, what evidence supported it, and how confident it was.  This is
the queryable audit trail that powers the SLO cockpit, trace-grounded
Reflexion (Phase E), and the fleet attention queue (Phase D).

Grounded in:
- arXiv:2603.21692 — Reasoning Provenance for Autonomous AI Agents
- Doc 322 — Agent Split View Monitoring 2026
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Generator, Literal, Optional


__all__ = [
    "AgentExecutionRecord",
    "AERStore",
    "new_aer",
]

ModelTier = Literal["fast", "reasoning", "advisor"]


@dataclass
class AgentExecutionRecord:
    """One turn's observable reasoning + runtime state.

    Fields are intentionally flat (no nested objects) so the whole record
    serialises to a single SQLite row and can be queried without joins.
    """

    # --- Identity ---
    run_id: str
    session_id: str
    turn_index: int
    trace_id: str = ""

    # --- Semantic state (AER core — arXiv:2603.21692) ---
    intent: str = ""
    observation: str = ""
    inference: str = ""
    evidence_refs: str = ""          # JSON-encoded list[str]
    confidence: float = 0.0
    revision_rationale: str = ""

    # --- Tool state ---
    tool_name: str = ""
    tool_args_hash: str = ""
    tool_result_hash: str = ""
    tool_duration_ms: int = 0
    tool_cost_usd: float = 0.0

    # --- Local runtime (abtop-inspired) ---
    context_window_pct: float = 0.0
    tokens_input: int = 0
    tokens_output: int = 0
    child_pids: str = ""             # JSON-encoded list[int]
    open_ports: str = ""             # JSON-encoded list[int]
    git_ref: str = ""
    git_dirty: bool = False

    # --- Model routing (Phase B) ---
    model_tier: ModelTier = "fast"
    route_reason: str = ""
    escalation_trigger: str = ""
    advisor_delta: str = ""

    # --- Safety ---
    permission_decision: str = ""
    policy_gate: str = ""

    # --- Eval ---
    verifier_verdict: str = ""
    eval_link: str = ""

    # --- Housekeeping ---
    ts: float = field(default_factory=time.time)

    # ------------------------------------------------------------------ #
    # Convenience accessors                                                #
    # ------------------------------------------------------------------ #

    def evidence_list(self) -> list[str]:
        if not self.evidence_refs:
            return []
        try:
            return json.loads(self.evidence_refs)
        except json.JSONDecodeError:
            return []

    def pid_list(self) -> list[int]:
        if not self.child_pids:
            return []
        try:
            return json.loads(self.child_pids)
        except json.JSONDecodeError:
            return []

    def port_list(self) -> list[int]:
        if not self.open_ports:
            return []
        try:
            return json.loads(self.open_ports)
        except json.JSONDecodeError:
            return []

    def to_dict(self) -> dict:
        return asdict(self)


def new_aer(
    run_id: str,
    session_id: str,
    turn_index: int,
    *,
    intent: str = "",
    model_tier: ModelTier = "fast",
) -> AgentExecutionRecord:
    """Factory — create a fresh AER for a new turn."""
    return AgentExecutionRecord(
        run_id=run_id,
        session_id=session_id,
        turn_index=turn_index,
        intent=intent,
        model_tier=model_tier,
    )


# ------------------------------------------------------------------ #
# Persistence                                                          #
# ------------------------------------------------------------------ #

_DDL = """
CREATE TABLE IF NOT EXISTS agent_execution_records (
    rowid               INTEGER PRIMARY KEY,
    run_id              TEXT NOT NULL,
    session_id          TEXT NOT NULL,
    turn_index          INTEGER NOT NULL,
    trace_id            TEXT,
    intent              TEXT,
    observation         TEXT,
    inference           TEXT,
    evidence_refs       TEXT,
    confidence          REAL,
    revision_rationale  TEXT,
    tool_name           TEXT,
    tool_args_hash      TEXT,
    tool_result_hash    TEXT,
    tool_duration_ms    INTEGER,
    tool_cost_usd       REAL,
    context_window_pct  REAL,
    tokens_input        INTEGER,
    tokens_output       INTEGER,
    child_pids          TEXT,
    open_ports          TEXT,
    git_ref             TEXT,
    git_dirty           INTEGER,
    model_tier          TEXT,
    route_reason        TEXT,
    escalation_trigger  TEXT,
    advisor_delta       TEXT,
    permission_decision TEXT,
    policy_gate         TEXT,
    verifier_verdict    TEXT,
    eval_link           TEXT,
    ts                  REAL
);
CREATE INDEX IF NOT EXISTS idx_aer_session
    ON agent_execution_records(session_id, turn_index);
CREATE INDEX IF NOT EXISTS idx_aer_run
    ON agent_execution_records(run_id);
"""

_INSERT = """
INSERT INTO agent_execution_records (
    run_id, session_id, turn_index, trace_id,
    intent, observation, inference, evidence_refs, confidence, revision_rationale,
    tool_name, tool_args_hash, tool_result_hash, tool_duration_ms, tool_cost_usd,
    context_window_pct, tokens_input, tokens_output,
    child_pids, open_ports, git_ref, git_dirty,
    model_tier, route_reason, escalation_trigger, advisor_delta,
    permission_decision, policy_gate, verifier_verdict, eval_link, ts
) VALUES (
    :run_id, :session_id, :turn_index, :trace_id,
    :intent, :observation, :inference, :evidence_refs, :confidence, :revision_rationale,
    :tool_name, :tool_args_hash, :tool_result_hash, :tool_duration_ms, :tool_cost_usd,
    :context_window_pct, :tokens_input, :tokens_output,
    :child_pids, :open_ports, :git_ref, :git_dirty,
    :model_tier, :route_reason, :escalation_trigger, :advisor_delta,
    :permission_decision, :policy_gate, :verifier_verdict, :eval_link, :ts
)
"""


class AERStore:
    """SQLite-backed store for AgentExecutionRecords.

    Thread-safe for single-process use (SQLite WAL mode + check_same_thread=False).
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._path = str(db_path)
        self._conn = sqlite3.connect(
            self._path,
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_DDL)
        self._conn.commit()

    # ---------------------------------------------------------------- #

    def write(self, rec: AgentExecutionRecord) -> None:
        """Persist one AER."""
        row = rec.to_dict()
        row["git_dirty"] = int(row["git_dirty"])
        self._conn.execute(_INSERT, row)
        self._conn.commit()

    def fetch_session(
        self, session_id: str, limit: int = 50
    ) -> list[AgentExecutionRecord]:
        """Retrieve the most recent *limit* records for a session."""
        cur = self._conn.execute(
            "SELECT * FROM agent_execution_records "
            "WHERE session_id = ? ORDER BY turn_index DESC LIMIT ?",
            (session_id, limit),
        )
        return [self._row_to_aer(r) for r in cur.fetchall()]

    def fetch_run(self, run_id: str) -> list[AgentExecutionRecord]:
        """Retrieve all records for a run, ordered by turn."""
        cur = self._conn.execute(
            "SELECT * FROM agent_execution_records "
            "WHERE run_id = ? ORDER BY turn_index",
            (run_id,),
        )
        return [self._row_to_aer(r) for r in cur.fetchall()]

    def latest(self, session_id: str) -> Optional[AgentExecutionRecord]:
        """Most recent record for a session, or None."""
        cur = self._conn.execute(
            "SELECT * FROM agent_execution_records "
            "WHERE session_id = ? ORDER BY turn_index DESC LIMIT 1",
            (session_id,),
        )
        row = cur.fetchone()
        return self._row_to_aer(row) if row else None

    def count(self, session_id: str) -> int:
        cur = self._conn.execute(
            "SELECT COUNT(*) FROM agent_execution_records WHERE session_id = ?",
            (session_id,),
        )
        return cur.fetchone()[0]

    def prune_older_than(self, cutoff_ts: float) -> int:
        """Delete records older than *cutoff_ts* (epoch seconds). Returns deleted count."""
        cur = self._conn.execute(
            "DELETE FROM agent_execution_records WHERE ts < ?", (cutoff_ts,)
        )
        self._conn.commit()
        return cur.rowcount

    # ---------------------------------------------------------------- #
    # Internal                                                           #
    # ---------------------------------------------------------------- #

    @staticmethod
    def _row_to_aer(row: sqlite3.Row) -> AgentExecutionRecord:
        d = dict(row)
        d.pop("rowid", None)
        d["git_dirty"] = bool(d["git_dirty"])
        return AgentExecutionRecord(**d)

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        try:
            yield
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def close(self) -> None:
        self._conn.close()
