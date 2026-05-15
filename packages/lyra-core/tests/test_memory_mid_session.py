"""Tests for mid-session lesson extraction (Phase CE.2, P1-3)."""
from __future__ import annotations

import pytest

from lyra_core.memory.mid_session import (
    AUTO_PROMOTE,
    REJECT_FLOOR,
    ExtractionResult,
    MidSessionExtractor,
    ScoredLesson,
    default_confidence,
    render_pending_table,
)
from lyra_core.memory.reasoning_bank import (
    Lesson,
    ReasoningBank,
    Trajectory,
    TrajectoryOutcome,
    TrajectoryStep,
)


def _lesson(
    lid: str,
    *,
    polarity: TrajectoryOutcome = TrajectoryOutcome.SUCCESS,
    title: str = "A long title with many words for testing",
    body: str = "x" * 80,
    sigs: tuple[str, ...] = ("sig-a",),
) -> Lesson:
    return Lesson(
        id=lid,
        polarity=polarity,
        title=title,
        body=body,
        task_signatures=sigs,
        source_trajectory_ids=("t-1",),
    )


def _trajectory(
    steps: int = 3,
    *,
    outcome: TrajectoryOutcome = TrajectoryOutcome.SUCCESS,
) -> Trajectory:
    return Trajectory(
        id="t-1",
        task_signature="sig-a",
        outcome=outcome,
        steps=tuple(
            TrajectoryStep(index=i, kind="tool_call", payload=f"step-{i}")
            for i in range(steps)
        ),
    )


class _FixedDistiller:
    """Distiller that always emits the same lessons regardless of trajectory."""

    def __init__(self, lessons: list[Lesson]) -> None:
        self.lessons = lessons

    def distill(self, trajectory: Trajectory) -> list[Lesson]:
        del trajectory
        return list(self.lessons)


# ────────────────────────────────────────────────────────────────
# ScoredLesson
# ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad", [-0.01, 1.01])
def test_scored_lesson_rejects_out_of_range_confidence(bad: float):
    with pytest.raises(ValueError):
        ScoredLesson(lesson=_lesson("l-1"), confidence=bad)


# ────────────────────────────────────────────────────────────────
# default_confidence
# ────────────────────────────────────────────────────────────────


def test_default_confidence_higher_for_success_multistep():
    lesson = _lesson("l-1")
    c = default_confidence(lesson, _trajectory(steps=5))
    assert c >= 0.8


def test_default_confidence_lower_for_failure_single_step():
    lesson = _lesson(
        "l-1",
        polarity=TrajectoryOutcome.FAILURE,
        title="short",
        body="short body",
    )
    c = default_confidence(
        lesson, _trajectory(steps=1, outcome=TrajectoryOutcome.FAILURE)
    )
    assert c < AUTO_PROMOTE


def test_default_confidence_clamps_to_one():
    lesson = _lesson(
        "l-1",
        title="A long title with many words for testing things",
        body="x" * 200,
        sigs=("sig-a", "sig-b"),
    )
    c = default_confidence(lesson, _trajectory(steps=10))
    assert c <= 1.0


# ────────────────────────────────────────────────────────────────
# MidSessionExtractor — construction
# ────────────────────────────────────────────────────────────────


def test_extractor_rejects_non_positive_turn_interval():
    bank = ReasoningBank(distiller=_FixedDistiller([]))
    with pytest.raises(ValueError):
        MidSessionExtractor(bank, turn_interval=0)


def test_extractor_rejects_inverted_thresholds():
    bank = ReasoningBank(distiller=_FixedDistiller([]))
    with pytest.raises(ValueError):
        MidSessionExtractor(bank, auto_promote=0.3, reject_floor=0.5)


# ────────────────────────────────────────────────────────────────
# tick()
# ────────────────────────────────────────────────────────────────


def test_tick_fires_every_interval_turns():
    bank = ReasoningBank(distiller=_FixedDistiller([]))
    ext = MidSessionExtractor(bank, turn_interval=3)
    assert ext.tick() is False  # 1
    assert ext.tick() is False  # 2
    assert ext.tick() is True   # 3 → fire
    ext.reset_counter()
    assert ext.tick() is False
    assert ext.tick() is False
    assert ext.tick() is True


# ────────────────────────────────────────────────────────────────
# Bucketing
# ────────────────────────────────────────────────────────────────


def test_high_confidence_goes_straight_to_bank():
    rich = _lesson("rich")
    distiller = _FixedDistiller([rich])
    bank = ReasoningBank(distiller=distiller)
    ext = MidSessionExtractor(bank, distiller=distiller)
    result = ext.extract(_trajectory(steps=5))
    assert len(result.promoted) == 1
    assert result.pending == ()
    # The bank now contains the promoted lesson.
    recalled = bank.recall("sig-a")
    assert any(l.id == "rich" for l in recalled)


def test_medium_confidence_lands_in_pending():
    middling = _lesson(
        "mid",
        polarity=TrajectoryOutcome.FAILURE,
        title="ok title",
        body="x" * 60,
    )
    distiller = _FixedDistiller([middling])
    bank = ReasoningBank(distiller=distiller)
    ext = MidSessionExtractor(bank, distiller=distiller)
    result = ext.extract(_trajectory(steps=2, outcome=TrajectoryOutcome.FAILURE))
    assert result.promoted == ()
    assert len(result.pending) == 1
    assert ext.pending()[0].lesson.id == "mid"
    # Bank still empty.
    assert bank.recall("sig-a") == ()


