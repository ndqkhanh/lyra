"""Wave-F Task 3 — refute-or-promote stage contract."""
from __future__ import annotations

import pytest

from lyra_core.loop import (
    RefuteError,
    RefuteOrPromoteResult,
    RefutePass,
    RefutePromoteStage,
    refute_or_promote,
)


def _always_refute(*, solution: str, attempt: int, history):
    return RefutePass(
        attempt=attempt,
        refuted=True,
        counter_example=f"boom-{attempt}",
        argument="always refutes",
    )


def _never_refute(*, solution: str, attempt: int, history):
    return RefutePass(attempt=attempt, refuted=False)


def _refute_once_then_give_up(*, solution: str, attempt: int, history):
    if attempt == 1:
        return RefutePass(
            attempt=attempt,
            refuted=False,
            argument="couldn't refute on first pass",
        )
    if attempt == 2:
        return RefutePass(
            attempt=attempt,
            refuted=True,
            counter_example="actually found one",
        )
    return RefutePass(attempt=attempt, refuted=False)


# ---- basic verdicts ------------------------------------------------


def test_never_refute_promotes() -> None:
    result = refute_or_promote(
        solution="candidate",
        adversary=_never_refute,
        max_attempts=3,
    )
    assert result.promoted is True
    assert result.verdict == "promoted"
    assert len(result.passes) == 3
    assert result.winning_pass is None


def test_always_refute_refutes_on_first_attempt() -> None:
    result = refute_or_promote(
        solution="candidate",
        adversary=_always_refute,
        max_attempts=5,
    )
    assert result.promoted is False
    assert result.verdict == "refuted"
    assert len(result.passes) == 1
    assert result.winning_pass is not None
    assert result.winning_pass.counter_example == "boom-1"


def test_refute_mid_loop_stops_early() -> None:
    result = refute_or_promote(
        solution="candidate",
        adversary=_refute_once_then_give_up,
        max_attempts=5,
    )
    assert result.promoted is False
    assert len(result.passes) == 2  # stopped after second attempt refuted
    assert result.winning_pass.attempt == 2


# ---- misuse / guards -----------------------------------------------


def test_max_attempts_must_be_positive() -> None:
    with pytest.raises(RefuteError):
        refute_or_promote(
            solution="x",
            adversary=_never_refute,
            max_attempts=0,
        )


def test_adversary_must_return_refutepass() -> None:
    def _bad(*, solution, attempt, history):
        return {"oops": True}

    with pytest.raises(RefuteError):
        refute_or_promote(
            solution="x",
            adversary=_bad,  # type: ignore[arg-type]
            max_attempts=2,
        )


def test_adversary_must_honour_attempt_counter() -> None:
    def _bad(*, solution, attempt, history):
        return RefutePass(attempt=attempt + 10, refuted=False)

    with pytest.raises(RefuteError):
        refute_or_promote(
            solution="x",
            adversary=_bad,
            max_attempts=2,
        )


# ---- bookkeeping ---------------------------------------------------


def test_passes_are_captured_in_order() -> None:
    result = refute_or_promote(
        solution="x",
        adversary=_never_refute,
        max_attempts=3,
    )
    assert [p.attempt for p in result.passes] == [1, 2, 3]
    assert all(p.refuted is False for p in result.passes)


def test_stage_runner_reusable() -> None:
    stage = RefutePromoteStage(adversary=_never_refute, max_attempts=2)
    r1 = stage.run(solution="a")
    r2 = stage.run(solution="b")
    assert r1.promoted and r2.promoted
    assert len(r1.passes) == len(r2.passes) == 2


def test_result_serialises() -> None:
    result = refute_or_promote(
        solution="x",
        adversary=_always_refute,
        max_attempts=2,
    )
    data = result.to_dict()
    assert data["promoted"] is False
    assert data["verdict"] == "refuted"
    assert data["winning_pass"]["counter_example"] == "boom-1"
    assert isinstance(data["passes"], list) and len(data["passes"]) == 1
