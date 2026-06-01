"""Tests for session continuation and context restoration."""

from __future__ import annotations

import pytest

from lyra_cli.autonomy.context_restorer import (
    ContextFragment,
    ContextRestorer,
    RestoreStatus,
)
from lyra_cli.autonomy.continuation.state_reconstructor import (
    ReconstructionPhase,
    StateReconstructor,
)


# ── Sample Data ────────────────────────────────────────────────────

def make_checkpoint_data(**overrides):
    data = {
        "session_id": "sess-001",
        "state": "EXECUTING",
        "goals": [
            {"goal_id": "g1", "name": "Add login", "status": "in_progress"},
            {"goal_id": "g2", "name": "Add tests", "status": "pending"},
        ],
        "tasks": [
            {"task_id": "t1", "goal_id": "g1", "description": "Create login form", "status": "completed"},
            {"task_id": "t2", "goal_id": "g1", "description": "Add OAuth", "status": "running"},
            {"task_id": "t3", "goal_id": "g1", "description": "Write tests", "status": "pending"},
            {"task_id": "t4", "goal_id": "g2", "description": "Integration test", "status": "failed"},
        ],
        "errors": ["OAuth token expired", "Network timeout"],
        "working_memory": {"current_file": "auth.py", "context": "auth implementation"},
        "budget": {"tokens_used": 5000, "level": "green"},
        "created_at": "2026-05-30T10:00:00",
        "version": "2.0",
    }
    data.update(overrides)
    return data


# ── ContextRestorer Tests ──────────────────────────────────────────


class TestContextRestorer:
    """Tests for ContextRestorer."""

    def test_restore_full_context(self):
        restorer = ContextRestorer()
        data = make_checkpoint_data()
        ctx = restorer.restore("sess-001", data)
        assert ctx.status == RestoreStatus.FULL
        assert ctx.fidelity_pct >= 95.0
        assert ctx.session_id == "sess-001"

    def test_restore_goals(self):
        restorer = ContextRestorer()
        data = make_checkpoint_data()
        ctx = restorer.restore("sess-002", data)
        assert len(ctx.goals) == 2
        assert ctx.goals[0]["goal_id"] == "g1"

    def test_restore_active_tasks(self):
        restorer = ContextRestorer()
        data = make_checkpoint_data()
        ctx = restorer.restore("sess-003", data)
        assert len(ctx.active_tasks) == 2  # t2 running, t3 pending

    def test_restore_completed_tasks(self):
        restorer = ContextRestorer()
        data = make_checkpoint_data()
        ctx = restorer.restore("sess-004", data)
        assert len(ctx.completed_tasks) == 1

    def test_restore_failed_tasks(self):
        restorer = ContextRestorer()
        data = make_checkpoint_data()
        ctx = restorer.restore("sess-005", data)
        assert len(ctx.failed_tasks) == 1

    def test_restore_errors(self):
        restorer = ContextRestorer()
        data = make_checkpoint_data()
        ctx = restorer.restore("sess-006", data)
        assert len(ctx.errors) == 2
        assert "OAuth token expired" in ctx.errors

    def test_restore_working_memory(self):
        restorer = ContextRestorer()
        data = make_checkpoint_data()
        ctx = restorer.restore("sess-007", data)
        assert ctx.working_memory["current_file"] == "auth.py"

    def test_restore_budget_state(self):
        restorer = ContextRestorer()
        data = make_checkpoint_data()
        ctx = restorer.restore("sess-008", data)
        assert ctx.budget_state["tokens_used"] == 5000
        assert ctx.budget_state["level"] == "green"

    def test_restore_empty_checkpoint_partial(self):
        restorer = ContextRestorer()
        ctx = restorer.restore("sess-empty", {"session_id": "sess-empty"})
        assert ctx.status == RestoreStatus.DEGRADED

    def test_restore_tasks_from_active_tasks_key(self):
        restorer = ContextRestorer()
        data = {
            "session_id": "alt-key",
            "state": "RUNNING",
            "active_tasks": [{"task_id": "a1", "status": "running"}],
        }
        ctx = restorer.restore("alt-key", data)
        assert len(ctx.active_tasks) == 1

    def test_store_and_use_fragment(self):
        restorer = ContextRestorer()
        fragment = ContextFragment(
            fragment_id="f1",
            category="memory",
            data={"key": "value"},
            priority=1,
        )
        restorer.store_fragment(fragment)
        assert len(restorer._fragments) == 1

    def test_diff_contexts_detects_added_tasks(self):
        restorer = ContextRestorer()
        data = make_checkpoint_data()
        prev = restorer.restore("diff-test", data)
        current = {
            "tasks": [
                {"task_id": "t1", "status": "completed"},
                {"task_id": "t2", "status": "running"},
                {"task_id": "t3", "status": "pending"},
                {"task_id": "t5", "status": "pending"},  # new
            ],
            "goals": [{"goal_id": "g1"}, {"goal_id": "g3"}],
        }
        diff = restorer.diff_contexts(prev, current)
        assert "t5" in diff["tasks"]["added"]

    def test_get_restore_summary(self):
        restorer = ContextRestorer()
        data = make_checkpoint_data()
        ctx = restorer.restore("summary-test", data)
        summary = restorer.get_restore_summary(ctx)
        assert "summary-test" in summary
        assert "Active tasks" in summary
        assert "Completed" in summary

    def test_clear_removes_fragments(self):
        restorer = ContextRestorer()
        restorer.store_fragment(
            ContextFragment(fragment_id="f1", category="task", data={}, priority=1)
        )
        restorer.clear()
        assert len(restorer._fragments) == 0


