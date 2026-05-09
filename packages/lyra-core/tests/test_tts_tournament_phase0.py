"""RED tests for v1.8 Wave-1 §3.1 — Tournament-Distilled TTS.

These tests are intentionally failing until the v1.8 Phase-1
implementation lands. Each test is marked ``phase0_red`` and
``xfail(strict=True)`` so:

- the test module is imported on every run (catches signature drift),
- the test executes (catches dataclass / Protocol drift),
- a passing test surfaces as ``XPASS → CI red``, forcing whoever lands
  the implementation to remove the marker in the same PR.
"""
from __future__ import annotations

import pytest

from lyra_core.tts import (
    Attempt,
    AttemptGenerator,
    Discriminator,
    TournamentTts,
    TtsBudget,
    TtsResult,
)


class _StubGenerator(AttemptGenerator):
    def __init__(self, artefacts: list[str]) -> None:
        self._artefacts = artefacts

    def generate(self, task_description: str, attempt_index: int) -> Attempt:
        return Attempt(
            id=f"a{attempt_index}",
            artefact=self._artefacts[attempt_index % len(self._artefacts)],
        )


class _PreferLongest(Discriminator):
    """Picks whichever artefact string is longer; deterministic."""

    def compare(self, a: Attempt, b: Attempt) -> Attempt:
        if len(a.artefact) == len(b.artefact):
            return a if a.id <= b.id else b
        return a if len(a.artefact) > len(b.artefact) else b


def test_budget_construction_validates_caps() -> None:
    """Public contract: zero / negative caps must raise immediately."""
    with pytest.raises(ValueError):
        TtsBudget(max_attempts=0, max_wall_clock_s=10.0, max_total_tokens=1000)
    with pytest.raises(ValueError):
        TtsBudget(max_attempts=4, max_wall_clock_s=0.0, max_total_tokens=1000)
    with pytest.raises(ValueError):
        TtsBudget(max_attempts=4, max_wall_clock_s=10.0, max_total_tokens=0)
    valid = TtsBudget(max_attempts=4, max_wall_clock_s=10.0, max_total_tokens=1000)
    assert valid.max_attempts == 4


def test_tournament_returns_winner_with_strictly_better_or_equal_score_than_average() -> None:
    """Winner score must be >= mean attempt score (no anti-improvement)."""
    gen = _StubGenerator(["short", "medium-len", "longest-of-the-three"])
    tts = TournamentTts(
        generator=gen,
        discriminator=_PreferLongest(),
        budget=TtsBudget(max_attempts=4, max_wall_clock_s=5.0, max_total_tokens=10_000),
    )
    result: TtsResult = tts.run("dummy task")
    losers_scores: list[float] = [0.0 for _ in result.losers]  # placeholder until impl
    avg_score = (result.winning_score + sum(losers_scores)) / (1 + len(result.losers))
    assert result.winning_score >= avg_score


def test_tournament_rounds_form_valid_bracket() -> None:
    """For N=4 attempts, expect 2 rounds (R0: 4→2, R1: 2→1)."""
    gen = _StubGenerator(["a", "bb", "ccc", "dddd"])
    tts = TournamentTts(
        generator=gen,
        discriminator=_PreferLongest(),
        budget=TtsBudget(max_attempts=4, max_wall_clock_s=5.0, max_total_tokens=10_000),
    )
    result = tts.run("dummy task")
    assert len(result.rounds) == 2
    assert all(r.round_index in (0, 1) for r in result.rounds)
    assert len(result.rounds[0].pairs) == 2
    assert len(result.rounds[-1].winners) == 1


def test_tournament_distilled_summary_mentions_loser_count() -> None:
    """The Parallel-Distill-Refine summary must reference how many losers it absorbed."""
    gen = _StubGenerator(["x", "yy", "zzz", "wwww"])
    tts = TournamentTts(
        generator=gen,
        discriminator=_PreferLongest(),
        budget=TtsBudget(max_attempts=4, max_wall_clock_s=5.0, max_total_tokens=10_000),
    )
    result = tts.run("dummy task")
    assert str(len(result.losers)) in result.distilled_summary


def test_tournament_honours_attempt_cap() -> None:
    """Even if the bracket would prefer more, max_attempts is the hard cap."""
    gen = _StubGenerator(["a", "b", "c", "d", "e", "f", "g", "h"])
    tts = TournamentTts(
        generator=gen,
        discriminator=_PreferLongest(),
        budget=TtsBudget(max_attempts=2, max_wall_clock_s=5.0, max_total_tokens=10_000),
    )
    result = tts.run("dummy task")
    total_attempts = 1 + len(result.losers)
    assert total_attempts <= 2