def test_low_confidence_dropped():
    poor = _lesson(
        "poor",
        polarity=TrajectoryOutcome.FAILURE,
        title="tiny",
        body="short",
        sigs=(),
    )
    distiller = _FixedDistiller([poor])
    bank = ReasoningBank(distiller=distiller)
    # Force a very low confidence by pinning to a noisy heuristic.
    ext = MidSessionExtractor(
        bank,
        distiller=distiller,
        confidence_fn=lambda _l, _t: 0.1,
    )
    result = ext.extract(_trajectory(steps=1, outcome=TrajectoryOutcome.FAILURE))
    assert result.promoted == ()
    assert result.pending == ()
    assert len(result.dropped) == 1


def test_caller_supplied_confidence_fn_drives_bucket():
    lesson = _lesson("custom")
    distiller = _FixedDistiller([lesson])
    bank = ReasoningBank(distiller=distiller)
    ext = MidSessionExtractor(
        bank, distiller=distiller, confidence_fn=lambda _l, _t: 0.5
    )
    result = ext.extract(_trajectory())
    assert result.promoted == ()
    assert len(result.pending) == 1


def test_thresholds_are_inclusive_on_the_boundary():
    """confidence == auto_promote should promote, not go pending."""
    distiller = _FixedDistiller([_lesson("boundary")])
    bank = ReasoningBank(distiller=distiller)
    ext = MidSessionExtractor(
        bank,
        distiller=distiller,
        confidence_fn=lambda _l, _t: AUTO_PROMOTE,
    )
    result = ext.extract(_trajectory())
    assert len(result.promoted) == 1


def test_thresholds_inclusive_at_reject_floor():
    distiller = _FixedDistiller([_lesson("just-pending")])
    bank = ReasoningBank(distiller=distiller)
    ext = MidSessionExtractor(
        bank,
        distiller=distiller,
        confidence_fn=lambda _l, _t: REJECT_FLOOR,
    )
    result = ext.extract(_trajectory())
    assert len(result.pending) == 1
    assert result.dropped == ()


# ────────────────────────────────────────────────────────────────
# Pending queue ops
# ────────────────────────────────────────────────────────────────


def test_promote_pending_moves_to_bank():
    distiller = _FixedDistiller([_lesson("p1")])
    bank = ReasoningBank(distiller=distiller)
    ext = MidSessionExtractor(
        bank, distiller=distiller, confidence_fn=lambda _l, _t: 0.5
    )
    ext.extract(_trajectory())
    out = ext.promote("p1")
    assert out is not None
    assert out.lesson.id == "p1"
    assert ext.pending() == ()
    assert any(l.id == "p1" for l in bank.recall("sig-a"))


def test_promote_unknown_id_returns_none():
    bank = ReasoningBank(distiller=_FixedDistiller([]))
    ext = MidSessionExtractor(bank)
    assert ext.promote("nope") is None


def test_reject_pending_drops_without_persisting():
    distiller = _FixedDistiller([_lesson("r1")])
    bank = ReasoningBank(distiller=distiller)
    ext = MidSessionExtractor(
        bank, distiller=distiller, confidence_fn=lambda _l, _t: 0.5
    )
    ext.extract(_trajectory())
    out = ext.reject("r1")
    assert out is not None
    assert ext.pending() == ()
    assert bank.recall("sig-a") == ()


def test_clear_pending_returns_count():
    distiller = _FixedDistiller([_lesson(f"l{i}") for i in range(3)])
    bank = ReasoningBank(distiller=distiller)
    ext = MidSessionExtractor(
        bank, distiller=distiller, confidence_fn=lambda _l, _t: 0.5
    )
    ext.extract(_trajectory())
    assert len(ext.pending()) == 3
    assert ext.clear_pending() == 3
    assert ext.pending() == ()


# ────────────────────────────────────────────────────────────────
# Reporting helpers
# ────────────────────────────────────────────────────────────────


def test_extraction_result_counts():
    er = ExtractionResult(
        promoted=(),
        pending=(ScoredLesson(_lesson("a"), 0.6),),
        dropped=(),
    )
    assert er.counts() == {"promoted": 0, "pending": 1, "dropped": 0}


def test_render_pending_table_shape():
    rows = render_pending_table(
        [
            ScoredLesson(
                _lesson("xyz", title="t" * 200), 0.55
            )
        ]
    )
    assert rows[0]["id"] == "xyz"
    assert len(rows[0]["title"]) <= 80
    assert rows[0]["confidence"] == "0.55"


# ────────────────────────────────────────────────────────────────
# Integration with the real HeuristicDistiller
# ────────────────────────────────────────────────────────────────


def test_extract_with_real_heuristic_distiller_does_not_crash():
    """Smoke-test against the production distiller."""
    bank = ReasoningBank(distiller=_FixedDistiller([]))
    ext = MidSessionExtractor(bank)  # uses HeuristicDistiller by default
    traj = _trajectory(steps=4)
    # Should not raise, regardless of how many lessons the distiller emits.
    result = ext.extract(traj)
    total = len(result.promoted) + len(result.pending) + len(result.dropped)
    assert total >= 0
