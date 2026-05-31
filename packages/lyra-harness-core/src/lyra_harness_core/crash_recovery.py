"""Append-Only Context Log for Crash Recovery — P1-X #16 (HIGH, LOW).

JSONL-based append-only log with checkpoint markers and crash recovery replay.
Builds on AppendOnlyContext from kv_cache.py for the in-memory buffer, adding
durable persistence and recovery.

See: plan-phase1-harness.md, Manus KV-cache pattern
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Log Entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LogEntry:
    """A single immutable entry in the append-only log."""

    sequence: int
    timestamp: float
    event: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {"seq": self.sequence, "ts": self.timestamp, "event": self.event, "data": self.data},
            sort_keys=True,
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, line: str) -> LogEntry:
        obj = json.loads(line)
        return cls(
            sequence=obj["seq"],
            timestamp=obj["ts"],
            event=obj["event"],
            data=obj.get("data", {}),
        )


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Checkpoint:
    """A recovery checkpoint within the log."""

    sequence: int
    timestamp: float
    label: str = ""
    snapshot: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Append-Only Log
# ---------------------------------------------------------------------------


@dataclass
class AppendOnlyLog:
    """A durable, append-only JSONL log.

    Every entry is written atomically (single-line JSON). Once written,
    entries are never modified — preserving crash-recovery semantics.

    Usage::

        log = AppendOnlyLog(Path("/tmp/agent.log"))
        log.append("tool_call", {"tool": "read", "path": "/tmp/x"})
        log.append("tool_result", {"result": "ok"})
        log.checkpoint(label="after_tool")

        # After crash:
        recovered = AppendOnlyLog(Path("/tmp/agent.log"))
        state = recovered.replay_until_checkpoint()
    """

    path: Path
    _next_sequence: int = field(default=0, init=False)
    _last_checkpoint: Checkpoint | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        # Recover the next sequence number from the existing file
        if self.path.exists():
            self._next_sequence = self._scan_last_sequence() + 1
        else:
            self._next_sequence = 0

    # --- Append ---------------------------------------------------------------

    def append(self, event: str, data: dict[str, Any] | None = None) -> LogEntry:
        """Append an event to the log. Returns the LogEntry."""
        entry = LogEntry(
            sequence=self._next_sequence,
            timestamp=time.time(),
            event=event,
            data=data or {},
        )
        line = entry.to_json() + "\n"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())  # durable write
        self._next_sequence += 1
        return entry

    def checkpoint(self, label: str = "", snapshot: dict[str, Any] | None = None) -> LogEntry:
        """Write a checkpoint marker into the log."""
        return self.append(
            "__checkpoint__",
            {"label": label, "snapshot": snapshot or {}},
        )

    def mark_start(self, metadata: dict[str, Any] | None = None) -> LogEntry:
        """Mark the start of a new session/run."""
        return self.append("__session_start__", metadata or {})

    def mark_end(self, metadata: dict[str, Any] | None = None) -> LogEntry:
        """Mark a clean session end."""
        return self.append("__session_end__", metadata or {})

    def mark_error(self, error: str, context: dict[str, Any] | None = None) -> LogEntry:
        """Record an error event."""
        data = {"error": error, **(context or {})}
        return self.append("__error__", data)

    # --- Read / Replay --------------------------------------------------------

    def entries(self) -> list[LogEntry]:
        """Read all entries from the log."""
        if not self.path.exists():
            return []
        result: list[LogEntry] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    result.append(LogEntry.from_json(line))
        return result

    def entries_since(self, since_sequence: int) -> list[LogEntry]:
        """Read entries since a given sequence number (exclusive)."""
        return [e for e in self.entries() if e.sequence > since_sequence]

    def checkpoints(self) -> list[Checkpoint]:
        """Extract all checkpoints from the log."""
        result: list[Checkpoint] = []
        for entry in self.entries():
            if entry.event == "__checkpoint__":
                result.append(Checkpoint(
                    sequence=entry.sequence,
                    timestamp=entry.timestamp,
                    label=entry.data.get("label", ""),
                    snapshot=entry.data.get("snapshot", {}),
                ))
        return result

    def last_checkpoint(self) -> Checkpoint | None:
        """Return the most recent checkpoint, or None."""
        cps = self.checkpoints()
        return cps[-1] if cps else None

    def replay_until_checkpoint(self) -> tuple[Checkpoint | None, list[LogEntry]]:
        """Replay: find the last checkpoint and return it plus all entries after.

        Returns (last_checkpoint_or_None, entries_after_checkpoint).
        Callers can reconstruct state by applying entries after the checkpoint.
        """
        cps = self.checkpoints()
        if not cps:
            return None, self.entries()

        last_cp = cps[-1]
        after = self.entries_since(last_cp.sequence)
        return last_cp, after

    def entries_by_event(self, event: str) -> list[LogEntry]:
        """Filter entries by event type."""
        return [e for e in self.entries() if e.event == event]

    # --- Stats ----------------------------------------------------------------

    @property
    def entry_count(self) -> int:
        if not self.path.exists():
            return 0
        count = 0
        with open(self.path, "r", encoding="utf-8") as f:
            for _ in f:
                count += 1
        return count

    @property
    def size_bytes(self) -> int:
        if not self.path.exists():
            return 0
        return self.path.stat().st_size

    @property
    def last_sequence(self) -> int:
        return max(self._next_sequence - 1, -1)

    @property
    def is_empty(self) -> bool:
        return self.entry_count == 0

    # --- Maintenance ----------------------------------------------------------

    def clear(self) -> None:
        """Delete the log file and reset state."""
        if self.path.exists():
            self.path.unlink()
        self._next_sequence = 0
        self._last_checkpoint = None

    def truncate_before(self, before_sequence: int) -> int:
        """Remove entries before a sequence number. Returns count removed.

        Useful for log rotation: keep only recent entries.
        """
        entries = self.entries()
        kept = [e for e in entries if e.sequence >= before_sequence]
        removed = len(entries) - len(kept)

        if removed > 0 and kept:
            self.path.write_text(
                "".join(e.to_json() + "\n" for e in kept),
                encoding="utf-8",
            )
        elif not kept:
            self.clear()

        return removed

    # --- Internal -------------------------------------------------------------

    def _scan_last_sequence(self) -> int:
        """Scan the log file to find the last sequence number."""
        last = -1
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        obj = json.loads(line)
                        last = max(last, obj.get("seq", -1))
                    except json.JSONDecodeError:
                        continue
        return last


# ---------------------------------------------------------------------------
# Crash Recovery
# ---------------------------------------------------------------------------


@dataclass
class CrashRecovery:
    """Recover agent state from an append-only log after a crash.

    Usage::

        recovery = CrashRecovery(log)
        if recovery.was_clean_shutdown:
            print("Clean shutdown — nothing to recover")
        else:
            cp, pending = recovery.replay()
            # Rebuild state from cp.snapshot, then apply pending entries

        # Start new session:
        recovery.begin_session()
    """

    log: AppendOnlyLog

    def begin_session(self, metadata: dict[str, Any] | None = None) -> LogEntry:
        """Mark the start of a new session."""
        return self.log.mark_start(metadata or {})

    def end_session(self, metadata: dict[str, Any] | None = None) -> LogEntry:
        """Mark a clean session end."""
        return self.log.mark_end(metadata or {})

    @property
    def was_clean_shutdown(self) -> bool:
        """Check if the last session ended cleanly."""
        entries = self.log.entries()
        for e in reversed(entries):
            if e.event == "__session_end__":
                return True
            if e.event == "__session_start__":
                return False
        return False

    @property
    def last_error(self) -> LogEntry | None:
        """Return the most recent error entry, if any."""
        errors = self.log.entries_by_event("__error__")
        return errors[-1] if errors else None

    def replay(self) -> tuple[Checkpoint | None, list[LogEntry]]:
        """Replay the log: get the last checkpoint + pending entries.

        Returns (last_checkpoint, entries_after_checkpoint).
        Callers rebuild state from the checkpoint snapshot, then
        re-apply each pending entry.
        """
        return self.log.replay_until_checkpoint()

    def last_session_entries(self) -> list[LogEntry]:
        """Get entries from the most recent session (since last __session_start__)."""
        entries = self.log.entries()
        session_start_idx = -1
        for i, e in enumerate(entries):
            if e.event == "__session_start__":
                session_start_idx = i
        if session_start_idx == -1:
            return entries
        return entries[session_start_idx:]

    def session_count(self) -> int:
        """Count the number of sessions in the log."""
        return len(self.log.entries_by_event("__session_start__"))

    def error_count(self) -> int:
        """Count the number of error entries in the log."""
        return len(self.log.entries_by_event("__error__"))

    @property
    def is_empty(self) -> bool:
        return self.log.is_empty

    def clear(self) -> None:
        """Clear the log and start fresh."""
        self.log.clear()


__all__ = [
    "AppendOnlyLog",
    "Checkpoint",
    "CrashRecovery",
    "LogEntry",
]
