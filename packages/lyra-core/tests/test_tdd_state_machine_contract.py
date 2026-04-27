"""Wave-F Task 1 — TDD phase state machine contract.

Pins:
* Every legal transition is accepted with valid evidence.
* Every illegal transition is rejected in strict mode.
* Evidence dataclasses validate their own shape.
* Lenient mode degrades to warnings rather than exceptions.
* History + evidence ledger + warnings list are all append-only.
"""
from __future__ import annotations

import pytest

from lyra_core.tdd import (
    GreenPassArtifact,
    PlanArtifact,
    RedFailureArtifact,
    RefactorArtifact,
    ShipArtifact,
    TDDPhase,
    TDDStateMachine,
    TransitionError,
)


# ---- helpers ----------------------------------------------------


def _walk_full_loop(sm: TDDStateMachine) -> None:
    sm.advance(TDDPhase.PLAN, evidence=PlanArtifact(steps=("write test",)))
    sm.advance(
        TDDPhase.RED,
        evidence=RedFailureArtifact(
            test_file="tests/x.py",
            test_name="test_x",
            failure_message="AssertionError: x != 1",
        ),
    )
    sm.advance(
        TDDPhase.GREEN,
        evidence=GreenPassArtifact(
            test_file="tests/x.py",
            test_name="test_x",
            all_tests_passed=True,
        ),
    )
    sm.advance(
        TDDPhase.REFACTOR,
        evidence=RefactorArtifact(
            diff_summary="extracted helper",
            tests_still_green=True,
        ),
    )
    sm.advance(
        TDDPhase.SHIP,
        evidence=ShipArtifact(summary="v0.1.0"),
    )


# ---- legal transitions ------------------------------------------


def test_initial_phase_is_idle() -> None:
    sm = TDDStateMachine()
    assert sm.phase == TDDPhase.IDLE
    assert sm.legal_next() == (TDDPhase.PLAN,)


def test_full_happy_path() -> None:
    sm = TDDStateMachine()
    _walk_full_loop(sm)
    assert sm.phase == TDDPhase.SHIP
    assert [src.value + "->" + dst.value for src, dst in sm.history] == [
        "idle->plan",
        "plan->red",
        "red->green",
        "green->refactor",
        "refactor->ship",
    ]
    # Evidence ledger captures each piece of evidence, in order.
    assert len(sm.evidence_ledger) == 5
    assert isinstance(sm.evidence_ledger[0], PlanArtifact)
    assert isinstance(sm.evidence_ledger[-1], ShipArtifact)


def test_red_can_loop_back_to_plan() -> None:
    sm = TDDStateMachine()
    sm.advance(TDDPhase.PLAN, evidence=PlanArtifact(steps=("a",)))
    sm.advance(
        TDDPhase.RED,
        evidence=RedFailureArtifact(
            test_file="t.py",
            test_name="test_a",
            failure_message="boom",
        ),
    )
    sm.advance(TDDPhase.PLAN, evidence=PlanArtifact(steps=("refine",)))
    assert sm.phase == TDDPhase.PLAN


def test_green_can_loop_back_to_red_for_next_test() -> None:
    sm = TDDStateMachine()
    sm.advance(TDDPhase.PLAN, evidence=PlanArtifact(steps=("a",)))
    sm.advance(
        TDDPhase.RED,
        evidence=RedFailureArtifact("t.py", "test_a", "boom"),
    )
    sm.advance(
        TDDPhase.GREEN,
        evidence=GreenPassArtifact("t.py", "test_a", True),
    )
    sm.advance(
        TDDPhase.RED,
        evidence=RedFailureArtifact("t.py", "test_b", "bang"),
    )
    assert sm.phase == TDDPhase.RED


def test_ship_returns_to_idle() -> None:
    sm = TDDStateMachine()
    _walk_full_loop(sm)
    sm.advance(TDDPhase.IDLE)
    assert sm.phase == TDDPhase.IDLE


# ---- illegal transitions (strict) -------------------------------


