"""Tests for the CostTracker."""

from __future__ import annotations

import pytest

from lyra_cost import CallOutcome, CostTracker, ModelTier, SessionBudget, TaskCostSummary


class TestCostTracker:
    """Suite of tests for CostTracker."""

    def test_initial_state(self) -> None:
        tracker = CostTracker("test-session")
        assert tracker.session_id == "test-session"
        assert tracker.total_spent == 0.0
        assert tracker.total_calls == 0
        assert tracker.successful_tasks == 0
        assert tracker.failed_tasks == 0
        assert tracker.cost_per_successful_task == 0.0
        assert tracker.cost_per_call == 0.0
        assert not tracker.budget.circuit_breaker_triggered

    def test_record_call_and_total_cost(self) -> None:
        tracker = CostTracker("session-1")
        record = tracker.record_call(
            model="haiku",
            input_tokens=1000,
            output_tokens=500,
            task_id="task-1",
        )

        assert record.model_name == "haiku"
        assert record.model_tier == ModelTier.TIER_1
        assert record.input_tokens == 1000
        assert record.output_tokens == 500
        assert record.total_cost > 0
        assert record.outcome == CallOutcome.SUCCESS
        assert record.task_id == "task-1"
        assert tracker.total_spent == record.total_cost
        assert tracker.total_calls == 1

    def test_record_several_calls(self) -> None:
        tracker = CostTracker("session-2")
        for _ in range(5):
            tracker.record_call(model="haiku", input_tokens=100, output_tokens=50)

        assert tracker.total_calls == 5
        assert tracker.total_spent > 0
        assert 0 < tracker.cost_per_call < 0.01

    def test_cost_per_successful_task(self) -> None:
        tracker = CostTracker("session-3")
        tracker.record_call(model="haiku", input_tokens=1000, output_tokens=500)
        spent = tracker.total_spent

        # No successes yet
        assert tracker.cost_per_successful_task == 0.0

        tracker.record_success("task-1")
        assert tracker.cost_per_successful_task == pytest.approx(spent)

        # Add a second task with more spend
        tracker.record_call(model="sonnet", input_tokens=2000, output_tokens=1000, task_id="task-2")
        spent2 = tracker.total_spent
        tracker.record_success("task-2")
        assert tracker.cost_per_successful_task == pytest.approx(spent2 / 2.0)
        assert tracker.successful_tasks == 2

    def test_task_failure_tracking(self) -> None:
        tracker = CostTracker("session-4")
        tracker.record_call(model="haiku", input_tokens=100, output_tokens=50, task_id="task-1")
        tracker.record_failure("task-1")
        assert tracker.failed_tasks == 1
        assert tracker.successful_tasks == 0

        tracker.record_success("task-1")
        assert tracker.failed_tasks == 0
        assert tracker.successful_tasks == 1

    def test_task_summary(self) -> None:
        tracker = CostTracker("session-5")
        tracker.record_call(model="haiku", input_tokens=1000, output_tokens=500, task_id="task-1")
        tracker.record_success("task-1")

        summary = tracker.task_summary("task-1")
        assert summary is not None
        assert isinstance(summary, TaskCostSummary)
        assert summary.task_id == "task-1"
        assert summary.total_calls == 1
        assert summary.successful_calls == 1
        assert summary.total_cost > 0
        assert summary.cached_cost_savings == 0

    def test_task_summary_missing(self) -> None:
        tracker = CostTracker("session-6")
        assert tracker.task_summary("nonexistent") is None

    def test_session_summary(self) -> None:
        tracker = CostTracker("session-7")
        tracker.record_call(model="haiku", input_tokens=1000, output_tokens=500)
        tracker.record_success("task-1")

        summary = tracker.session_summary
        assert summary["session_id"] == "session-7"
        assert summary["total_calls"] == 1
        assert summary["successful_tasks"] == 1
        assert summary["circuit_breaker_triggered"] is False
        assert "session_duration_seconds" in summary

    def test_budget_property(self) -> None:
        tracker = CostTracker("session-8")
        tracker.record_call(model="haiku", input_tokens=1000, output_tokens=500)
        budget = tracker.budget
        assert isinstance(budget, SessionBudget)
        assert budget.session_id == "session-8"
        assert budget.total_spent == tracker.total_spent
        assert budget.total_calls == 1

    def test_circuit_breaker_blocks(self) -> None:
        tracker = CostTracker("session-9", circuit_breaker_limit=0.001)
        # First call triggers breaker
        tracker.record_call(model="sonnet", input_tokens=100000, output_tokens=50000)
        assert tracker.budget.circuit_breaker_triggered
        with pytest.raises(RuntimeError, match="Circuit breaker is active"):
            tracker.record_call(model="haiku", input_tokens=100, output_tokens=50)

    def test_cached_outcomes_in_task_summary(self) -> None:
        tracker = CostTracker("session-10")
        tracker.record_call(
            model="haiku", input_tokens=1000, output_tokens=500,
            task_id="task-1", outcome=CallOutcome.CACHED_PROMPT,
        )
        tracker.record_success("task-1")
        summary = tracker.task_summary("task-1")
        assert summary is not None
        assert summary.cached_cost_savings > 0

    def test_tier_resolution(self) -> None:
        tracker = CostTracker("session-11")
        # Various model names should map to correct tiers
        r0 = tracker.record_call(model="local-model", input_tokens=100, output_tokens=50)
        assert r0.model_tier == ModelTier.TIER_0  # "local" keyword matches TIER_0

        r1 = tracker.record_call(model="haiku", input_tokens=100, output_tokens=50)
        assert r1.model_tier == ModelTier.TIER_1

        r2 = tracker.record_call(model="opus", input_tokens=100, output_tokens=50)
        assert r2.model_tier == ModelTier.TIER_3

        r3 = tracker.record_call(model="deepseek-v4-pro", input_tokens=100, output_tokens=50)
        assert r3.model_tier == ModelTier.TIER_3

    def test_records_are_immutable(self) -> None:
        tracker = CostTracker("session-12")
        record = tracker.record_call(model="haiku", input_tokens=100, output_tokens=50)
        assert tracker.records == (record,)
