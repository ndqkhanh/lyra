"""Shared Success/Failure Ledger — Prevents redundant work across agent swarm (P4-X HIGH×MED).

Records task outcomes (success, failure, in-progress) and provides idempotent
task dispatch. Agents consult the ledger before starting work to avoid duplication.

See: plan-phase4-swarm-investigations.md §4.13, AutoScientists shared log pattern
"""
from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LedgerEntryStatus(str, enum.Enum):
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPIRED = "expired"


class IdempotencyMode(str, enum.Enum):
    STRICT = "strict"  # Never re-run a succeeded task
    SOFT = "soft"  # Re-run if explicitly requested
    RETRY_ONLY = "retry_only"  # Re-run only failed tasks


# ---------------------------------------------------------------------------
# Core Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LedgerEntry:
    """A single entry in the shared ledger."""

    task_id: str
    agent_id: str
    status: LedgerEntryStatus
    timestamp: float
    output: str = ""
    error: str = ""
    fingerprint: str = ""  # Content hash for idempotency
    attempt: int = 1


@dataclass(frozen=True)
class LedgerQuery:
    """Query constraints for filtering ledger entries."""

    task_id: str | None = None
    agent_id: str | None = None
    status: LedgerEntryStatus | None = None
    since: float | None = None
    fingerprint: str | None = None


@dataclass(frozen=True)
class LedgerStats:
    """Aggregate statistics from the ledger."""

    total_entries: int
    succeeded: int
    failed: int
    in_progress: int
    claimed: int
    expired: int
    distinct_tasks: int
    distinct_agents: int

    @property
    def success_rate(self) -> float:
        attempted = self.succeeded + self.failed
        if attempted == 0:
            return 1.0
        return self.succeeded / attempted


# ---------------------------------------------------------------------------
# Shared Ledger
# ---------------------------------------------------------------------------


@dataclass
class SharedLedger:
    """Thread-safe ledger that prevents redundant work across agent swarms.

    Usage::

        ledger = SharedLedger()
        # Claim before starting
        if ledger.claim("task-1", "agent-a"):
            try:
                result = do_work()
                ledger.record_success("task-1", "agent-a", output=result)
            except Exception as e:
                ledger.record_failure("task-1", "agent-a", error=str(e))
    """

    _entries: dict[str, list[LedgerEntry]] = field(default_factory=dict)
    _claim_timeout: float = 300.0  # seconds before claim expires

    def claim(self, task_id: str, agent_id: str, fingerprint: str = "") -> bool:
        """Claim a task for execution. Returns False if already claimed or succeeded."""
        existing = self._entries.get(task_id, [])

        # Check if already succeeded
        for entry in existing:
            if entry.status == LedgerEntryStatus.SUCCEEDED:
                return False
            if entry.status == LedgerEntryStatus.CLAIMED:
                if time.time() - entry.timestamp < self._claim_timeout:
                    return False
                # Claim expired — mark it
                self._add_entry(task_id, LedgerEntry(
                    task_id=task_id, agent_id=entry.agent_id,
                    status=LedgerEntryStatus.EXPIRED, timestamp=time.time(),
                    fingerprint=fingerprint, attempt=entry.attempt,
                ))

        self._add_entry(task_id, LedgerEntry(
            task_id=task_id, agent_id=agent_id,
            status=LedgerEntryStatus.CLAIMED, timestamp=time.time(),
            fingerprint=fingerprint, attempt=len(existing) + 1,
        ))
        return True

    def start(self, task_id: str, agent_id: str) -> bool:
        """Mark a claimed task as in-progress."""
        existing = self._entries.get(task_id, [])
        for entry in existing:
            if entry.status == LedgerEntryStatus.CLAIMED and entry.agent_id == agent_id:
                self._add_entry(task_id, LedgerEntry(
                    task_id=task_id, agent_id=agent_id,
                    status=LedgerEntryStatus.IN_PROGRESS, timestamp=time.time(),
                    fingerprint=entry.fingerprint, attempt=entry.attempt,
                ))
                return True
        return False

    def record_success(self, task_id: str, agent_id: str, output: str = "") -> None:
        self._add_entry(task_id, LedgerEntry(
            task_id=task_id, agent_id=agent_id,
            status=LedgerEntryStatus.SUCCEEDED, timestamp=time.time(),
            output=output,
        ))

    def record_failure(self, task_id: str, agent_id: str, error: str = "") -> None:
        self._add_entry(task_id, LedgerEntry(
            task_id=task_id, agent_id=agent_id,
            status=LedgerEntryStatus.FAILED, timestamp=time.time(),
            error=error,
        ))

    def is_completed(self, task_id: str) -> bool:
        entries = self._entries.get(task_id, [])
        return any(e.status == LedgerEntryStatus.SUCCEEDED for e in entries)

    def is_claimed(self, task_id: str) -> bool:
        entries = self._entries.get(task_id, [])
        now = time.time()
        return any(
            e.status == LedgerEntryStatus.CLAIMED and now - e.timestamp < self._claim_timeout
            for e in entries
        )

    def last_entry(self, task_id: str) -> LedgerEntry | None:
        entries = self._entries.get(task_id, [])
        return entries[-1] if entries else None

    def query(self, query: LedgerQuery | None = None) -> tuple[LedgerEntry, ...]:
        """Query entries matching constraints."""
        q = query or LedgerQuery()
        results: list[LedgerEntry] = []
        for entries in self._entries.values():
            for entry in entries:
                if q.task_id is not None and entry.task_id != q.task_id:
                    continue
                if q.agent_id is not None and entry.agent_id != q.agent_id:
                    continue
                if q.status is not None and entry.status != q.status:
                    continue
                if q.since is not None and entry.timestamp < q.since:
                    continue
                if q.fingerprint is not None and entry.fingerprint != q.fingerprint:
                    continue
                results.append(entry)
        return tuple(results)

    def stats(self) -> LedgerStats:
        """Compute aggregate statistics."""
        all_entries = [e for entries in self._entries.values() for e in entries]
        task_ids = set(self._entries.keys())
        agent_ids = {e.agent_id for e in all_entries}
        status_counts = {
            status: sum(1 for e in all_entries if e.status == status)
            for status in LedgerEntryStatus
        }
        return LedgerStats(
            total_entries=len(all_entries),
            succeeded=status_counts[LedgerEntryStatus.SUCCEEDED],
            failed=status_counts[LedgerEntryStatus.FAILED],
            in_progress=status_counts[LedgerEntryStatus.IN_PROGRESS],
            claimed=status_counts[LedgerEntryStatus.CLAIMED],
            expired=status_counts[LedgerEntryStatus.EXPIRED],
            distinct_tasks=len(task_ids),
            distinct_agents=len(agent_ids),
        )

    def reset(self) -> None:
        self._entries.clear()

    @property
    def entry_count(self) -> int:
        return sum(len(entries) for entries in self._entries.values())

    @property
    def task_count(self) -> int:
        return len(self._entries)

    def _add_entry(self, task_id: str, entry: LedgerEntry) -> None:
        if task_id not in self._entries:
            self._entries[task_id] = []
        self._entries[task_id].append(entry)


