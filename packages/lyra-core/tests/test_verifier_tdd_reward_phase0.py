"""RED tests for v1.8 Wave-1 §3.4 — TDD-Reward inference signal."""
from __future__ import annotations

import pytest

from lyra_core.verifier import TddTestOutcome, compute_tdd_reward


def test_compute_tdd_reward_rejects_duplicate_nodeids() -> None:
    """Public contract: a duplicate nodeid is a programmer error, raise loudly."""
    outcomes = [
        TddTestOutcome(nodeid="tests/test_a.py::test_x", was_failing_before=True, is_passing_after=True),
        TddTestOutcome(nodeid="tests/test_a.py::test_x", was_failing_before=False, is_passing_after=True),
    ]
    with pytest.raises(ValueError, match="duplicate"):
        compute_tdd_reward(outcomes)


def test_perfect_red_to_green_yields_top_score() -> None:
    """Every previously-red test now green => score == 1.0."""
    outcomes = [
        TddTestOutcome(nodeid="t::a", was_failing_before=True, is_passing_after=True),
        TddTestOutcome(nodeid="t::b", was_failing_before=True, is_passing_after=True),
    ]
    sig = compute_tdd_reward(outcomes)
    assert sig.score == pytest.approx(1.0)
    assert sig.ratio_red_to_green == pytest.approx(1.0)


def test_breaking_a_previously_green_test_drops_score() -> None:
    """Regressions count: a green→red transition must reduce the score."""
    no_regression = [
        TddTestOutcome(nodeid="t::a", was_failing_before=True, is_passing_after=True),
        TddTestOutcome(nodeid="t::b", was_failing_before=False, is_passing_after=True),
    ]
    with_regression = [
        TddTestOutcome(nodeid="t::a", was_failing_before=True, is_passing_after=True),
        TddTestOutcome(nodeid="t::b", was_failing_before=False, is_passing_after=False),
    ]
    s_no = compute_tdd_reward(no_regression).score
    s_yes = compute_tdd_reward(with_regression).score
    assert s_yes < s_no


def test_new_test_addition_is_credited() -> None:
    """Authoring a *new* failing test (then making it pass) is the TDD ideal."""
    outcomes = [
        TddTestOutcome(
            nodeid="t::new", was_failing_before=True, is_passing_after=True, is_new_test=True
        )
    ]
    sig = compute_tdd_reward(outcomes)
    assert sig.new_tests_added == 1
    assert sig.score > 0.0


def test_custom_weights_change_the_score() -> None:
    """Weights override is part of the public contract for downstream tuners."""
    outcomes = [
        TddTestOutcome(nodeid="t::a", was_failing_before=True, is_passing_after=True),
        TddTestOutcome(nodeid="t::b", was_failing_before=False, is_passing_after=False),
    ]
    s_default = compute_tdd_reward(outcomes).score
    s_red_heavy = compute_tdd_reward(
        outcomes,
        weights={"red_to_green": 1.0, "green_kept": 0.0, "new_tests": 0.0},
    ).score
    assert s_default != s_red_heavy
