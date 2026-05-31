"""Tests for ledger.py — Shared Success/Failure Ledger (P4-X HIGH×MED)."""
from __future__ import annotations

import pytest
from lyra_harness_core.ledger import (
    IdempotencyMode,
    IdempotentResult,
    IdempotentRunner,
    LedgerEntry,
    LedgerEntryStatus,
    LedgerQuery,
    LedgerStats,
    SharedLedger,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestLedgerEntryStatus:
    def test_values(self):
        assert LedgerEntryStatus.SUCCEEDED.value == "succeeded"
        assert LedgerEntryStatus.FAILED.value == "failed"
        assert LedgerEntryStatus.CLAIMED.value == "claimed"
        assert LedgerEntryStatus.IN_PROGRESS.value == "in_progress"
        assert LedgerEntryStatus.EXPIRED.value == "expired"

class TestIdempotencyMode:
    def test_values(self):
        assert IdempotencyMode.STRICT.value == "strict"
        assert IdempotencyMode.SOFT.value == "soft"
        assert IdempotencyMode.RETRY_ONLY.value == "retry_only"


# ---------------------------------------------------------------------------
# LedgerEntry
# ---------------------------------------------------------------------------

class TestLedgerEntry:
    def test_creation(self):
        entry = LedgerEntry(
            task_id="task-1", agent_id="agent-a",
            status=LedgerEntryStatus.CLAIMED, timestamp=100.0,
        )
        assert entry.task_id == "task-1"
        assert entry.agent_id == "agent-a"
        assert entry.status == LedgerEntryStatus.CLAIMED

    def test_defaults(self):
        entry = LedgerEntry(
            task_id="t1", agent_id="a1",
            status=LedgerEntryStatus.IN_PROGRESS, timestamp=0.0,
        )
        assert entry.output == ""
        assert entry.error == ""
        assert entry.fingerprint == ""
        assert entry.attempt == 1

    def test_frozen(self):
        entry = LedgerEntry(
            task_id="t1", agent_id="a1",
            status=LedgerEntryStatus.SUCCEEDED, timestamp=0.0,
        )
        with pytest.raises(Exception):
            entry.status = LedgerEntryStatus.FAILED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LedgerQuery
# ---------------------------------------------------------------------------

class TestLedgerQuery:
    def test_defaults(self):
        q = LedgerQuery()
        assert q.task_id is None
        assert q.agent_id is None

    def test_custom(self):
        q = LedgerQuery(task_id="t1", status=LedgerEntryStatus.SUCCEEDED)
        assert q.task_id == "t1"
        assert q.status == LedgerEntryStatus.SUCCEEDED

    def test_frozen(self):
        q = LedgerQuery()
        with pytest.raises(Exception):
            q.task_id = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LedgerStats
# ---------------------------------------------------------------------------

class TestLedgerStats:
    def test_success_rate(self):
        stats = LedgerStats(
            total_entries=5, succeeded=3, failed=1,
            in_progress=1, claimed=0, expired=0,
            distinct_tasks=3, distinct_agents=2,
        )
        assert stats.success_rate == 0.75

    def test_success_rate_no_attempts(self):
        stats = LedgerStats(
            total_entries=0, succeeded=0, failed=0,
            in_progress=0, claimed=0, expired=0,
            distinct_tasks=0, distinct_agents=0,
        )
        assert stats.success_rate == 1.0


# ---------------------------------------------------------------------------
# SharedLedger
# ---------------------------------------------------------------------------

class TestSharedLedger:
    def test_empty(self):
        ledger = SharedLedger()
        assert ledger.entry_count == 0
        assert ledger.task_count == 0

    def test_claim_succeeds(self):
        ledger = SharedLedger()
        assert ledger.claim("task-1", "agent-a")

    def test_claim_fails_when_already_claimed(self):
        ledger = SharedLedger()
        assert ledger.claim("task-1", "agent-a")
        assert not ledger.claim("task-1", "agent-b")

    def test_claim_fails_when_already_succeeded(self):
        ledger = SharedLedger()
        ledger.record_success("task-1", "agent-a")
        assert not ledger.claim("task-1", "agent-b")

    def test_is_completed(self):
        ledger = SharedLedger()
        assert not ledger.is_completed("task-1")
        ledger.record_success("task-1", "agent-a")
        assert ledger.is_completed("task-1")

    def test_is_claimed(self):
        ledger = SharedLedger()
        assert not ledger.is_claimed("task-1")
        ledger.claim("task-1", "agent-a")
        assert ledger.is_claimed("task-1")

    def test_record_success(self):
        ledger = SharedLedger()
        ledger.record_success("task-1", "agent-a", output="done")
        entry = ledger.last_entry("task-1")
        assert entry.status == LedgerEntryStatus.SUCCEEDED
        assert entry.output == "done"

    def test_record_failure(self):
        ledger = SharedLedger()
        ledger.record_failure("task-1", "agent-a", error="timeout")
        entry = ledger.last_entry("task-1")
        assert entry.status == LedgerEntryStatus.FAILED
        assert entry.error == "timeout"

    def test_start(self):
        ledger = SharedLedger()
        ledger.claim("task-1", "agent-a")
        assert ledger.start("task-1", "agent-a")
        entry = ledger.last_entry("task-1")
        assert entry.status == LedgerEntryStatus.IN_PROGRESS

    def test_start_fails_if_not_claimed(self):
        ledger = SharedLedger()
        assert not ledger.start("task-1", "agent-a")

    def test_last_entry_none(self):
        ledger = SharedLedger()
        assert ledger.last_entry("nonexistent") is None

    def test_query_by_task_id(self):
        ledger = SharedLedger()
        ledger.record_success("task-1", "agent-a")
        ledger.record_failure("task-2", "agent-b")
        results = ledger.query(LedgerQuery(task_id="task-1"))
        assert len(results) == 1
        assert results[0].task_id == "task-1"

    def test_query_by_agent_id(self):
        ledger = SharedLedger()
        ledger.record_success("task-1", "agent-a")
        ledger.record_failure("task-2", "agent-b")
        results = ledger.query(LedgerQuery(agent_id="agent-b"))
        assert len(results) == 1

    def test_query_by_status(self):
        ledger = SharedLedger()
        ledger.record_success("task-1", "agent-a")
        ledger.record_failure("task-2", "agent-a")
        results = ledger.query(LedgerQuery(status=LedgerEntryStatus.FAILED))
        assert len(results) == 1

    def test_query_empty(self):
        ledger = SharedLedger()
        assert ledger.query() == ()

    def test_stats(self):
        ledger = SharedLedger()
        ledger.record_success("task-1", "agent-a")
        ledger.record_success("task-2", "agent-a")
        ledger.record_failure("task-3", "agent-b")
        stats = ledger.stats()
        assert stats.succeeded == 2
        assert stats.failed == 1
        assert stats.distinct_tasks == 3
        assert stats.distinct_agents == 2

    def test_reset(self):
        ledger = SharedLedger()
        ledger.record_success("task-1", "agent-a")
        ledger.reset()
        assert ledger.entry_count == 0

    def test_multiple_entries_per_task(self):
        ledger = SharedLedger()
        ledger.claim("task-1", "agent-a")
        ledger.start("task-1", "agent-a")
        ledger.record_success("task-1", "agent-a")
        entries = ledger.query(LedgerQuery(task_id="task-1"))
        assert len(entries) == 3  # claimed, in_progress, succeeded

    def test_claim_after_failure(self):
        """A failed task can be re-claimed."""
        ledger = SharedLedger()
        ledger.record_failure("task-1", "agent-a")
        assert ledger.claim("task-1", "agent-b")


# ---------------------------------------------------------------------------
# IdempotentResult
# ---------------------------------------------------------------------------

class TestIdempotentResult:
    def test_executed(self):
        r = IdempotentResult(
            task_id="t1", was_executed=True,
            status=LedgerEntryStatus.SUCCEEDED, output="done",
        )
        assert r.was_executed
        assert r.output == "done"

    def test_skipped(self):
        r = IdempotentResult(
            task_id="t1", was_executed=False,
            status=LedgerEntryStatus.SUCCEEDED,
        )
        assert not r.was_executed

    def test_frozen(self):
        r = IdempotentResult(task_id="x", was_executed=True, status=LedgerEntryStatus.SUCCEEDED)
        with pytest.raises(Exception):
            r.was_executed = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# IdempotentRunner
# ---------------------------------------------------------------------------

class TestIdempotentRunner:
    def test_run_executes(self):
        runner = IdempotentRunner()
        calls = []

        def task_fn(tid):
            calls.append(tid)
            return f"result-{tid}"

        result = runner.run("task-1", "agent-a", task_fn)
        assert result.was_executed
        assert result.status == LedgerEntryStatus.SUCCEEDED
        assert result.output == "result-task-1"
        assert calls == ["task-1"]

    def test_run_skips_completed_strict(self):
        ledger = SharedLedger()
        runner = IdempotentRunner(ledger=ledger, mode=IdempotencyMode.STRICT)

        def task_fn(tid):
            return f"result-{tid}"

        # First run
        result1 = runner.run("task-1", "agent-a", task_fn)
        assert result1.was_executed

        # Second run — should skip
        calls = []
        def task_fn2(tid):
            calls.append(tid)
            return "should not run"

        result2 = runner.run("task-1", "agent-b", task_fn2)
        assert not result2.was_executed
        assert calls == []

    def test_run_handles_failure(self):
        runner = IdempotentRunner()

        def task_fn(tid):
            raise RuntimeError("boom")

        result = runner.run("task-1", "agent-a", task_fn)
        assert result.was_executed
        assert result.status == LedgerEntryStatus.FAILED
        assert result.error == "boom"

    def test_run_retry_only_mode(self):
        ledger = SharedLedger()
        ledger.record_success("task-1", "agent-a")
        runner = IdempotentRunner(ledger=ledger, mode=IdempotencyMode.RETRY_ONLY)

        calls = []
        def task_fn(tid):
            calls.append(tid)
            return "retried"

        # RETRY_ONLY skips succeeded tasks
        result = runner.run("task-1", "agent-b", task_fn)
        assert not result.was_executed
        assert calls == []


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_swarm_pattern(self):
        """Multiple agents consulting the shared ledger to avoid redundant work."""
        ledger = SharedLedger()

        # Agent A claims and completes task-1
        assert ledger.claim("task-1", "agent-a")
        ledger.start("task-1", "agent-a")
        ledger.record_success("task-1", "agent-a", output="Agent A result")

        # Agent B tries to claim task-1 → denied
        assert not ledger.claim("task-1", "agent-b")

        # Agent B claims task-2 instead
        assert ledger.claim("task-2", "agent-b")

        # Agent C claims task-3
        assert ledger.claim("task-3", "agent-c")

        stats = ledger.stats()
        assert stats.succeeded == 1
        assert stats.claimed == 3  # task-1, task-2, task-3 all claimed

    def test_idempotent_fan_out(self):
        """Fan-out multiple tasks with idempotent runner."""
        runner = IdempotentRunner()
        results = []

        def make_runner(n):
            def fn(tid):
                return f"task-{n}-result"
            return fn

        for i in range(5):
            results.append(runner.run(f"task-{i}", f"agent-{i % 2}", make_runner(i)))

        assert all(r.status == LedgerEntryStatus.SUCCEEDED for r in results)
        assert all(r.was_executed for r in results)

        # Re-run — all should be skipped (strict mode)
        results2 = []
        for i in range(5):
            results2.append(runner.run(f"task-{i}", f"agent-{i % 2}", make_runner(i)))

        assert all(not r.was_executed for r in results2)

        stats = runner.ledger.stats()
        assert stats.succeeded == 5
        assert stats.distinct_tasks == 5
