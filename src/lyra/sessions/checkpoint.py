"""
Checkpoint manager — crash recovery and agent state snapshots on top of SessionManager.

Stores full agent-state snapshots as checkpoints, detects interrupted sessions,
and supports recovery from the latest checkpoint with automatic pruning of old
checkpoints.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from lyra.sessions.persist import SessionManager, SessionStatus

logger = structlog.get_logger(__name__)

DEFAULT_STALE_MINUTES = 5
MAX_CHECKPOINTS_PER_SESSION = 50


@dataclass
class CheckpointRecord:
    """A single checkpoint snapshot for a session."""

    checkpoint_id: int
    session_id: str
    checkpoint_index: int
    state: dict[str, Any]
    created_at: datetime


class CheckpointManager:
    """
    Crash-recovery layer on top of SessionManager.

    Stores checkpoint snapshots in a dedicated SQLite table, detects
    interrupted ACTIVE sessions, restores from the last checkpoint,
    and auto-prunes old checkpoints to bound storage.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        *,
        stale_minutes: int = DEFAULT_STALE_MINUTES,
        max_checkpoints: int = MAX_CHECKPOINTS_PER_SESSION,
    ) -> None:
        """
        Initialize the checkpoint manager.

        Args:
            session_manager: The underlying SessionManager instance.
            stale_minutes: Minutes of inactivity after which a session is
                considered interrupted.
            max_checkpoints: Maximum number of checkpoints to retain per
                session before pruning.
        """
        self._sm = session_manager
        self._stale_minutes = stale_minutes
        self._max_checkpoints = max_checkpoints
        self._lock = threading.Lock()
        self._initialize_checkpoint_table()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _initialize_checkpoint_table(self) -> None:
        """Create the checkpoint table if it does not exist."""
        conn = self._sm._conn
        if conn is None:
            return
        with self._sm._lock:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_checkpoints (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id       TEXT NOT NULL REFERENCES sessions(session_id),
                    checkpoint_index INTEGER NOT NULL,
                    state_data       TEXT NOT NULL,
                    created_at       TEXT NOT NULL,
                    UNIQUE(session_id, checkpoint_index)
                )
            """)
            self._sm._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ckpt_session
                ON session_checkpoints(session_id)
            """)
            self._sm._conn.commit()

    # ------------------------------------------------------------------
    # Checkpoint CRUD
    # ------------------------------------------------------------------

    def save_checkpoint(
        self,
        session_id: str,
        state: dict[str, Any],
    ) -> CheckpointRecord | None:
        """
        Save a checkpoint snapshot for the given session.

        The session must already exist in the SessionManager.  After saving,
        any excess checkpoints beyond ``max_checkpoints`` are pruned.

        Args:
            session_id: The session identifier.
            state: Full agent state dict to snapshot.

        Returns:
            The new CheckpointRecord, or None if the session does not exist.
        """
        record = self._sm.get_session(session_id)
        if record is None:
            logger.warning("checkpoint_save_skipped", session_id=session_id, reason="session_not_found")
            return None

        now = datetime.now(timezone.utc)

        # Determine the next checkpoint index for this session
        next_index = self._next_checkpoint_index(session_id)

        with self._lock:
            self._sm._conn.execute(
                """INSERT OR IGNORE INTO session_checkpoints
                   (session_id, checkpoint_index, state_data, created_at)
                   VALUES (?, ?, ?, ?)""",
                (session_id, next_index, json.dumps(state), now.isoformat()),
            )
            self._sm._conn.commit()

        cp = CheckpointRecord(
            checkpoint_id=0,  # will be updated below
            session_id=session_id,
            checkpoint_index=next_index,
            state=state,
            created_at=now,
        )

        # Re-read to get the actual rowid
        rows = self._sm._conn.execute(
            "SELECT id FROM session_checkpoints WHERE session_id=? AND checkpoint_index=?",
            (session_id, next_index),
        ).fetchall()
        if rows:
            cp.checkpoint_id = rows[0]["id"]

        self._prune(session_id)
        logger.info("checkpoint_saved", session_id=session_id, checkpoint_index=next_index)
        return cp

    def restore_checkpoint(
        self,
        session_id: str,
    ) -> dict[str, Any] | None:
        """
        Return the state data from the most recent checkpoint, or None.

        Args:
            session_id: The session identifier.

        Returns:
            The state dict of the latest checkpoint, or None.
        """
        row = self._sm._conn.execute(
            """SELECT state_data FROM session_checkpoints
               WHERE session_id = ?
               ORDER BY checkpoint_index DESC LIMIT 1""",
            (session_id,),
        ).fetchone()

        if row is None:
            return None

        return json.loads(row["state_data"])

    def list_checkpoints(
        self,
        session_id: str,
    ) -> list[CheckpointRecord]:
        """
        List all checkpoints for a session, ordered by index ascending.

        Args:
            session_id: The session identifier.

        Returns:
            List of CheckpointRecord objects.
        """
        rows = self._sm._conn.execute(
            """SELECT id, session_id, checkpoint_index, state_data, created_at
               FROM session_checkpoints
               WHERE session_id = ?
               ORDER BY checkpoint_index ASC""",
            (session_id,),
        ).fetchall()

        return [
            CheckpointRecord(
                checkpoint_id=r["id"],
                session_id=r["session_id"],
                checkpoint_index=r["checkpoint_index"],
                state=json.loads(r["state_data"]),
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Crash / interruption detection
    # ------------------------------------------------------------------

    def detect_interrupted(
        self,
        *,
        stale_minutes: int | None = None,
    ) -> list[str]:
        """
        Find ACTIVE sessions whose last activity is past the stale threshold.

        A session is considered interrupted if:
        - Its status is ACTIVE, AND
        - Its ``updated_at`` timestamp is older than ``stale_minutes``, AND
        - It has at least one checkpoint (so recovery is possible).

        Args:
            stale_minutes: Override the default stale threshold for this
                query.  Uses the instance default if not provided.

        Returns:
            List of session_id strings for interrupted sessions.
        """
        threshold_minutes = stale_minutes if stale_minutes is not None else self._stale_minutes
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)
        cutoff_str = cutoff.isoformat()

        # ACTIVE sessions with updated_at before cutoff --- must have at least one checkpoint
        rows = self._sm._conn.execute(
            """SELECT s.session_id
               FROM sessions s
               WHERE s.status = ?
                 AND s.updated_at < ?
                 AND EXISTS (
                   SELECT 1 FROM session_checkpoints c
                   WHERE c.session_id = s.session_id
                 )
               ORDER BY s.updated_at ASC""",
            (SessionStatus.ACTIVE.value, cutoff_str),
        ).fetchall()

        return [r["session_id"] for r in rows]

    def recover(
        self,
        session_id: str,
        *,
        mark_paused: bool = True,
    ) -> dict[str, Any] | None:
        """
        Recover a session from its latest checkpoint.

        Restores the agent state from the most recent checkpoint.  Optionally
        marks the session status as PAUSED so it is not picked up again by
        ``detect_interrupted``.

        Args:
            session_id: The session identifier.
            mark_paused: If True (default), set session status to PAUSED
                to prevent re-detection.

        Returns:
            The restored state dict, or None if no checkpoint exists.
        """
        state = self.restore_checkpoint(session_id)
        if state is None:
            logger.warning("recovery_failed_no_checkpoint", session_id=session_id)
            return None

        if mark_paused:
            self._sm.update_session(session_id, status=SessionStatus.PAUSED)

        logger.info("session_recovered", session_id=session_id)
        return state

    # ------------------------------------------------------------------
    # Pruning
    # ------------------------------------------------------------------

    def _prune(self, session_id: str) -> None:
        """
        Remove excess checkpoints for a session, keeping only the most recent
        ``max_checkpoints`` entries.
        """
        with self._lock:
            # Count current checkpoints
            row = self._sm._conn.execute(
                "SELECT COUNT(*) AS cnt FROM session_checkpoints WHERE session_id=?",
                (session_id,),
            ).fetchone()
            count = row["cnt"] if row else 0

            if count <= self._max_checkpoints:
                return

            # Delete oldest ones beyond the limit
            self._sm._conn.execute(
                """DELETE FROM session_checkpoints
                   WHERE session_id = ?
                     AND checkpoint_index NOT IN (
                       SELECT checkpoint_index FROM session_checkpoints
                       WHERE session_id = ?
                       ORDER BY checkpoint_index DESC
                       LIMIT ?
                     )""",
                (session_id, session_id, self._max_checkpoints),
            )
            self._sm._conn.commit()

            logger.info(
                "checkpoints_pruned",
                session_id=session_id,
                kept=self._max_checkpoints,
                total_removed=count - self._max_checkpoints,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_checkpoint_index(self, session_id: str) -> int:
        """Return the next available checkpoint index (max + 1, or 0)."""
        row = self._sm._conn.execute(
            "SELECT COALESCE(MAX(checkpoint_index), -1) + 1 AS nxt FROM session_checkpoints WHERE session_id=?",
            (session_id,),
        ).fetchone()
        return row["nxt"] if row else 0
