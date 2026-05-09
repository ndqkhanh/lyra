"""RED tests for v1.8 Wave-1 §3.2 — ReasoningBank with failure-distillation + MaTTS."""
from __future__ import annotations

from lyra_core.memory import (
    Distiller,
    Lesson,
    ReasoningBank,
    Trajectory,
    TrajectoryOutcome,
    TrajectoryStep,
)


def _trajectory(*, outcome: TrajectoryOutcome, sig: str = "parse-json", n_steps: int = 3) -> Trajectory:
    return Trajectory(
        id=f"t-{outcome.value}-{sig}",
        task_signature=sig,
        outcome=outcome,
        steps=tuple(
            TrajectoryStep(index=i, kind="message", payload=f"step-{i}") for i in range(n_steps)
        ),
        final_artefact="diff: ...",
    )


class _StubDistiller(Distiller):
    """Returns one Lesson per trajectory with the same polarity."""

    def distill(self, trajectory: Trajectory) -> tuple[Lesson, ...]:
        return (
            Lesson(
                id=f"l-{trajectory.id}",
                polarity=trajectory.outcome,
                title=f"Lesson from {trajectory.id}",
                body="distilled body",
                task_signatures=(trajectory.task_signature,),
                source_trajectory_ids=(trajectory.id,),
            ),
        )


def test_trajectory_outcome_is_a_two_value_enum() -> None:
    """The bank only has two valid polarities — anything else is a bug."""
    assert {e.value for e in TrajectoryOutcome} == {"success", "failure"}


def test_lesson_carries_back_pointer_to_source_trajectory() -> None:
    """Audit trail: every lesson must cite the trajectory it came from."""
    t = _trajectory(outcome=TrajectoryOutcome.FAILURE)
    lesson = _StubDistiller().distill(t)[0]
    assert t.id in lesson.source_trajectory_ids


def test_record_returns_at_least_one_lesson_for_a_failure() -> None:
    """Failure-distillation contract: an obvious failure produces an anti-skill."""
    bank = ReasoningBank(distiller=_StubDistiller())
    lessons = bank.record(_trajectory(outcome=TrajectoryOutcome.FAILURE))
    assert len(lessons) >= 1
    assert any(lesson.polarity is TrajectoryOutcome.FAILURE for lesson in lessons)


def test_recall_filters_by_polarity() -> None:
    bank = ReasoningBank(distiller=_StubDistiller())
    bank.record(_trajectory(outcome=TrajectoryOutcome.SUCCESS, sig="parse-json"))
    bank.record(_trajectory(outcome=TrajectoryOutcome.FAILURE, sig="parse-json"))
    only_failures = bank.recall("parse-json", polarity=TrajectoryOutcome.FAILURE)
    assert all(lesson.polarity is TrajectoryOutcome.FAILURE for lesson in only_failures)


def test_recall_respects_topk_cap() -> None:
    bank = ReasoningBank(distiller=_StubDistiller())
    for i in range(10):
        bank.record(_trajectory(outcome=TrajectoryOutcome.SUCCESS, sig=f"task-{i}"))
    out = bank.recall("task-0", k=3)
    assert len(out) <= 3


def test_matts_prefix_diversifies_per_attempt() -> None:
    """MaTTS contract: different attempt_index values yield different prefixes."""
    bank = ReasoningBank(distiller=_StubDistiller())
    for i in range(5):
        bank.record(_trajectory(outcome=TrajectoryOutcome.SUCCESS, sig=f"task-{i}"))
    p0 = bank.matts_prefix("task-0", attempt_index=0)
    p1 = bank.matts_prefix("task-0", attempt_index=1)
    p2 = bank.matts_prefix("task-0", attempt_index=2)
    assert len({p0, p1, p2}) >= 2
