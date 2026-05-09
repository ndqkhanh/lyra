"""Phase J.5 (v3.1.0): GEPA-style prompt evolver — contract tests.

Locked surface (each test pins one part of the public contract):

1. ``score_candidate`` returns 1.0 on empty examples.
2. ``score_candidate`` is the exact pass-rate over substring matches.
3. ``EvolveCandidate.dominates`` implements Pareto dominance precisely.
4. ``pareto_front`` keeps the non-dominated set, dedupes prompts, and
   sorts by score↓ then length↑.
5. ``templated_mutator`` is a closed-form deterministic rewriter; the
   same RNG state always produces the same offspring.
6. ``evolve`` with ``generations=0`` returns the seed candidates
   evaluated once.
7. ``evolve`` with a discriminating training set produces a strictly
   better best.score than the seed when at least one mutation helps.
8. ``evolve`` history records one entry per generation and the
   per-generation best_score is monotone non-decreasing.
"""
from __future__ import annotations

import random

from lyra_core.evolve import (
    EvolveCandidate,
    EvolveTrainExample,
    evolve,
    pareto_front,
    score_candidate,
    templated_mutator,
)


# ----------------------------- scoring ----------------------------------- #


def _stub_echo(prompt: str, _input: str) -> str:
    return prompt


def test_score_empty_examples_is_one() -> None:
    assert score_candidate("anything", [], model_call=_stub_echo) == 1.0


def test_score_matches_pass_rate_exactly() -> None:
    examples = [
        EvolveTrainExample(input="i1", expected="found"),
        EvolveTrainExample(input="i2", expected="missing"),
        EvolveTrainExample(input="i3", expected="found"),
    ]
    score = score_candidate("found", examples, model_call=_stub_echo)
    assert abs(score - (2 / 3)) < 1e-9


# ----------------------------- dominance --------------------------------- #


def test_dominance_strict() -> None:
    a = EvolveCandidate(prompt="a", score=0.9, length=20, generation=0)
    b = EvolveCandidate(prompt="b", score=0.8, length=30, generation=0)
    assert a.dominates(b)
    assert not b.dominates(a)


def test_dominance_ties_are_not_strict() -> None:
    a = EvolveCandidate(prompt="a", score=0.9, length=20, generation=0)
    b = EvolveCandidate(prompt="b", score=0.9, length=20, generation=0)
    assert not a.dominates(b)
    assert not b.dominates(a)


def test_dominance_score_tied_length_better() -> None:
    a = EvolveCandidate(prompt="a", score=0.9, length=10, generation=0)
    b = EvolveCandidate(prompt="b", score=0.9, length=20, generation=0)
    assert a.dominates(b)
    assert not b.dominates(a)


# ----------------------------- pareto front ------------------------------ #


def test_pareto_front_keeps_non_dominated() -> None:
    cs = [
        EvolveCandidate(prompt="short_low", score=0.6, length=10, generation=0),
        EvolveCandidate(prompt="long_high", score=0.9, length=80, generation=0),
        EvolveCandidate(prompt="dominated", score=0.6, length=80, generation=0),
        EvolveCandidate(prompt="balanced", score=0.8, length=40, generation=0),
    ]
    front = pareto_front(cs)
    names = {c.prompt for c in front}
    assert "dominated" not in names
    assert {"short_low", "long_high", "balanced"} <= names


def test_pareto_front_sorts_score_desc_then_length_asc() -> None:
    cs = [
        EvolveCandidate(prompt="b", score=0.7, length=20, generation=0),
        EvolveCandidate(prompt="a", score=0.9, length=10, generation=0),
        EvolveCandidate(prompt="c", score=0.7, length=10, generation=0),
    ]
    front = pareto_front(cs)
    assert [c.prompt for c in front] == ["a", "c", "b"]


def test_pareto_front_deduplicates_identical_prompts() -> None:
    cs = [
        EvolveCandidate(prompt="x", score=0.9, length=10, generation=0),
        EvolveCandidate(prompt="x", score=0.9, length=10, generation=1),
    ]
    front = pareto_front(cs)
    assert len(front) == 1


def test_pareto_front_empty_returns_empty_tuple() -> None:
    assert pareto_front([]) == ()


# ----------------------------- mutator ----------------------------------- #


def test_templated_mutator_is_deterministic_under_same_seed() -> None:
    base = "Solve the problem."
    a = templated_mutator(base, random.Random(7))
    b = templated_mutator(base, random.Random(7))
    assert a == b
    assert a != base


def test_templated_mutator_no_op_when_all_nudges_present() -> None:
    base = "Solve the problem."
    rng = random.Random(0)
    saturated = base
    for _ in range(20):
        saturated = templated_mutator(saturated, rng)
    final = templated_mutator(saturated, rng)
    assert final == saturated  # no further mutation possible


# ----------------------------- driver ------------------------------------ #


def test_evolve_zero_generations_evaluates_once() -> None:
    examples = [
        EvolveTrainExample(input="i1", expected="seed"),
        EvolveTrainExample(input="i2", expected="seed"),
    ]
    report = evolve(
        ["seed"],
        examples,
        model_call=_stub_echo,
        generations=0,
        population=1,
    )
    assert len(report.history) == 1
    assert report.best.prompt == "seed"
    assert report.best.score == 1.0


def test_evolve_finds_strictly_better_when_seed_fails() -> None:
    """A deterministic mutator that always rewrites toward the answer
    proves the GEPA mechanism: scoring → mutation → Pareto filter →
    surfaced best — works end-to-end without depending on the
    templated mutator's RNG coverage.
    """
    examples = [EvolveTrainExample(input="x", expected="Answer:")]

    def _always_answer(prompt: str, _rng: random.Random) -> str:
        return prompt + " Answer:"

    report = evolve(
        ["Solve the problem."],
        examples,
        model_call=_stub_echo,
        generations=2,
        population=2,
        mutator=_always_answer,
    )
    assert report.best.score == 1.0
    assert "Answer:" in report.best.prompt
    assert report.best.generation >= 1


def test_evolve_history_one_entry_per_generation_plus_seed() -> None:
    examples = [EvolveTrainExample(input="x", expected="anything")]
    report = evolve(
        ["seed"],
        examples,
        model_call=_stub_echo,
        generations=2,
        population=2,
    )
    assert len(report.history) == 3
    assert report.history[0].generation == 0
    assert report.history[-1].generation == 2


def test_evolve_best_score_is_monotone_non_decreasing() -> None:
    examples = [EvolveTrainExample(input="x", expected="Answer:")]

    def _appender(prompt: str, _rng: random.Random) -> str:
        return prompt + " Answer:"

    report = evolve(
        ["nope"],
        examples,
        model_call=_stub_echo,
        generations=4,
        population=4,
        mutator=_appender,
    )
    scores = [h.best_score for h in report.history]
    for prev, nxt in zip(scores, scores[1:]):
        assert nxt >= prev