def test_strict_rejects_idle_to_red() -> None:
    sm = TDDStateMachine()
    with pytest.raises(TransitionError):
        sm.advance(
            TDDPhase.RED,
            evidence=RedFailureArtifact("t.py", "test_x", "boom"),
        )


def test_strict_rejects_plan_to_green() -> None:
    sm = TDDStateMachine()
    sm.advance(TDDPhase.PLAN, evidence=PlanArtifact(steps=("a",)))
    with pytest.raises(TransitionError):
        sm.advance(
            TDDPhase.GREEN,
            evidence=GreenPassArtifact("t.py", "test_a", True),
        )


def test_strict_rejects_refactor_to_idle() -> None:
    sm = TDDStateMachine()
    _walk_full_loop(sm)
    # SHIP → IDLE is legal; REFACTOR → IDLE is not.
    sm2 = TDDStateMachine()
    sm2.advance(TDDPhase.PLAN, evidence=PlanArtifact(steps=("a",)))
    sm2.advance(TDDPhase.RED, evidence=RedFailureArtifact("t.py", "test_a", "boom"))
    sm2.advance(TDDPhase.GREEN, evidence=GreenPassArtifact("t.py", "test_a", True))
    sm2.advance(
        TDDPhase.REFACTOR,
        evidence=RefactorArtifact("tidy", True),
    )
    with pytest.raises(TransitionError):
        sm2.advance(TDDPhase.IDLE)


# ---- evidence validation ---------------------------------------


def test_plan_artifact_rejects_empty_steps() -> None:
    with pytest.raises(TransitionError):
        PlanArtifact(steps=()).validate()


def test_red_artifact_rejects_empty_fields() -> None:
    with pytest.raises(TransitionError):
        RedFailureArtifact("", "test_x", "boom").validate()
    with pytest.raises(TransitionError):
        RedFailureArtifact("t.py", "", "boom").validate()
    with pytest.raises(TransitionError):
        RedFailureArtifact("t.py", "test_x", "").validate()


def test_green_artifact_rejects_failing_suite() -> None:
    with pytest.raises(TransitionError):
        GreenPassArtifact("t.py", "test_x", False).validate()


def test_refactor_artifact_rejects_broken_suite() -> None:
    with pytest.raises(TransitionError):
        RefactorArtifact("refactor", False).validate()


def test_ship_artifact_requires_some_identity() -> None:
    with pytest.raises(TransitionError):
        ShipArtifact().validate()
    ShipArtifact(commit_sha="abc").validate()
    ShipArtifact(pr_url="https://example.test/pr/1").validate()
    ShipArtifact(summary="v0.1").validate()


def test_missing_evidence_rejected_in_strict_mode() -> None:
    sm = TDDStateMachine()
    with pytest.raises(TransitionError):
        sm.advance(TDDPhase.PLAN)  # evidence missing


def test_wrong_evidence_type_rejected_in_strict_mode() -> None:
    sm = TDDStateMachine()
    with pytest.raises(TransitionError):
        sm.advance(TDDPhase.PLAN, evidence=ShipArtifact(summary="oops"))


# ---- lenient mode ----------------------------------------------


def test_lenient_mode_warns_but_allows_illegal_transition() -> None:
    sm = TDDStateMachine(strict=False)
    sm.advance(
        TDDPhase.GREEN,
        evidence=GreenPassArtifact("t.py", "test_x", True),
    )
    assert sm.phase == TDDPhase.GREEN
    assert sm.warnings, "lenient mode should record a warning"


def test_lenient_mode_accepts_missing_evidence() -> None:
    sm = TDDStateMachine(strict=False)
    sm.advance(TDDPhase.PLAN)
    assert sm.phase == TDDPhase.PLAN
    assert any("requires evidence" in w for w in sm.warnings)


def test_reset_returns_to_idle_and_logs_history() -> None:
    sm = TDDStateMachine()
    sm.advance(TDDPhase.PLAN, evidence=PlanArtifact(steps=("a",)))
    sm.reset()
    assert sm.phase == TDDPhase.IDLE
    assert sm.history[-1] == (TDDPhase.PLAN, TDDPhase.IDLE)