# ── StateReconstructor Tests ───────────────────────────────────────


class TestStateReconstructor:
    """Tests for StateReconstructor."""

    def test_reconstruct_full_state(self):
        reconstructor = StateReconstructor()
        data = make_checkpoint_data()
        state = reconstructor.reconstruct("sess-001", data)
        assert state.session_id == "sess-001"
        assert state.state == "EXECUTING"
        assert state.is_valid is True

    def test_reconstruct_counts_tasks(self):
        reconstructor = StateReconstructor()
        data = make_checkpoint_data()
        state = reconstructor.reconstruct("sess-002", data)
        assert state.completed_task_count == 1
        assert state.failed_task_count == 1
        assert len(state.active_tasks) == 2

    def test_reconstruct_empty_data(self):
        reconstructor = StateReconstructor()
        state = reconstructor.reconstruct("empty", {"session_id": "empty"})
        assert state.state == "IDLE"
        assert state.completed_task_count == 0

    def test_reconstruct_with_strict_validation_fails(self):
        reconstructor = StateReconstructor(strict_validation=True)
        state = reconstructor.reconstruct("bad", {"not": "valid"})
        assert state.is_valid is False
        assert state.state == "UNKNOWN"

    def test_reconstruct_without_strict_validation_continues(self):
        reconstructor = StateReconstructor(strict_validation=False)
        state = reconstructor.reconstruct("partial", {"not": "valid"})
        # Lenient mode tries to extract what it can
        assert state.state == "IDLE"

    def test_reconstruct_calculates_checkpoint_age(self):
        reconstructor = StateReconstructor()
        data = make_checkpoint_data()
        state = reconstructor.reconstruct("age-test", data)
        assert state.checkpoint_age_seconds >= 0.0

    def test_reconstruct_with_report(self):
        reconstructor = StateReconstructor()
        data = make_checkpoint_data()
        report = reconstructor.reconstruct_with_report("rpt-001", data)
        assert report.success is True
        assert report.state is not None
        assert ReconstructionPhase.REBUILD in report.phases_completed

    def test_reconstruct_with_report_failures(self):
        reconstructor = StateReconstructor(strict_validation=True)
        report = reconstructor.reconstruct_with_report("bad-rpt", {"broken": True})
        assert report.success is False

    def test_validate_checkpoint_with_tasks_list(self):
        reconstructor = StateReconstructor()
        is_valid, warnings = reconstructor._validate_checkpoint(
            {"session_id": "v1", "tasks": [{"task_id": "t1"}]}
        )
        assert is_valid is True

    def test_validate_checkpoint_with_bad_task(self):
        reconstructor = StateReconstructor()
        is_valid, warnings = reconstructor._validate_checkpoint(
            {"session_id": "v2", "tasks": ["not_a_dict"]}
        )
        assert any("not a valid dict" in w for w in warnings)

    def test_get_history(self):
        reconstructor = StateReconstructor()
        data = make_checkpoint_data()
        reconstructor.reconstruct_with_report("h1", data)
        reconstructor.reconstruct_with_report("h2", data)
        history = reconstructor.get_history()
        assert len(history) == 2

    def test_get_success_rate(self):
        reconstructor = StateReconstructor()
        data = make_checkpoint_data()
        reconstructor.reconstruct_with_report("s1", data)
        rate = reconstructor.get_success_rate()
        assert rate == 1.0

        reconstructor2 = StateReconstructor(strict_validation=True)
        reconstructor2.reconstruct_with_report("s2", {"bad": True})
        rate2 = reconstructor2.get_success_rate()
        assert rate2 == 0.0

    def test_clear_history(self):
        reconstructor = StateReconstructor()
        reconstructor.reconstruct_with_report("c1", make_checkpoint_data())
        reconstructor.clear()
        assert reconstructor.get_success_rate() == 0.0
