"""Smoke tests for the eval runner and its three corpora."""
from __future__ import annotations

from lyra_evals.corpora import (
    golden_tasks,
    long_horizon_tasks,
    red_team_tasks,
)
from lyra_evals.runner import EvalRunner, TaskResult


def test_corpora_present() -> None:
    assert len(golden_tasks()) >= 3
    assert len(red_team_tasks()) >= 2
    assert len(long_horizon_tasks()) >= 1


def test_runner_smoke_pass_policy() -> None:
    """A runner with the always-pass policy must pass all golden tasks."""
    def policy(task) -> TaskResult:
        return TaskResult(task_id=task.id, passed=True, reason="ok")

    runner = EvalRunner(policy=policy)
    report = runner.run(golden_tasks())
    assert report.total >= 3
    assert report.passed == report.total
    assert report.success_rate == 1.0


def test_runner_smoke_red_team_detection() -> None:
    """A red-team policy marked as 'caught' drives recall."""
    def policy(task) -> TaskResult:
        return TaskResult(
            task_id=task.id,
            passed=True,  # the agent caught the sabotage
            reason="flagged",
        )
    report = EvalRunner(policy=policy).run(red_team_tasks())
    assert report.success_rate == 1.0


def test_runner_drift_gate() -> None:
    """Success < gate threshold flips the drift gate."""
    def policy(task) -> TaskResult:
        return TaskResult(task_id=task.id, passed=False, reason="sabotaged")

    runner = EvalRunner(policy=policy, drift_gate=0.5)
    report = runner.run(golden_tasks())
    assert report.drift_gate_tripped is True


def test_runner_report_fields() -> None:
    def policy(task) -> TaskResult:
        return TaskResult(task_id=task.id, passed=True)

    report = EvalRunner(policy=policy).run(long_horizon_tasks())
    assert report.total == len(long_horizon_tasks())
    assert 0.0 <= report.success_rate <= 1.0
    assert report.to_dict()["total"] == report.total
