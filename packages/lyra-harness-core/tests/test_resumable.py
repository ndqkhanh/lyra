"""Tests for resumable.py — Resumable Long Runs (P4-B6 HIGH×MED)."""
from __future__ import annotations

import pytest
from lyra_harness_core.resumable import (
    CheckpointStore,
    CheckpointStrategy,
    ResumeAction,
    ResumePlan,
    ResumePlanner,
    ResumableRun,
    RunCheckpoint,
    RunResult,
    RunStatus,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestRunStatus:
    def test_values(self):
        assert RunStatus.COMPLETED.value == "completed"
        assert RunStatus.FAILED.value == "failed"
        assert RunStatus.PAUSED.value == "paused"

class TestCheckpointStrategy:
    def test_values(self):
        assert CheckpointStrategy.AFTER_EACH_SUBTASK.value == "after_each_subtask"
        assert CheckpointStrategy.MANUAL.value == "manual"

class TestResumeAction:
    def test_values(self):
        assert ResumeAction.SKIP.value == "skip"
        assert ResumeAction.RETRY.value == "retry"
        assert ResumeAction.EXECUTE.value == "execute"


# ---------------------------------------------------------------------------
# RunCheckpoint
# ---------------------------------------------------------------------------

class TestRunCheckpoint:
    def test_creation(self):
        cp = RunCheckpoint(
            checkpoint_id="run-001-task-a",
            subtask_id="task-a",
            timestamp=1000.0,
            status=RunStatus.COMPLETED,
            output="done",
        )
        assert cp.subtask_id == "task-a"
        assert cp.status == RunStatus.COMPLETED
        assert cp.output == "done"

    def test_defaults(self):
        cp = RunCheckpoint(
            checkpoint_id="c1", subtask_id="t1", timestamp=0.0, status=RunStatus.PENDING,
        )
        assert cp.error == ""
        assert cp.metadata == {}

    def test_frozen(self):
        cp = RunCheckpoint(
            checkpoint_id="c1", subtask_id="t1", timestamp=0.0, status=RunStatus.COMPLETED,
        )
        with pytest.raises(Exception):
            cp.status = RunStatus.FAILED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CheckpointStore
# ---------------------------------------------------------------------------

class TestCheckpointStore:
    def test_empty(self):
        store = CheckpointStore()
        assert store.checkpoint_count == 0

    def test_save_and_get(self):
        store = CheckpointStore()
        cp = RunCheckpoint("c1", "t1", 1.0, RunStatus.COMPLETED)
        store.save(cp)
        assert store.checkpoint_count == 1
        assert store.get("t1") is cp

    def test_get_missing(self):
        store = CheckpointStore()
        assert store.get("nonexistent") is None

    def test_get_all(self):
        store = CheckpointStore()
        store.save(RunCheckpoint("c1", "a", 1.0, RunStatus.COMPLETED))
        store.save(RunCheckpoint("c2", "b", 2.0, RunStatus.FAILED))
        assert len(store.get_all()) == 2

    def test_subtask_ids(self):
        store = CheckpointStore()
        store.save(RunCheckpoint("c1", "a", 1.0, RunStatus.COMPLETED))
        store.save(RunCheckpoint("c2", "b", 1.0, RunStatus.COMPLETED))
        assert set(store.subtask_ids()) == {"a", "b"}

    def test_completed_subtask_ids(self):
        store = CheckpointStore()
        store.save(RunCheckpoint("c1", "a", 1.0, RunStatus.COMPLETED))
        store.save(RunCheckpoint("c2", "b", 1.0, RunStatus.FAILED))
        assert store.completed_subtask_ids() == ("a",)

    def test_failed_subtask_ids(self):
        store = CheckpointStore()
        store.save(RunCheckpoint("c1", "a", 1.0, RunStatus.COMPLETED))
        store.save(RunCheckpoint("c2", "b", 1.0, RunStatus.FAILED))
        assert store.failed_subtask_ids() == ("b",)

    def test_overwrite(self):
        store = CheckpointStore()
        cp1 = RunCheckpoint("c1", "a", 1.0, RunStatus.RUNNING)
        cp2 = RunCheckpoint("c1", "a", 2.0, RunStatus.COMPLETED)
        store.save(cp1)
        store.save(cp2)
        assert store.get("a").status == RunStatus.COMPLETED

    def test_clear(self):
        store = CheckpointStore()
        store.save(RunCheckpoint("c1", "a", 1.0, RunStatus.COMPLETED))
        store.clear()
        assert store.checkpoint_count == 0


# ---------------------------------------------------------------------------
# ResumePlan
# ---------------------------------------------------------------------------

class TestResumePlan:
    def test_creation(self):
        plan = ResumePlan(
            skip_ids=("a", "b"),
            retry_ids=("c",),
            execute_ids=("d", "e"),
        )
        assert plan.total_actions == 5
        assert plan.has_work

    def test_no_work(self):
        plan = ResumePlan(skip_ids=("a",), retry_ids=(), execute_ids=())
        assert not plan.has_work


# ---------------------------------------------------------------------------
# ResumePlanner
# ---------------------------------------------------------------------------

class TestResumePlanner:
    def test_all_new(self):
        planner = ResumePlanner()
        store = CheckpointStore()
        plan = planner.plan(("a", "b", "c"), store)
        assert plan.execute_ids == ("a", "b", "c")
        assert plan.skip_ids == ()
        assert plan.retry_ids == ()

    def test_skip_completed(self):
        planner = ResumePlanner()
        store = CheckpointStore()
        store.save(RunCheckpoint("c1", "a", 1.0, RunStatus.COMPLETED))
        plan = planner.plan(("a", "b"), store)
        assert plan.skip_ids == ("a",)
        assert plan.execute_ids == ("b",)

    def test_retry_failed(self):
        planner = ResumePlanner()
        store = CheckpointStore()
        store.save(RunCheckpoint("c1", "a", 1.0, RunStatus.FAILED, error="timeout"))
        plan = planner.plan(("a", "b"), store)
        assert plan.retry_ids == ("a",)
        assert plan.execute_ids == ("b",)

    def test_mixed(self):
        planner = ResumePlanner()
        store = CheckpointStore()
        store.save(RunCheckpoint("c1", "a", 1.0, RunStatus.COMPLETED))
        store.save(RunCheckpoint("c2", "b", 1.0, RunStatus.FAILED))
        plan = planner.plan(("a", "b", "c"), store)
        assert plan.skip_ids == ("a",)
        assert plan.retry_ids == ("b",)
        assert plan.execute_ids == ("c",)


# ---------------------------------------------------------------------------
# RunResult
# ---------------------------------------------------------------------------

class TestRunResult:
    def test_success_rate(self):
        result = RunResult(
            run_id="r1", status=RunStatus.COMPLETED,
            checkpoints=(), total_subtasks=4,
            completed_count=3, failed_count=1, skipped_count=0, duration_ms=100.0,
        )
        assert result.success_rate == 0.75

    def test_success_rate_all_pass(self):
        result = RunResult(
            run_id="r1", status=RunStatus.COMPLETED,
            checkpoints=(), total_subtasks=3,
            completed_count=3, failed_count=0, skipped_count=0, duration_ms=0.0,
        )
        assert result.success_rate == 1.0

    def test_success_rate_no_attempt(self):
        result = RunResult(
            run_id="r1", status=RunStatus.PENDING,
            checkpoints=(), total_subtasks=0,
            completed_count=0, failed_count=0, skipped_count=0, duration_ms=0.0,
        )
        assert result.success_rate == 1.0

    def test_frozen(self):
        result = RunResult(
            run_id="x", status=RunStatus.COMPLETED,
            checkpoints=(), total_subtasks=0, completed_count=0,
            failed_count=0, skipped_count=0, duration_ms=0.0,
        )
        with pytest.raises(Exception):
            result.status = RunStatus.FAILED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ResumableRun
# ---------------------------------------------------------------------------

class TestResumableRun:
    def test_execute_all_success(self):
        run = ResumableRun(run_id="test-run")
        calls = []

        def runner(sid):
            calls.append(sid)
            return f"result-{sid}"

        result = run.execute(("a", "b", "c"), runner)
        assert result.status == RunStatus.COMPLETED
        assert result.completed_count == 3
        assert result.failed_count == 0
        assert calls == ["a", "b", "c"]

    def test_execute_with_failures(self):
        run = ResumableRun(run_id="test-run")

        def runner(sid):
            if sid == "b":
                raise RuntimeError("fail")
            return f"result-{sid}"

        result = run.execute(("a", "b", "c"), runner)
        assert result.status == RunStatus.PAUSED
        assert result.completed_count == 2
        assert result.failed_count == 1

    def test_resume_skips_completed(self):
        run = ResumableRun(run_id="test-run")
        calls = []

        def runner(sid):
            calls.append(sid)
            return f"result-{sid}"

        # First run: complete a, fail b
        def runner1(sid):
            if sid == "b":
                raise RuntimeError("fail")
            return f"result-{sid}"

        run.execute(("a", "b", "c"), runner1)

        # Resume: skip a, retry b, skip c (c was also completed in first run)
        calls.clear()
        result = run.execute(("a", "b", "c"), runner, resume=True)
        assert result.status == RunStatus.COMPLETED
        assert result.skipped_count == 2  # a and c were already completed
        assert result.completed_count == 1  # only b was retried and succeeded
        assert "a" not in calls  # skipped (already completed)
        assert "b" in calls  # retried

    def test_resume_all_already_done(self):
        run = ResumableRun(run_id="test-run")
        calls = []

        def runner(sid):
            calls.append(sid)
            return f"result-{sid}"

        run.execute(("a", "b"), runner)
        calls.clear()

        result = run.execute(("a", "b"), runner, resume=True)
        assert result.status == RunStatus.COMPLETED
        assert result.skipped_count == 2
        assert calls == []  # nothing re-executed

    def test_reset(self):
        run = ResumableRun(run_id="test-run")

        def runner(sid):
            return f"result-{sid}"

        run.execute(("a",), runner)
        assert run.checkpoint_count == 1
        run.reset()
        assert run.checkpoint_count == 0

    def test_checkpoints_preserved(self):
        run = ResumableRun(run_id="test-run")

        def runner(sid):
            return f"result-{sid}"

        result = run.execute(("a", "b"), runner)
        assert len(result.checkpoints) == 2
        assert result.checkpoints[0].output == "result-a"

    def test_retry_failed_succeeds(self):
        run = ResumableRun(run_id="test-run")
        attempts = {"b": 0}

        def runner1(sid):
            if sid == "b":
                raise RuntimeError("fail")
            return f"result-{sid}"

        run.execute(("a", "b"), runner1)

        def runner2(sid):
            attempts["b"] += 1
            return f"result-retry-{sid}"

        result = run.execute(("a", "b"), runner2, resume=True)
        assert result.completed_count == 1  # only b was retried and succeeded
        assert result.skipped_count == 1  # a was skipped
        assert attempts["b"] == 1


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_checkpoint_resume_cycle(self):
        """Simulate a long run that fails midway and resumes."""
        run = ResumableRun(run_id="deep-research-001")

        tasks = ("lit-review", "code-audit", "arch-review", "merge-report")

        # First attempt: code-audit fails
        def first_attempt(sid):
            if sid == "code-audit":
                raise RuntimeError("API rate limit")
            return f"[{sid}] analysis complete"

        result1 = run.execute(tasks, first_attempt)
        assert result1.status == RunStatus.PAUSED
        assert result1.completed_count == 3  # lit-review, arch-review, merge-report succeeded
        assert result1.failed_count == 1  # code-audit failed

        # Resume: code-audit should be retried, others skipped
        retried = []

        def second_attempt(sid):
            retried.append(sid)
            return f"[{sid}] retry complete"

        result2 = run.execute(tasks, second_attempt, resume=True)
        assert result2.status == RunStatus.COMPLETED
        assert result2.skipped_count == 3
        assert retried == ["code-audit"]
        assert result2.success_rate == 1.0

    def test_multiple_failures_eventual_success(self):
        run = ResumableRun(run_id="flaky-run")
        attempts = {"flaky-task": 0}

        def flaky_runner(sid):
            attempts["flaky-task"] += 1
            if attempts["flaky-task"] < 3:
                raise RuntimeError(f"attempt {attempts['flaky-task']} failed")
            return "finally works"

        result1 = run.execute(("flaky-task",), flaky_runner)
        assert result1.failed_count == 1
        assert attempts["flaky-task"] == 1

        result2 = run.execute(("flaky-task",), flaky_runner, resume=True)
        assert result2.failed_count == 1
        assert attempts["flaky-task"] == 2

        result3 = run.execute(("flaky-task",), flaky_runner, resume=True)
        assert result3.completed_count == 1
        assert attempts["flaky-task"] == 3
