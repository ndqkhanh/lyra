"""Fork-from-Checkpoint Session Exploration — P1-B6 (HIGH, MED).

Snapshot agent state at any point, fork into independent sessions,
and track parent-child lineage. Each fork is a complete copy of the
agent state at the checkpoint, allowing parallel exploration of
different decision paths.

See: plan-phase1-harness.md §4.6, Claude Code checkpointing
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Session Snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionSnapshot:
    """An immutable capture of agent state at a point in time.

    Snapshots are the basis for forking — each fork starts from a snapshot
    and diverges independently.
    """

    snapshot_id: str
    parent_session_id: str
    timestamp: float
    label: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp


# ---------------------------------------------------------------------------
# Session Fork
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionFork:
    """A forked session created from a snapshot."""

    fork_id: str
    snapshot_id: str
    parent_session_id: str
    created_at: float
    label: str = ""
    status: str = "active"  # active, completed, abandoned, merged

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at


# ---------------------------------------------------------------------------
# Checkpoint Store
# ---------------------------------------------------------------------------


@dataclass
class CheckpointStore:
    """Stores session snapshots and manages forking.

    Each session can have multiple snapshots. Snapshots can be forked
    into independent sessions that share the parent's state at the
    snapshot point but diverge thereafter.
    """

    _snapshots: dict[str, list[SessionSnapshot]] = field(default_factory=dict)
    _forks: dict[str, list[SessionFork]] = field(default_factory=dict)
    _fork_index: dict[str, SessionFork] = field(default_factory=dict)
    _lineage: dict[str, str] = field(default_factory=dict)  # fork_id → parent_session_id

    # --- Snapshots ------------------------------------------------------------

    def create_snapshot(
        self,
        session_id: str,
        *,
        label: str = "",
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SessionSnapshot:
        """Capture the current state of a session as a snapshot."""
        snap = SessionSnapshot(
            snapshot_id=_new_id("snap"),
            parent_session_id=session_id,
            timestamp=time.time(),
            label=label,
            context=context or {},
            metadata=metadata or {},
        )
        if session_id not in self._snapshots:
            self._snapshots[session_id] = []
        self._snapshots[session_id].append(snap)
        return snap

    def get_snapshots(self, session_id: str) -> list[SessionSnapshot]:
        """Get all snapshots for a session, ordered by timestamp."""
        return list(self._snapshots.get(session_id, []))

    def get_snapshot(self, snapshot_id: str) -> SessionSnapshot | None:
        """Find a snapshot by ID."""
        for snaps in self._snapshots.values():
            for s in snaps:
                if s.snapshot_id == snapshot_id:
                    return s
        return None

    def latest_snapshot(self, session_id: str) -> SessionSnapshot | None:
        """Get the most recent snapshot for a session."""
        snaps = self.get_snapshots(session_id)
        return snaps[-1] if snaps else None

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot. Returns True if found."""
        for sid, snaps in self._snapshots.items():
            for i, s in enumerate(snaps):
                if s.snapshot_id == snapshot_id:
                    snaps.pop(i)
                    if not snaps:
                        del self._snapshots[sid]
                    return True
        return False

    def snapshot_count(self, session_id: str | None = None) -> int:
        """Count snapshots, optionally filtered by session."""
        if session_id:
            return len(self._snapshots.get(session_id, []))
        return sum(len(s) for s in self._snapshots.values())

    # --- Forking --------------------------------------------------------------

    def fork(
        self,
        snapshot_id: str,
        *,
        label: str = "",
    ) -> SessionFork | None:
        """Create a new forked session from a snapshot.

        The fork gets a copy of the snapshot's context and starts
        as an independent session.
        """
        snap = self.get_snapshot(snapshot_id)
        if snap is None:
            return None

        fork = SessionFork(
            fork_id=_new_id("fork"),
            snapshot_id=snapshot_id,
            parent_session_id=snap.parent_session_id,
            created_at=time.time(),
            label=label,
        )

        # Index the fork
        self._fork_index[fork.fork_id] = fork
        self._lineage[fork.fork_id] = snap.parent_session_id

        # Store under parent
        if snap.parent_session_id not in self._forks:
            self._forks[snap.parent_session_id] = []
        self._forks[snap.parent_session_id].append(fork)

        return fork

    def get_fork(self, fork_id: str) -> SessionFork | None:
        """Get a fork by ID."""
        return self._fork_index.get(fork_id)

    def get_forks(self, session_id: str) -> list[SessionFork]:
        """Get all forks created from a session's snapshots."""
        return list(self._forks.get(session_id, []))

    def fork_count(self, session_id: str | None = None) -> int:
        """Count forks, optionally filtered by parent session."""
        if session_id:
            return len(self._forks.get(session_id, []))
        return len(self._fork_index)

    def complete_fork(self, fork_id: str) -> bool:
        """Mark a fork as completed."""
        fork = self._fork_index.get(fork_id)
        if fork is None:
            return False
        # Create updated fork (frozen, so we replace)
        updated = SessionFork(
            fork_id=fork.fork_id,
            snapshot_id=fork.snapshot_id,
            parent_session_id=fork.parent_session_id,
            created_at=fork.created_at,
            label=fork.label,
            status="completed",
        )
        self._fork_index[fork_id] = updated
        # Update in the parent's list too
        for flist in self._forks.values():
            for i, f in enumerate(flist):
                if f.fork_id == fork_id:
                    flist[i] = updated
                    return True
        return True

    def abandon_fork(self, fork_id: str) -> bool:
        """Mark a fork as abandoned."""
        fork = self._fork_index.get(fork_id)
        if fork is None:
            return False
        updated = SessionFork(
            fork_id=fork.fork_id,
            snapshot_id=fork.snapshot_id,
            parent_session_id=fork.parent_session_id,
            created_at=fork.created_at,
            label=fork.label,
            status="abandoned",
        )
        self._fork_index[fork_id] = updated
        for flist in self._forks.values():
            for i, f in enumerate(flist):
                if f.fork_id == fork_id:
                    flist[i] = updated
                    return True
        return True

    def merge_fork(self, fork_id: str) -> bool:
        """Mark a fork as merged back into the parent session."""
        fork = self._fork_index.get(fork_id)
        if fork is None:
            return False
        updated = SessionFork(
            fork_id=fork.fork_id,
            snapshot_id=fork.snapshot_id,
            parent_session_id=fork.parent_session_id,
            created_at=fork.created_at,
            label=fork.label,
            status="merged",
        )
        self._fork_index[fork_id] = updated
        for flist in self._forks.values():
            for i, f in enumerate(flist):
                if f.fork_id == fork_id:
                    flist[i] = updated
                    return True
        return True

    def active_forks(self, session_id: str | None = None) -> list[SessionFork]:
        """Get all active (non-completed, non-abandoned) forks."""
        if session_id:
            forks = self._forks.get(session_id, [])
        else:
            forks = list(self._fork_index.values())
        return [f for f in forks if f.status == "active"]

    # --- Lineage --------------------------------------------------------------

    def parent_session(self, fork_id: str) -> str | None:
        """Get the parent session ID for a fork."""
        return self._lineage.get(fork_id)

    def sibling_forks(self, fork_id: str) -> list[SessionFork]:
        """Get all forks that share the same parent as the given fork."""
        fork = self._fork_index.get(fork_id)
        if fork is None:
            return []
        siblings = []
        for f in self._forks.get(fork.parent_session_id, []):
            if f.fork_id != fork_id and f.snapshot_id == fork.snapshot_id:
                siblings.append(f)
        return siblings

    def fork_tree(self, session_id: str) -> dict[str, Any]:
        """Build a tree view of a session's fork lineage."""
        snaps = self.get_snapshots(session_id)
        forks = self.get_forks(session_id)

        return {
            "session_id": session_id,
            "snapshot_count": len(snaps),
            "fork_count": len(forks),
            "active_forks": len([f for f in forks if f.status == "active"]),
            "completed_forks": len([f for f in forks if f.status == "completed"]),
            "abandoned_forks": len([f for f in forks if f.status == "abandoned"]),
            "snapshots": [
                {
                    "snapshot_id": s.snapshot_id,
                    "label": s.label,
                    "timestamp": s.timestamp,
                    "fork_count": sum(1 for f in forks if f.snapshot_id == s.snapshot_id),
                }
                for s in snaps
            ],
        }

    # --- Cleanup --------------------------------------------------------------

    def prune_old_snapshots(self, session_id: str, max_age_seconds: float) -> int:
        """Remove snapshots older than max_age_seconds. Returns count removed."""
        cutoff = time.time() - max_age_seconds
        removed = 0
        snaps = self._snapshots.get(session_id, [])
        kept = [s for s in snaps if s.timestamp >= cutoff]
        removed = len(snaps) - len(kept)
        if kept:
            self._snapshots[session_id] = kept
        elif session_id in self._snapshots:
            del self._snapshots[session_id]
        return removed

    def clear(self) -> None:
        """Remove all snapshots and forks."""
        self._snapshots.clear()
        self._forks.clear()
        self._fork_index.clear()
        self._lineage.clear()

    @property
    def total_snapshots(self) -> int:
        return sum(len(s) for s in self._snapshots.values())

    @property
    def total_forks(self) -> int:
        return len(self._fork_index)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id(prefix: str) -> str:
    """Generate a short unique ID with a prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


__all__ = [
    "CheckpointStore",
    "SessionFork",
    "SessionSnapshot",
]
