"""Contract tests for ``lyra_core.eval.passk`` (Phase J.2).

Coverage:

* deterministic models produce ``pass@k == pass^k`` (no flakiness).
* a model that flips outcome ⇒ ``pass@k=1, pass^k=0, flaky=True``.
* the per-case breakdown matches the trial outcomes byte-for-byte.
* the ``reliability_gap`` is exactly ``pass@k - pass^k``.
* ``k < 1`` is rejected.
"""
from __future__ import annotations

import pytest
from lyra_core.eval import EvalCase, run_passk


_CASE_PASS = EvalCase(
    name="hello-world",
    prompt="say hello",
    expected_substrings=("hello",),
    mode="all",
)
_CASE_FAIL = EvalCase(
    name="never-passes",
    prompt="give up",
    expected_substrings=("nope-token-not-in-output",),
    mode="all",
)


def _always_match(_prompt: str) -> str:
    return "hello world"


def _never_match(_prompt: str) -> str:
    return "totally unrelated"


class _Flipper:
    """Pass on even-indexed calls, fail on odd-indexed calls."""

    def __init__(self) -> None:
        self.n = 0

    def __call__(self, _prompt: str) -> str:
        self.n += 1
        return "hello" if self.n % 2 == 1 else "bye"


def test_deterministic_pass_yields_full_reliability() -> None:
    report = run_passk([_CASE_PASS], k=5, model_call=_always_match)
    assert report.pass_at_k == 1.0
    assert report.pass_pow_k == 1.0
    assert report.reliability_gap == 0.0
    assert report.flaky_cases == ()


def test_deterministic_fail_yields_zero_reliability() -> None:
    report = run_passk([_CASE_FAIL], k=3, model_call=_never_match)
    assert report.pass_at_k == 0.0
    assert report.pass_pow_k == 0.0
    assert report.flaky_cases == ()


def test_flipper_surfaces_flakiness() -> None:
    flipper = _Flipper()
    report = run_passk([_CASE_PASS], k=4, model_call=flipper)
    [trial] = report.trials
    assert trial.passed_count == 2
    assert trial.passed_any
    assert not trial.passed_all
    assert trial.flaky
    assert report.pass_at_k == 1.0
    assert report.pass_pow_k == 0.0
    assert report.reliability_gap == 1.0
    assert report.flaky_cases == ("hello-world",)


def test_per_case_serialisation_matches_trial_outcomes() -> None:
    report = run_passk(
        [_CASE_PASS, _CASE_FAIL],
        k=2,
        model_call=_always_match,
    )
    body = report.to_dict()
    assert body["k"] == 2
    assert body["total_cases"] == 2
    per_case = {entry["name"]: entry for entry in body["per_case"]}
    assert per_case["hello-world"]["passed_count"] == 2
    assert per_case["hello-world"]["passed_all"] is True
    assert per_case["never-passes"]["passed_count"] == 0
    assert per_case["never-passes"]["passed_all"] is False


def test_invalid_k_rejected() -> None:
    with pytest.raises(ValueError):
        run_passk([_CASE_PASS], k=0, model_call=_always_match)


def test_flakiness_score_minority_normalised() -> None:
    """A 4/5 pass split should give flakiness=0.2 (one trial against majority)."""
    flipper = _Flipper()
    report = run_passk([_CASE_PASS], k=5, model_call=flipper)
    [trial] = report.trials
    # Flipper passes on odd calls (1,3,5) — that's 3 of 5 ⇒ minority=2 ⇒ 0.4.
    assert trial.passed_count == 3
    assert pytest.approx(trial.flakiness, rel=1e-6) == 0.4


def test_empty_corpus_reports_perfect_score() -> None:
    report = run_passk([], k=3, model_call=_always_match)
    assert report.total_cases == 0
    assert report.pass_at_k == 1.0
    assert report.pass_pow_k == 1.0
    assert report.flaky_cases == ()