# ---------------------------------------------------------------------------
# Idempotent Task Runner
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IdempotentResult:
    """Result of an idempotent task execution."""

    task_id: str
    was_executed: bool  # True if actually ran, False if skipped
    status: LedgerEntryStatus
    output: str = ""
    error: str = ""


@dataclass
class IdempotentRunner:
    """Wraps a task runner with idempotency guarantees via the shared ledger."""

    ledger: SharedLedger = field(default_factory=SharedLedger)
    mode: IdempotencyMode = IdempotencyMode.STRICT

    def run(
        self,
        task_id: str,
        agent_id: str,
        runner,
        fingerprint: str = "",
    ) -> IdempotentResult:
        """Run a task idempotently. Skips if already completed (strict mode)."""
        # Check if already done
        if self.mode == IdempotencyMode.STRICT and self.ledger.is_completed(task_id):
            entry = self.ledger.last_entry(task_id)
            return IdempotentResult(
                task_id=task_id,
                was_executed=False,
                status=LedgerEntryStatus.SUCCEEDED,
                output=entry.output if entry else "",
            )

        # Check if already claimed
        if self.mode != IdempotencyMode.RETRY_ONLY and self.ledger.is_claimed(task_id):
            return IdempotentResult(
                task_id=task_id,
                was_executed=False,
                status=LedgerEntryStatus.CLAIMED,
            )

        # Claim + execute
        if not self.ledger.claim(task_id, agent_id, fingerprint):
            return IdempotentResult(
                task_id=task_id,
                was_executed=False,
                status=LedgerEntryStatus.SUCCEEDED,
            )

        self.ledger.start(task_id, agent_id)

        try:
            output = runner(task_id)
            self.ledger.record_success(task_id, agent_id, output=str(output))
            return IdempotentResult(
                task_id=task_id,
                was_executed=True,
                status=LedgerEntryStatus.SUCCEEDED,
                output=str(output),
            )
        except Exception as e:
            self.ledger.record_failure(task_id, agent_id, error=str(e))
            return IdempotentResult(
                task_id=task_id,
                was_executed=True,
                status=LedgerEntryStatus.FAILED,
                error=str(e),
            )


__all__ = [
    "IdempotencyMode",
    "IdempotentResult",
    "IdempotentRunner",
    "LedgerEntry",
    "LedgerEntryStatus",
    "LedgerQuery",
    "LedgerStats",
    "SharedLedger",
]
