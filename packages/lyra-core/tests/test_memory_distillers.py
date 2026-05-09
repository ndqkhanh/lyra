"""Tests for the v1.8 §3.2 default distillers (Heuristic + LLM scaffold)."""
from __future__ import annotations

from lyra_core.memory import (
    HeuristicDistiller,
    LLMDistiller,
    Trajectory,
    TrajectoryOutcome,
    TrajectoryStep,
)


def _trajectory(
    *,
    outcome: TrajectoryOutcome,
    sig: str = "parse-json",
    steps: tuple[TrajectoryStep, ...] | None = None,
    final_artefact: str = "diff: ...",
) -> Trajectory:
    if steps is None:
        steps = (
            TrajectoryStep(index=0, kind="message", payload="user asked for parser"),
            TrajectoryStep(index=1, kind="tool_call", payload="view src/parser.py"),
            TrajectoryStep(
                index=2,
                kind="tool_call",
                payload="bash pytest tests/test_parser.py",
            ),
        )
    return Trajectory(
        id=f"t-{outcome.value}-{sig}",
        task_signature=sig,
        outcome=outcome,
        steps=steps,
        final_artefact=final_artefact,
    )


# ---------------------------------------------------------------------------
# HeuristicDistiller — success path
# ---------------------------------------------------------------------------


def test_heuristic_success_yields_strategy_lesson() -> None:
    d = HeuristicDistiller()
    lessons = d.distill(_trajectory(outcome=TrajectoryOutcome.SUCCESS))
    assert len(lessons) == 1
    lesson = lessons[0]
    assert lesson.polarity is TrajectoryOutcome.SUCCESS
    assert lesson.title.startswith("Strategy:")
    assert "parse-json" in lesson.task_signatures
    assert "Sequence that worked" in lesson.body


def test_heuristic_failure_yields_anti_skill() -> None:
    """The §3.2 contract: every failure trajectory yields ≥1 anti-skill."""
    d = HeuristicDistiller()
    failure = _trajectory(
        outcome=TrajectoryOutcome.FAILURE,
        steps=(
            TrajectoryStep(index=0, kind="tool_call", payload="bash pytest -k parser"),
            TrajectoryStep(
                index=1,
                kind="message",
                payload="error: ImportError no module named parser_v2",
            ),
        ),
    )
    lessons = d.distill(failure)
    assert len(lessons) >= 1
    assert lessons[0].polarity is TrajectoryOutcome.FAILURE
    assert lessons[0].title.startswith("Anti-skill:")
    assert "ImportError" in lessons[0].body or "Symptom" in lessons[0].body


def test_heuristic_failure_with_recovery_emits_two_lessons() -> None:
    """Failures that mention a recovery hint yield a second positive lesson."""
    d = HeuristicDistiller()
    failure = _trajectory(
        outcome=TrajectoryOutcome.FAILURE,
        steps=(
            TrajectoryStep(index=0, kind="tool_call", payload="bash pytest -k parser"),
            TrajectoryStep(
                index=1,
                kind="message",
                payload="error: ImportError; retry with the parser_v3 fallback",
            ),
        ),
    )
    lessons = d.distill(failure)
    assert len(lessons) == 2
    assert lessons[0].polarity is TrajectoryOutcome.FAILURE
    assert lessons[1].polarity is TrajectoryOutcome.SUCCESS
    assert "Recovery hint" in lessons[1].title


def test_heuristic_empty_failure_still_emits_lesson() -> None:
    d = HeuristicDistiller()
    empty = Trajectory(
        id="t-empty",
        task_signature="empty-task",
        outcome=TrajectoryOutcome.FAILURE,
        steps=(),
    )
    lessons = d.distill(empty)
    assert len(lessons) == 1
    assert lessons[0].polarity is TrajectoryOutcome.FAILURE


def test_heuristic_empty_success_yields_no_lesson() -> None:
    """An empty success trajectory carries no signal — bank stays clean."""
    d = HeuristicDistiller()
    empty = Trajectory(
        id="t-empty-success",
        task_signature="empty-task",
        outcome=TrajectoryOutcome.SUCCESS,
        steps=(),
    )
    assert d.distill(empty) == ()


def test_heuristic_is_deterministic_for_same_input() -> None:
    """Same trajectory in → same lesson IDs out (snapshotting contract)."""
    d = HeuristicDistiller()
    t = _trajectory(outcome=TrajectoryOutcome.SUCCESS)
    lessons_a = d.distill(t)
    lessons_b = d.distill(t)
    assert tuple(lesson.id for lesson in lessons_a) == tuple(
        lesson.id for lesson in lessons_b
    )


# ---------------------------------------------------------------------------
# LLMDistiller — wraps a callable, falls back gracefully
# ---------------------------------------------------------------------------


def test_llm_distiller_normal_path() -> None:
    def fake_llm(_prompt: str) -> list[dict[str, str]]:
        return [
            {"polarity": "success", "title": "Use FTS5", "body": "It's faster."},
            {"polarity": "failure", "title": "Skip Chroma", "body": "Cold-start is slow."},
        ]

    d = LLMDistiller(llm=fake_llm)
    lessons = d.distill(_trajectory(outcome=TrajectoryOutcome.SUCCESS))
    assert len(lessons) == 2
    assert lessons[0].polarity is TrajectoryOutcome.SUCCESS
    assert lessons[1].polarity is TrajectoryOutcome.FAILURE
    assert lessons[0].title == "Use FTS5"


def test_llm_distiller_falls_back_on_exception() -> None:
    """If the callable raises, fall back to the heuristic distiller."""

    def angry_llm(_prompt: str) -> list[dict[str, str]]:
        raise RuntimeError("LLM down")

    d = LLMDistiller(llm=angry_llm)
    lessons = d.distill(_trajectory(outcome=TrajectoryOutcome.SUCCESS))
    assert len(lessons) >= 1
    assert lessons[0].polarity is TrajectoryOutcome.SUCCESS


def test_llm_distiller_falls_back_on_empty_payload() -> None:
    def silent_llm(_prompt: str) -> list[dict[str, str]]:
        return []

    d = LLMDistiller(llm=silent_llm)
    lessons = d.distill(_trajectory(outcome=TrajectoryOutcome.FAILURE))
    assert len(lessons) >= 1
    assert lessons[0].polarity is TrajectoryOutcome.FAILURE
